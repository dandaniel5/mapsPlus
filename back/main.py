import logging
import os
from typing import List

import aiohttp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

# from pywebpush import webpush, WebPushException

load_dotenv()

MONGO_URL = os.environ["MONGO_URL"]
TOKEN = os.environ["TELEGRAM_TOKEN"]
BACK_URL = os.environ["BACK_URL"]
FRONT_URL = os.environ["FRONT_URL"]

WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = BACK_URL + WEBHOOK_PATH
PAY_BACK_URL = f"{BACK_URL}/p"

DATABASE_NAME = "FMAP"

# Подключение к MongoDB
client = AsyncIOMotorClient(MONGO_URL)
db = client[DATABASE_NAME]

bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()
dp.include_router(router)


# Модель данных для сохранения подписки


class SubscriptionRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class UserState(StatesGroup):
    phone = State()
    email = State()
    lang = State()


class ItemModel(BaseModel):
    name: str
    stock: int
    info: str
    measurement_type: str
    reserved: int
    tags: List[str]
    currency: str
    price: float  # Обновлено поле для цены
    step: int


class CartItemModel(BaseModel):
    name: str
    item: ItemModel
    amount: int


class OrderModel(BaseModel):
    tg_id: int
    name: str
    cart: List[CartItemModel]
    totalCost: float


app = FastAPI()
origins = [
    "http://localhost:3000",
    "localhost:3000",
    f"{BACK_URL}",
    FRONT_URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

favicon_path = 'favicon.ico'
robots_path = 'robots.txt'

# Создаем логгер для FastAPI
logger = logging.getLogger("fastapi")

# Настраиваем обработчики логов
logging.basicConfig(
    level=logging.DEBUG,  # Уровень логирования
    # Формат сообщения
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",  # Формат даты и времени
    filename="app.log",  # Имя файла для сохранения логов
    filemode="a"  # Режим записи в файл (append)
)

# Добавляем обработчик логов FastAPI к настроенному логгеру
logger.addHandler(logging.StreamHandler())


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


@app.get('/robots.txt', include_in_schema=False)
async def favicon():
    return FileResponse(robots_path)


@app.get("/api/userObj")
async def root(tg_id: str):
    userObj = await db.Users.find_one({"tg_id": tg_id}, {"_id": 0})
    if not userObj:
        raise HTTPException(status_code=404, detail="User not found")

    return JSONResponse(content={
        "message": "Hello World",
        "userObj": userObj
    })


async def alert_user(tg_id, alert):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {
        "chat_id": f"{tg_id}",
        "text": f"{alert}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                logger.info("Message sent successfully")
            else:
                logger.info(
                    f"Failed to send message. Status code: {response.status}")


async def alert_danil(msg: str = "забыл ввести текст"):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {
        "chat_id": f"{219045984}",
        "text": f"{msg}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                logger.info("Message sent successfully")
            else:
                logger.info(
                    f"Failed to send message. Status code: {response.status}")


@app.post(WEBHOOK_PATH)
async def bot_webhook(update: dict):
    telegram_update = types.Update(**update)
    await dp.feed_update(bot=bot, update=telegram_update)


@app.on_event("startup")
async def on_startup():
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(
            url=WEBHOOK_URL
        )


@app.on_event("shutdown")
async def on_shutdown():
    # await bot.get_session()
    await bot.session.close()
    logging.info("Bot stopped")


@router.message(CommandStart())
async def new_message(message: types.Message, state: FSMContext) -> None:
    tg_id = message.from_user.id
    builder = InlineKeyboardBuilder()
    builder.button(text='Welcome to friendly map bot',
                   web_app=WebAppInfo(resize_keyboard=True, url=f'{FRONT_URL}?={tg_id}'))
    await bot.send_message(message.chat.id, text="open map",
                           reply_markup=builder.as_markup())


async def is_user_in_db_USERS(tg_id):
    if await db.Users.find_one({"tg_id": f"{tg_id}"}):
        return True
    else:
        False


async def is_user_anlerts_on(tg_id):
    if await db.Users.find_one({"tg_id": f"{tg_id}", "anlerts_on": True}):
        return True
    else:
        return False


async def lang_in_db(tg_id):
    data = await db.Users.find_one({'tg_id': str(tg_id)}, {'_id': 0, 'lang': 1})
    if data and 'lang' in data:
        return True
    else:
        return False


async def add_user_to_db_USERS(tg_id):
    try:
        await db.Users.insert_one({"tg_id": f"{tg_id}", "anlerts_on": False})
    except Exception as e:
        print(e)


async def init_user(tg_id):
    if not await is_user_in_db_USERS(tg_id):
        await add_user_to_db_USERS(tg_id)
