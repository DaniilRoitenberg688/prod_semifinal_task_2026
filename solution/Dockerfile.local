# Базовый образ с общими зависимостями
FROM python:3.11-slim as builder

WORKDIR /app

# Устанавливаем системные зависимости

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .



# Стадия для миграций
FROM builder as migrations
CMD ["alembic", "-c", "./alembic.ini", "upgrade", "head"]

# Стадия для основного приложения
FROM builder as run
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Стадия для разработки
FROM builder as dev
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
