from aiogram import Router
from aiogram.types import Message
from groq import AsyncGroq

from app.settings import secrets, bot
from app.utils.opening_hours import check_opening_hours  # Импортируем функцию проверки времени
from app.views import system_prompt

router = Router()
client = AsyncGroq(api_key=secrets.groq_api_key)


def format_schedule(opening_hours) -> str:
    """Функция переводит интервалы Telegram в читаемый текст для нейросети"""
    if not opening_hours or not hasattr(opening_hours, "opening_hours") or not opening_hours.opening_hours:
        return "График работы свободный или не настроен."

    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    lines = []

    for interval in opening_hours.opening_hours:
        start_day = (interval.opening_minute // 1440) % 7
        start_hour = (interval.opening_minute % 1440) // 60
        start_min = (interval.opening_minute % 1440) % 60

        end_day = (interval.closing_minute // 1440) % 7
        end_hour = (interval.closing_minute % 1440) // 60
        end_min = (interval.closing_minute % 1440) % 60

        time_str = f"{start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d}"
        if start_day == end_day:
            lines.append(f"• {days[start_day]}: {time_str}")
        else:
            lines.append(
                f"• С {days[start_day]} {start_hour:02d}:{start_min:02d} до {days[end_day]} {end_hour:02d}:{end_min:02d}"
            )

    tz_str = f"\nЧасовой пояс: {opening_hours.time_zone_name}" if hasattr(opening_hours, "time_zone_name") else ""
    return "\n".join(lines) + tz_str


@router.business_message()
async def business_message_handler(message: Message):
    try:
        # Проверяем, что ID бизнес-соединения вообще существует в сообщении
        if not message.business_connection_id:
            return

        # 1. Запрашиваем информацию о бизнес-соединении
        business_conn = await bot.get_business_connection(business_connection_id=message.business_connection_id)

        # 2. Рабочие часы привязаны к чату аккаунта. Запрашиваем полную информацию о чате владельца бизнеса.
        chat_info = await bot.get_chat(chat_id=business_conn.user_chat_id)
        opening_hours = chat_info.business_opening_hours

        # 3. Проверяем рабочие часы.
        # Если часы не настроены в Telegram вообще ИЛИ если check_opening_hours вернула False (сейчас рабочее время)
        if not opening_hours or not check_opening_hours(opening_hours):
            print("⏱ Сейчас рабочее время (или часы работы не настроены в ТГ). Бот молчит.")
            return  # Выходим из функции, бот ничего не отвечает

    except Exception as e:
        print(f"⚠️ Ошибка при проверке рабочих часов: {e}")
        return

    # --- ВСЁ ЧТО НИЖЕ — СРАБОТАЕТ ТОЛЬКО В НЕРАБОЧЕЕ ВРЕМЯ ---

    # Оформляем имя пользователя для логов
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID {message.from_user.id}"
    print(f"📥 Нерабочее время! Бот поймал сообщение от {user_info}: {message.text}")

    # Создаем текстовое описание графика для ИИ
    schedule_text = format_schedule(opening_hours)

    try:
        print("🤖 Отправляем запрос в Groq API...")
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt(schedule_text)},  # Передаем график работы в промпт
                {"role": "user", "content": message.text},
            ],
        )
        answer = response.choices[0].message.content
        print(f"🎯 Ответ от Groq получен: {answer}")

        # ХАК ДЛЯ MARKDOWN: экранируем подчёркивания, чтобы Telegram их не съедал
        safe_answer = answer.replace("_", "\\_")

        # Отправляем ответ в рамках того же бизнес-соединения
        await bot.send_message(
            chat_id=message.chat.id, text=safe_answer, business_connection_id=message.business_connection_id
        )
        print("📤 Ответ успешно отправлен пользователю!")

    except Exception as e:
        print(f"❌ Ошибка в блоке Groq или при отправке сообщения: {e}")
