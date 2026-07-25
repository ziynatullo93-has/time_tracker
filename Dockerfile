FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn

COPY . .

EXPOSE 10000

ENTRYPOINT ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
CMD ["--port", "10000"]