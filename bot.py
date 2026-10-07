import os
import logging
import threading
from html import escape

import telebot
from telebot import types

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["BOT_TOKEN"].strip()
ADMIN_ID = int(os.environ["ADMIN_ID"].strip())
SITE_URL = "https://nonelock.github.io/pc-builder/"
bot = telebot.TeleBot(TOKEN)
waiting = set()
lock = threading.Lock()


def menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🗝️ Открыть конфигуратор", url=SITE_URL))
    markup.add(types.InlineKeyboardButton("🌍 Сообщить об ошибке", callback_data="report"))
    markup.add(types.InlineKeyboardButton("❤️ О проекте", callback_data="about"))
    return markup


def begin_report(chat_id):
    with lock:
        waiting.add(chat_id)
    bot.send_message(chat_id, " 🤝 Опиши проблему одним текстовым сообщением. /cancel — отмена.")


@bot.message_handler(commands=["start", "site", "help"])
def start(message):
    if message.chat.type != "private":
        bot.reply_to(message, "Напиши боту в личные сообщения.")
        return
    text = "Добро пожаловать в PC Сборщик!"
    if message.from_user.id == ADMIN_ID:
        text += "\nТы администратор этого бота."
    bot.send_message(message.chat.id, text, reply_markup=menu())


@bot.message_handler(commands=["id"])
def show_id(message):
    bot.reply_to(message, f"Твой Telegram ID: {message.from_user.id}")


@bot.message_handler(commands=["report"])
def report_command(message):
    if message.chat.type == "private":
        begin_report(message.chat.id)


@bot.message_handler(commands=["cancel"])
def cancel(message):
    with lock:
        waiting.discard(message.chat.id)
    bot.reply_to(message, "Отменено.")


@bot.message_handler(commands=["about"])
def about(message):
    bot.send_message(message.chat.id, "PC Сборщик — подбор деталей и базовые проверки совместимости. Характеристики нужно сверять с документацией производителей.")


@bot.callback_query_handler(func=lambda call: call.data in ["report", "about"])
def callback(call):
    bot.answer_callback_query(call.id)
    if call.message and call.message.chat.type == "private":
        if call.data == "report":
            begin_report(call.message.chat.id)
        else:
            about(call.message)


@bot.message_handler(content_types=["text"])
def receive_text(message):
    if message.chat.type != "private":
        return
    with lock:
        pending = message.chat.id in waiting
    if not pending:
        bot.send_message(message.chat.id, "Выбери действие:", reply_markup=menu())
        return
    user = message.from_user
    username = "@" + user.username if user.username else "без username"
    header = (
        "Новый отчёт\n"
        f"От: {escape(user.first_name)} ({escape(username)})\n"
        f"ID: {user.id}\n\n"
    )
    try:
        bot.send_message(ADMIN_ID, header, parse_mode="HTML")
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    except Exception as error:
        detail = str(error).replace(TOKEN, "[TOKEN HIDDEN]")
        logging.error("Report delivery failed: %s: %s", type(error).__name__, detail)
        bot.send_message(message.chat.id, "Отчёт не доставлен. Попробуй позже или /cancel. Причина записана в Logs.")
        return
    with lock:
        waiting.discard(message.chat.id)
    bot.send_message(message.chat.id, "Спасибо! Отчёт доставлен разработчику.")


if __name__ == "__main__":
    print("PC Сборщик бот запущен", flush=True)
    bot.infinity_polling(timeout=30, long_polling_timeout=30)