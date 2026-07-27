FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# Копируем весь проект
COPY . .

# Открываем порт для Render
EXPOSE 10000

# Надежный запуск через python-модуль с учетом порта Render
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]