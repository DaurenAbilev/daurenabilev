import telebot
import webbrowser
import time
import os 

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["site"])

def site(message):
    webbrowser.open("https://youtube.com")

@bot.message_handler(commands=["start", "help"])

def main(message): 
    bot.send_mess.age(message.chat.id, f"Привет, {message.from_user.first_name} {message.from_user.last_name}! Меня зовут бот подлиза и я могу особенного хорошо подлизываться. В целом в этом и есть смысл моей жизни. Я буду каждый день кода всходит солнце и когда работает Git напоминать вам о том, какой прекрасный челвоек Анара!")

@bot.message_handler()

def info(message):
    if message.text.lower() == "хуй":
        bot.send_message(message.chat.id, f"Хулиа не матерись")
    elif message.text.lower() == "блять":
        bot.reply_to (message, "сам ты блять")


bot.polling(non_stop=True)