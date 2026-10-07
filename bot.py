import json
import os
from pathlib import Path

import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.environ["ADMIN_ID"])
SITE_URL = "https://nonelock.github.io/pc-builder/"
DATA_FILE = Path("bot_data.json")

if not BOT_TOKEN:
    raise RuntimeError("Не найдена переменная окружения BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def load_data():
    if not DATA_FILE.exists():
        return {"admin_id": None, "report_waiting": []}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"admin_id": None, "report_waiting": []}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🖥 Открыть конфигуратор", url=SITE_URL))
    markup.add(
        types.InlineKeyboardButton("🐞 Сообщить об ошибке", callback_data="report"),
        types.InlineKeyboardButton("ℹ️ О проекте", callback_data="about"),
    )
    return markup


def send_menu(chat_id, text=None):
    text = text or (
        "👋 <b>Добро пожаловать в PC Сборщик!</b>\n\n"
        "Открой конфигуратор, подбери комплектующие и сообщи об ошибке в данных."
    )
    bot.send_message(chat_id, text, reply_markup=keyboard())


@bot.message_handler(commands=["start"])
def start(message):
    data = load_data()
    if data.get("admin_id") is None:
        data["admin_id"] = message.from_user.id
        save_data(data)
        bot.send_message(message.chat.id, "✅ Ты назначен администратором. Отчёты будут приходить сюда.")
    send_menu(message.chat.id)


@bot.message_handler(commands=["site"])
def site(message):
    bot.send_message(message.chat.id, "🖥 Открыть конфигуратор:", reply_markup=keyboard())


@bot.message_handler(commands=["about"])
def about(message):
    bot.send_message(
        message.chat.id,
        "ℹ️ <b>PC Сборщик</b>\n\n"
        "Проект для подбора комплектующих и базовой проверки совместимости ПК. "
        "Перед покупкой обязательно сверяй характеристики на сайте производителя.",
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(message.chat.id, "/start — главное меню\n/site — открыть сайт\n/report — отправить отчёт\n/about — о проекте")


def request_report(chat_id):
    data = load_data()
    waiting = data.get("report_waiting", [])
    if chat_id not in waiting:
        waiting.append(chat_id)
    data["report_waiting"] = waiting
    save_data(data)
    bot.send_message(chat_id, "🐞 Опиши проблему одним сообщением. Например: «Деталь не отображается».")


@bot.message_handler(commands=["report"])
def report_command(message):
    request_report(message.chat.id)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "report":
        request_report(call.message.chat.id)
        bot.answer_callback_query(call.id)
    elif call.data == "about":
        bot.answer_callback_query(call.id)
        about(call.message)


@bot.message_handler(content_types=["text"])
def text(message):
    data = load_data()
    waiting = data.get("report_waiting", [])
    if message.chat.id not in waiting:
        send_menu(message.chat.id, "Используй кнопки меню или команду /help.")
        return
    waiting.remove(message.chat.id)
    data["report_waiting"] = waiting
    save_data(data)
    user = message.from_user
    username = "@" + user.username if user.username else "без username"
    report = (
        "🐞 <b>Новый отчёт</b>\n\n"
        f"<b>От:</b> {user.first_name} ({username})\n"
        f"<b>ID:</b> <code>{user.id}</code>\n\n"
        f"<b>Текст:</b>\n{message.text}"
    )
    admin_id = data.get("admin_id")
    if admin_id:
        try:
            bot.send_message(admin_id, report)
        except Exception:
            pass
    bot.send_message(message.chat.id, "✅ Спасибо! Отчёт отправлен разработчику.")


if __name__ == "__main__":
    print("PC Сборщик бот запущен")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
