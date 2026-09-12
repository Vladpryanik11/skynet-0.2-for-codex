FROM python:3.12-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -e .

# Ключи передавайте через `docker run -e ANTHROPIC_API_KEY=... -e OPENAI_API_KEY=...`,
# не хардкодьте их в образе.
ENTRYPOINT ["python", "main.py"]
