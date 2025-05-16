from telegram import Bot
from config import ADMIN_CHAT_ID, TOKEN

async def send_alert_to_admin(chat_id: int, service: str, details: str):
    bot = Bot(token=TOKEN)
    alert_text = f"🚨 Nueva solicitud:\nServicio: {service}\nChat ID: {chat_id}\nDetalles: {details}"
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=alert_text)
