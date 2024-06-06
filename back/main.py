import logging
import os
from typing import List
from PIL import Image
from bson.objectid import ObjectId

from aiogram.types import Message

import aiohttp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import WebAppInfo, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.responses import HTMLResponse, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel


from aiogram.types import Location
# from aiogram.types.message import ParseMode
# from pywebpush import webpush, WebPushException

load_dotenv()

MONGO_URL = os.environ["MONGO_URL"]
TOKEN = os.environ["TELEGRAM_TOKEN"]
BACK_URL = os.environ["BACK_URL"]
# FRONT_URL = os.environ["FRONT_URL"]
FRONT_URL = "https://4c0864d7bdec7a.lhr.life"

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

class Item(BaseModel):
    tg_id: int | None = None



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

markers = [
    {"position": [41.695894, 44.801478], "popup": "Wyndham Grand back"}
]

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


@app.get('/robots.txt', include_in_schema=False)
async def favicon():
    return FileResponse(robots_path)


@app.post("/api/userObj")
async def root(item: Item):
    userObj = await db.Users.find_one({"tg_id": item.tg_id}, {"_id": 0})
    if not userObj:
        markers = []
        userObj = await db.Users.insert_one({"tg_id": item.tg_id, "markers": markers})
        userObj = await db.Users.find_one({"_id": userObj.inserted_id}, {"_id": 0})
    
    return JSONResponse(content={
        "message": "Привет, мир!",
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
    await init_user(tg_id)
    builder = InlineKeyboardBuilder()
    builder.button(text='Welcome to friendly map bot',
                   web_app=WebAppInfo(resize_keyboard=True, url=f'{FRONT_URL}/mini?={tg_id}'))
    builder.button(text='add mark',
                   web_app=WebAppInfo(resize_keyboard=True, url=f'{FRONT_URL}/mini?={tg_id}'))
    await bot.send_message(message.chat.id, text="add mark",
                           reply_markup=builder.as_markup())


async def is_user_in_db_USERS(tg_id):
    if await db.Users.find_one({"tg_id": f"{tg_id}"}):
        return True
    else:
        False

 

async def lang_in_db(tg_id):
    data = await db.Users.find_one({'tg_id': str(tg_id)}, {'_id': 0, 'lang': 1})
    if data and 'lang' in data:
        return True
    else:
        return False


async def init_user(tg_id):
    if not await is_user_in_db_USERS(tg_id):
        await db.Users.insert_one({"tg_id": tg_id , "markers": markers})



@app.get("/thumbnail/{image_id}")
async def get_thumbnail(image_id: str):
    if image_id == "None":
        return {404: "Not Found"}
    try:
        # Retrieve the image stream from GridFS by its ID
        stream = await fs.open_download_stream(ObjectId(image_id))

        # Read the image content from the stream
        image_data = await stream.read()

        # Create a Pillow Image object from the image data (using Pillow's Image module explicitly)
        img = Image.open(io.BytesIO(image_data))

        # Get the image dimensions
        width, height = img.size

        # Determine the crop box to get a centered square
        if width > height:
            left = (width - height) / 2
            top = 0
            right = left + height
            bottom = height
        else:
            left = 0
            top = (height - width) / 2
            right = width
            bottom = top + width

        # Crop the image to a centered square
        img_cropped = img.crop((left, top, right, bottom))

        # Resize the cropped image to 720x720
        img_resized = img_cropped.resize((720, 720))

        # Convert the resized image to bytes
        thumbnail_io = io.BytesIO()
        # Change format to WebP
        img_resized.save(thumbnail_io, format="WEBP")

        # Seek to the beginning of the BytesIO object
        thumbnail_io.seek(0)

        # Return the thumbnail image as a StreamingResponse
        # Adjust media type based on image format
        return StreamingResponse(thumbnail_io, media_type="image/webp")
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"File with ID '{image_id}' not found in GridFS.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.callback_query(lambda c: c.data.startswith('q_1'))
async def create_shop_url(call: CallbackQuery):
    product_name = call.data.split('_')[1]
    tg_id = call.from_user.id
    print(tg_id)
    cart_iteem = {
        "name": f"{product_name}",
        "amount": 0,
    }
    await db.Users.update_one({"tg_id": f"{tg_id}"}, {"$push": {"cart": cart_iteem}})
    await call.answer(text=f"Вы добавили в корзину {product_name}, обьем выберете в корзине")
    pass


# алгоритом вопросов 
# первый вопрос + колтуэкшон 
# добрый день, чтобы отставить отзыв
# отправте 
# активируется когда отправляешь геотег 
# дальше открывается карта на ней поевляется точка 
# # ты кнопкой апруваешь что геотег отметился правильно 
# # тут открывается вьюха в картой и прицелом посередине и его можно дивгать и когда сдвинул типа нбновленные данные по нажатию кнопки отправляются на бек и адрес перендривается 
# есои неправильно от отправляешь еще 1 геотег 
# геотег этого места 
# + название если можно в одно сообщение 
# content_types=types.ContentType.LOCATION


@router.message(lambda message: message.location)
async def handle_location(message: Message):
    location = message.location
    latitude = location.latitude
    longitude = location.longitude

    await message.answer(f"You shared your location: Latitude - {latitude}, Longitude - {longitude}")



# фото чека + фото места фотографии 

# оценка 

# нажмите /меню для возврата в меню 



