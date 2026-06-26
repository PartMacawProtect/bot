from aiogram import Router
from aiogram.types import Message
from groq import AsyncGroq
import json

from app.settings import secrets, bot
from app.views import system_prompt
from app.utils.opening_hours import check_opening_hours

router = Router()
client = AsyncGroq(api_key=secrets.groq_api_key)


@router.business_message()
async def business_message_handler(message: Message):
    print(f"📨 Полный объект message: {json.dumps(message.model_dump(), indent=2, default=str)}")
    
    try:
        # Проверяем есть ли opening_hours в самом message
        if hasattr(message, 'business_connection_id'):
            print(f"✅ business_connection_id: {message.business_connection_id}")
        
        # Пытаемся получить opening_hours из message
        opening_hours = getattr(message, 'opening_hours', None)
        if opening_hours:
            print(f"✅ opening_hours найдены в message: {opening_hours}")
            if not check_opening_hours(opening_hours):
                print("⏱ Сейчас рабочее время. Бот молчит.")
                return
        else:
            print("⚠️ opening_hours не найдены в message, отвечаем на все сообщения")

    except Exception as e:
        print(f"⚠️ Ошибка при проверке рабочих часов: {e}")
        import traceback
        traceback.print_exc()

    # --- ОТВЕЧАЕМ НА СООБЩЕНИЕ ---
    print(f"📥 Бот поймал сообщение от @{message.from_user.username}: {message.text}")

    try:
        print("🤖 Отправляем запрос в Groq API...")
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content
        print(f"🎯 Ответ от Groq получен: {answer}")

        await bot.send_message(
            chat_id=message.chat.id,
            text=answer,
            business_connection_id=message.business_connection_id
        )
        print("📤 Ответ успешно отправлен!")

    except Exception as e:
        print(f"❌ Ошибка в блоке Groq или отправки: {e}")

