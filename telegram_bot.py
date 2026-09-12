"""Telegram entry point for SKYNET tasks."""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from dataclasses import dataclass, field
from itertools import count

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

from institute.local_mode import skynet_mode  # noqa: E402
from institute.router import route_and_run  # noqa: E402
from institute.runtime import quality_gate_enabled  # noqa: E402

TELEGRAM_CHUNK_LIMIT = 3800
_task_ids = count(1)


@dataclass
class BotTask:
    id: int
    chat_id: int
    user_id: int | None
    text: str
    created_at: float = field(default_factory=time.time)


@dataclass
class BotState:
    queue: asyncio.Queue[BotTask]
    current: BotTask | None = None
    completed: int = 0
    failed: int = 0


def parse_allowed_user_ids(raw_value: str | None) -> set[int]:
    if not raw_value:
        return set()

    allowed: set[int] = set()
    for value in raw_value.replace(";", ",").split(","):
        value = value.strip()
        if not value:
            continue
        try:
            allowed.add(int(value))
        except ValueError:
            continue
    return allowed


def split_for_telegram(text: object, limit: int = TELEGRAM_CHUNK_LIMIT) -> list[str]:
    body = str(text or "").strip() or "(пустой ответ)"
    chunks: list[str] = []

    while len(body) > limit:
        split_at = max(
            body.rfind("\n\n", 0, limit),
            body.rfind("\n", 0, limit),
            body.rfind(" ", 0, limit),
        )
        if split_at < limit // 2:
            split_at = limit
        chunks.append(body[:split_at].rstrip())
        body = body[split_at:].lstrip()

    chunks.append(body)
    return chunks


async def send_long_message(application: Application, chat_id: int, text: object) -> None:
    for chunk in split_for_telegram(text):
        await application.bot.send_message(chat_id=chat_id, text=chunk)


def state_from(context: ContextTypes.DEFAULT_TYPE) -> BotState:
    return context.application.bot_data["state"]


def is_allowed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    allowed = context.application.bot_data["allowed_user_ids"]
    user = update.effective_user
    return not allowed or (user is not None and user.id in allowed)


async def deny_if_needed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if is_allowed(update, context):
        return False
    if update.effective_message:
        await update.effective_message.reply_text("Этот Telegram-пользователь не подключен к SKYNET.")
    return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update, context):
        return

    user_id = update.effective_user.id if update.effective_user else "unknown"
    await update.effective_message.reply_text(
        "SKYNET на связи.\n\n"
        "Просто отправь задачу обычным сообщением, а я поставлю ее в очередь, "
        "запущу агентов и пришлю результат сюда.\n\n"
        f"Твой Telegram ID: {user_id}"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update, context):
        return

    await update.effective_message.reply_text(
        "Команды:\n"
        "/start - запуск\n"
        "/id - показать твой Telegram ID\n"
        "/mode - текущий режим SKYNET\n"
        "/status - текущая задача и очередь\n\n"
        "Все остальные текстовые сообщения считаются заданиями для агентов."
    )


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else "unknown"
    chat_id = update.effective_chat.id if update.effective_chat else "unknown"
    await update.effective_message.reply_text(f"user_id: {user_id}\nchat_id: {chat_id}")


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update, context):
        return

    await update.effective_message.reply_text(
        "Режим SKYNET:\n"
        f"SKYNET_MODE={skynet_mode()}\n"
        f"DEFAULT_DEPARTMENT={os.environ.get('DEFAULT_DEPARTMENT', 'coders')}\n"
        f"ENABLE_QUALITY_GATE={int(quality_gate_enabled())}"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update, context):
        return

    state = state_from(context)
    current = f"#{state.current.id}: {state.current.text[:120]}" if state.current else "нет"
    await update.effective_message.reply_text(
        "Статус:\n"
        f"в работе: {current}\n"
        f"в очереди: {state.queue.qsize()}\n"
        f"готово: {state.completed}\n"
        f"ошибок: {state.failed}"
    )


async def task_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update, context):
        return

    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat or not message.text:
        return

    text = message.text.strip()
    if not text:
        return

    state = state_from(context)
    task = BotTask(
        id=next(_task_ids),
        chat_id=chat.id,
        user_id=update.effective_user.id if update.effective_user else None,
        text=text,
    )

    try:
        state.queue.put_nowait(task)
    except asyncio.QueueFull:
        await message.reply_text("Очередь заполнена. Подожди завершения текущих задач и отправь снова.")
        return

    position = state.queue.qsize()
    if state.current:
        await message.reply_text(f"Принял задачу #{task.id}. В очереди перед ней: {position - 1}.")
    else:
        await message.reply_text(f"Принял задачу #{task.id}. Запускаю агентов.")


async def typing_pulse(application: Application, chat_id: int) -> None:
    while True:
        await application.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(4)


async def worker(application: Application) -> None:
    state = application.bot_data["state"]
    while True:
        task = await state.queue.get()
        state.current = task
        pulse = asyncio.create_task(typing_pulse(application, task.chat_id))
        try:
            await application.bot.send_message(chat_id=task.chat_id, text=f"Задача #{task.id}: SKYNET начал работу.")
            result = await asyncio.to_thread(route_and_run, task.text)
            state.completed += 1
            await send_long_message(application, task.chat_id, f"Готово, задача #{task.id}:\n\n{result}")
        except Exception as exc:
            state.failed += 1
            await send_long_message(
                application,
                task.chat_id,
                f"Задача #{task.id} завершилась ошибкой:\n{type(exc).__name__}: {exc}",
            )
        finally:
            pulse.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pulse
            state.current = None
            state.queue.task_done()


async def post_init(application: Application) -> None:
    application.bot_data["worker_task"] = asyncio.create_task(
        worker(application), name="skynet-telegram-worker"
    )


async def post_shutdown(application: Application) -> None:
    task = application.bot_data.get("worker_task")
    if not task:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required in .env or environment.")

    max_queue_size = int_env("TELEGRAM_TASK_QUEUE_SIZE", 20)
    application = (
        Application.builder()
        .token(token)
        .concurrent_updates(True)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    application.bot_data["state"] = BotState(queue=asyncio.Queue(maxsize=max_queue_size))
    application.bot_data["allowed_user_ids"] = parse_allowed_user_ids(
        os.environ.get("TELEGRAM_ALLOWED_USER_IDS")
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("mode", mode_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, task_message))

    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
