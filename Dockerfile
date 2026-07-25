FROM python:3.11-slim

WORKDIR /app

# Принудительно ставим fastapi и uvicorn прямо при сборке образа
RUN pip install --no-cache-dir fastapi uvicorn

# Копируем остальной код
COPY . .

# Запуск через системный порт Render
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]