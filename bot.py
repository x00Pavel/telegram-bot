import telebot
import os
from flask import Flask, request
import logging
import json

TOKEN = os.environ["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)


def check_bot(message):
    if message.from_user.is_bot:
        bot.kick_chat_member(message.chat.id, message.chat.user_id)
        return False
    return True


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, f"Hello {message.chat.username}")
    # help(message)

@bot.message_handler("help")
def help(message):
    """Send a message when the command /help is issued."""
    text = f"""
    Hello, {message.chat.username}!
    I'm helper bot for channel t.me/vut_fit.
    Here is my command that can help you:
    /all_posts - to show all usefull posts in channel
    
    Pleas, remember, I'm still under development
    Thanks!
    """
    bot.send_message(message.chat.id, text)


@bot.message_handler("all_posts")
def all_posts(message):
    text = ""
    with open("./posts.json", "r") as f:
        data = json.load(f)
        for post in data["posts"]:
            text = text + f"{post[0]} - {post[1]}\n"
    bot.send_message(message.chat.id, "Posts are:\n" + text)

        
@bot.message_handler("add_post")
def add_post(message):
    if message.chat.username == "plov_ec":
        data = []
        with open("./posts.json", "r") as f:
            data = json.load(f)
        data["posts"].append(["link", "description"])
        with open("./posts.json", "w") as f:
            json.dump(data, f)
    else:
        bot.send_message(message.chat.id, f"Sorry, {message.chat.username}, you can't add posts")


@bot.message_handler("reminder")
def reminder(message):
    text = message.chat.text 




if "HEROKU" in list(os.environ.keys()):
    logger = telebot.logger
    telebot.logger.setLevel(logging.DEBUG)

    server = Flask(__name__)
    @server.route("/bot", methods=['POST'])
    def getMessage():
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "!", 200
    
    @server.route(f"/{TOKEN}", methods=['POST'])
    def webhook():
        bot.remove_webhook()
        bot.set_webhook(url=f'https://morning-beach-95188.herokuapp.com/bot') # этот url нужно заменить на url вашего Хероку приложения
        return "?", 200
    server.run(host="0.0.0.0", port=os.environ.get('PORT', 80))
else:
    bot.remove_webhook()
    print(bot.token)
    bot.polling(none_stop=True, interval=100)