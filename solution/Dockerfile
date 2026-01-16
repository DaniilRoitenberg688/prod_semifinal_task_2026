# Базовый образ с общими зависимостями
FROM python:3.12.1-alpine3.19 as builder

WORKDIR /app

RUN apk add --no-cache curl

# Устанавливаем системные зависимости

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .


RUN chmod +x run.sh


# Стадия для основного приложения
FROM builder as run
EXPOSE 8000
CMD ["./run.sh"]

