import dotenv
import os


dotenv.load_dotenv()


class Config():
    ADMIN_EMAIL=os.environ.get("ADMIN_EMAIL")
    ADMIN_FULLNAME=os.environ.get("ADMIN_FULLNAME")
    ADMIN_PASSWORD =os.environ.get("ADMIN_PASSWORD ")
    DB_HOST=os.environ.get("DB_HOST")
    DB_PORT=os.environ.get("DB_PORT")
    DB_NAME=os.environ.get("DB_NAME")
    DB_USER=os.environ.get("DB_USER")
    DB_PASSWORD=os.environ.get("DB_PASSWORD")
    RANDOM_SECRET=os.environ.get("RANDOM_SECRET")
    REDIS_HOST=os.environ.get("REDIS_HOST")
    REDIS_PORT=os.environ.get("REDIS_PORT")
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


config = Config()
