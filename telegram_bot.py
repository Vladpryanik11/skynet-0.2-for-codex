"""Telegram entry point for SKYNET tasks."""

from __future__ import annotations

import asyncio
import contextlib
import os
import sys
import time
from dataclasses import dataclass, field
from itertools import count
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_CHUNK_LIMIT = 3800
RUNNER_RESULT_START = "<<<SKYNET_RESULT_START>>>"
RUNNER_RESULT_END = "<<<SKYNET_RESULT_END>>>"
RUNNER_PATH = Path(__file__).resolve().with_name("telegram_task_runner.py")

_task_ids = count(1)


@dataclass(frozen=True)
class WorkMode:
    key: str
    label: str
    description: str
    department_override: str | None


WORK_MODES: dict[str, WorkMode] = {
    "fast": WorkMode("fast", "Быстрый", "короткий прямой ответ без полного конвейера агентов", None),
    "auto": WorkMode("auto", "Авто", "SKYNET сам выбирает отдел", None),
    "coders": WorkMode("coders", "Кодеры", "агенты, код, интеграции, деплой", "coders"),
    "marketing": WorkMode("marketing", "Маркетинг", "посты, офферы, SEO, тексты", "marketing"),
    "design": WorkMode("design", "Дизайн", "лендинги, UI, HTML/CSS-макеты", "design"),
}


@dataclass
class BotTask:
    id: int
    chat_id: int
    user_id: int | None
    text: str
    mode: str
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    progress: int = 0
    stage: str = "в очереди"


@dataclass
class BotState:
    queue: asyncio.Queue[BotTask]
    current: BotTask | None = None
    completed: int = 0
    failed: int = 0
    chat_modes: dict[int, str] = field(default_factory=dict)


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


def progress_bar(percent: int, width: int = 18) -> str:
    percent = max(0, min(100, int(percent)))
    filled = round(width * percent / 100)
    return "[" + ("█" * filled) + ("░" * (width - filled)) + "]"


def progress_percent(elapsed: float, timeout: int) -> int:
    if timeout <= 0:
        return 5
    ratio = max(0.0, min(1.0, elapsed / timeout))
    return max(5, min(95, int(5 + ratio * 90)))


def progress_stage(percent: int, mode: str = "auto") -> str:
    if mode == "fast":
        if percent < 25:
            return "подготовка ответа"
        if percent < 75:
            return "локальная модель пишет ответ"
        return "финальная сборка"

    if percent < 15:
        return "подготовка запуска"
    if percent < 35:
        return "выбор отдела и контекста"
    if percent < 70:
        return "агенты выполняют задачу"
    if percent < 92:
        return "сборка финального ответа"
    return "финальная проверка"


def extract_runner_result(output: str) -> str:
    start = output.find(RUNNER_RESULT_START)
    end = output.find(RUNNER_RESULT_END, start + len(RUNNER_RESULT_START))
    if start == -1 or end == -1:
        return output.strip()
    return output[start + len(RUNNER_RESULT_START) : end].strip()


def default_mode() -> str:
    mode = os.environ.get("TELEGRAM_DEFAULT_MODE", "fast").strip().lower()
    return mode if mode in WORK_MODES else "fast"


def mode_for_chat(state: BotState, chat_id: int) -> str:
    mode = state.chat_modes.get(chat_id, default_mode())
    return mode if mode in WORK_MODES else default_mode()


def mode_keyboard(selected_mode: str | None = None) -> InlineKeyboardMarkup:
    selected_mode = selected_mode or default_mode()

    def button(mode: str) -> InlineKeyboardButton:
        label = WORK_MODES[mode].label
        if mode == selected_mode:
            label = f"• {label}"
        return InlineKeyboardButton(label, callback_data=f"mode:{mode}")

    return InlineKeyboardMarkup(
        [
            [button("fast"), button("auto")],
            [button("coders"), button("marketing"), button("design")],
            [InlineKeyboardButton("Статус", callback_data="status")],
        ]
    )


def mode_text(selected_mode: str) -> str:
    mode = WORK_MODES[selected_mode]
    lines = [
        "Выбери режим работы SKYNET:",
        "",
        f"Сейчас: {mode.label}",
        mode.description,
        "",
        "Быстрый режим подходит для обычных вопросов. Отделы запускают полный агентный конвейер и работают дольше.",
        "",
        "После выбора просто отправь задачу обычным сообщением.",
    ]
    return "\n".join(lines)


def status_text(state: BotState, chat_id: int | None = None) -> str:
    if state.current:
        elapsed = int(time.time() - state.current.started_at) if state.current.started_at else 0
        current = (
            f"#{state.current.id} · {WORK_MODES[state.current.mode].label} · "
            f"{state.current.progress}% {progress_bar(state.current.progress)}\n"
            f"этап: {state.current.stage}\n"
            f"время: {elapsed} сек\n"
            f"запрос: {state.current.text[:160]}"
        )
    else:
        current = "нет"

    selected = ""
    if chat_id is not None:
        selected_mode = mode_for_chat(state, chat_id)
        selected = f"\nрежим этого чата: {WORK_MODES[selected_mode].label}"

    return (
        "Статус SKYNET:\n"
        f"в работе: {current}\n"
        f"в очереди: {state.queue.qsize()}\n"
        f"готово: {state.completed}\n"
        f"ошибок: {state.failed}"
        f"{selected}"
    )


def tail_text(text: str, limit: int = 1600) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return "..." + text[-limit:]


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

    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat:
        return

    state = state_from(context)
    selected_mode = mode_for_chat(state, chat.id)
    user_id = update.effective_user.id if update.effective_user else "unknown"
    await message.reply_text(
        "SKYNET на связи.\n\n"
        "Выбери режим кнопками ниже или оставь Быстрый. Потом отправь задачу обычным сообщением, "
        "а я покажу прогресс и пришлю результат сюда.\n\n"
        f"Твой Telegram ID: {user_id}",
        reply_markup=mode_keyboard(selected_mode),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update, context):
        return

    await update.effective_message.reply_text(
        "Команды:\n"
        "/start - запуск и выбор режима\n"
        "/id - показать твой Telegram ID\n"
        "/mode - кнопки режимов работы\n"
        "/status - текущая задача и очередь\n\n"
        "Все остальные текстовые сообщения считаются заданиями SKYNET."
    )


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else "unknown"
    chat_id = update.effective_chat.id if update.effective_chat else "unknown"
    await update.effective_message.reply_text(f"user_id: {user_id}\nchat_id: {chat_id}")


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update, context):
        return

    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat:
        return

    state = state_from(context)
    selected_mode = mode_for_chat(state, chat.id)
    await message.reply_text(mode_text(selected_mode), reply_markup=mode_keyboard(selected_mode))


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update, context):
        return

    state = state_from(context)
    chat_id = update.effective_chat.id if update.effective_chat else None
    await update.effective_message.reply_text(status_text(state, chat_id))


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await deny_if_needed(update, context):
        return

    query = update.callback_query
    chat = update.effective_chat
    if not query or not chat or not query.data:
        return

    state = state_from(context)
    data = query.data
    if data.startswith("mode:"):
        requested_mode = data.split(":", 1)[1]
        if requested_mode not in WORK_MODES:
            await query.answer("Неизвестный режим.")
            return

        state.chat_modes[chat.id] = requested_mode
        await query.answer(f"Режим: {WORK_MODES[requested_mode].label}")
        with contextlib.suppress(TelegramError):
            await query.edit_message_text(
                mode_text(requested_mode),
                reply_markup=mode_keyboard(requested_mode),
            )
        return

    if data == "status":
        await query.answer("Обновляю статус")
        selected_mode = mode_for_chat(state, chat.id)
        with contextlib.suppress(TelegramError):
            await query.edit_message_text(
                status_text(state, chat.id),
                reply_markup=mode_keyboard(selected_mode),
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
    selected_mode = mode_for_chat(state, chat.id)
    task = BotTask(
        id=next(_task_ids),
        chat_id=chat.id,
        user_id=update.effective_user.id if update.effective_user else None,
        text=text,
        mode=selected_mode,
    )

    try:
        state.queue.put_nowait(task)
    except asyncio.QueueFull:
        await message.reply_text("Очередь заполнена. Подожди завершения текущих задач и отправь снова.")
        return

    position = state.queue.qsize()
    label = WORK_MODES[selected_mode].label
    action = "Готовлю ответ" if selected_mode == "fast" else "Запускаю агентов"
    if state.current:
        await message.reply_text(f"Принял задачу #{task.id}. Режим: {label}. В очереди перед ней: {position - 1}.")
    else:
        await message.reply_text(f"Принял задачу #{task.id}. Режим: {label}. {action}.")


async def typing_pulse(application: Application, chat_id: int) -> None:
    while True:
        with contextlib.suppress(TelegramError):
            await application.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(4)


async def progress_pulse(
    application: Application,
    task: BotTask,
    progress_message_id: int,
    timeout: int,
    interval: int,
) -> None:
    while True:
        elapsed = time.time() - (task.started_at or time.time())
        task.progress = progress_percent(elapsed, timeout)
        task.stage = progress_stage(task.progress, task.mode)
        text = (
            f"Задача #{task.id} в работе\n"
            f"Режим: {WORK_MODES[task.mode].label}\n"
            f"Готовность: {task.progress}% {progress_bar(task.progress)}\n"
            f"Этап: {task.stage}"
        )
        with contextlib.suppress(TelegramError):
            await application.bot.edit_message_text(
                chat_id=task.chat_id,
                message_id=progress_message_id,
                text=text,
            )
        await asyncio.sleep(interval)


async def run_skynet_task(task: BotTask, timeout: int) -> str:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(RUNNER_PATH),
        "--mode",
        task.mode,
        cwd=str(RUNNER_PATH.parent),
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(task.text.encode("utf-8")),
            timeout=timeout,
        )
    except asyncio.TimeoutError as exc:
        process.kill()
        with contextlib.suppress(Exception):
            await process.communicate()
        raise TimeoutError(f"превышен лимит выполнения {timeout} сек") from exc

    stdout_text = stdout.decode("utf-8", errors="replace")
    stderr_text = stderr.decode("utf-8", errors="replace")
    result_text = extract_runner_result(stdout_text)

    if process.returncode != 0:
        details = tail_text(stderr_text or stdout_text or "runner stopped without output")
        raise RuntimeError(details)

    return result_text or "(пустой ответ)"


async def worker(application: Application) -> None:
    state = application.bot_data["state"]
    task_timeout = int_env("TELEGRAM_TASK_TIMEOUT", 600)
    progress_interval = int_env("TELEGRAM_PROGRESS_INTERVAL", 5)
    while True:
        task = await state.queue.get()
        state.current = task
        task.started_at = time.time()
        task.progress = 1
        task.stage = "запуск"
        typing = asyncio.create_task(typing_pulse(application, task.chat_id))
        progress: asyncio.Task | None = None
        try:
            progress_message = await application.bot.send_message(
                chat_id=task.chat_id,
                text=(
                    f"Задача #{task.id} в работе\n"
                    f"Режим: {WORK_MODES[task.mode].label}\n"
                    f"Готовность: {task.progress}% {progress_bar(task.progress)}\n"
                    f"Этап: {task.stage}"
                ),
            )
            progress = asyncio.create_task(
                progress_pulse(application, task, progress_message.message_id, task_timeout, progress_interval)
            )
            result = await run_skynet_task(task, task_timeout)
            task.progress = 100
            task.stage = "готово"
            state.completed += 1
            progress.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await progress
            with contextlib.suppress(TelegramError):
                await application.bot.edit_message_text(
                    chat_id=task.chat_id,
                    message_id=progress_message.message_id,
                    text=(
                        f"Задача #{task.id} завершена\n"
                        f"Режим: {WORK_MODES[task.mode].label}\n"
                        f"Готовность: 100% {progress_bar(100)}"
                    ),
                )
            await send_long_message(application, task.chat_id, f"Готово, задача #{task.id}:\n\n{result}")
        except Exception as exc:
            state.failed += 1
            if progress is not None:
                progress.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await progress
            await send_long_message(
                application,
                task.chat_id,
                f"Задача #{task.id} завершилась ошибкой:\n{type(exc).__name__}: {exc}",
            )
        finally:
            typing.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await typing
            if progress is not None:
                progress.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await progress
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
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, task_message))

    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
