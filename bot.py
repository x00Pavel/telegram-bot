import telebot
import os
from flask import Flask, request
import logging
import json
import boto3

TOKEN = os.environ["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)

s3 = boto3.client('s3')
BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
file_name = "posts.json"

def check_bot(message):
    if message.from_user.is_bot:
        bot.kick_chat_member(message.chat.id, message.from_user.user_id)
        return False
    return True

@bot.message_handler(commands=["start", "help"])
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


@bot.message_handler(commands=["all_posts"])
def all_posts(message):
    text = ""
    if not os.path.exists(file_name):
        with open(file_name, "wb") as f:
            s3.download_fileobj(BUCKET_NAME, file_name, f)
        
    with open(file_name, "r") as f:
        data = json.load(f)
        for post in data["posts"]:
            text = text + f"{post[0]} - {post[1]}\n"
    bot.send_message(message.chat.id, "Posts are:\n" + text)

        
@bot.message_handler(commands=["add_post"])
def add_post(message):
    if message.chat.username == "plov_ec":
        # Download file if it does not exist - only in first use after restart
        if not os.path.exists(file_name):
            with open(file_name, "wb") as f:
                s3.download_fileobj(BUCKET_NAME, file_name, f)

        # Parse message -> insert to file -> upload to S3
        with open(file_name, "w+") as f:
            data = json.load(f)
            words = message.chat.text.split("/add_message").split("|")
            data["posts"].append([words[0], words[1]])
            json.dump(data, f)

        with open(file_name, "rb") as f:
            s3.upload_fileobj(f, BUCKET_NAME, file_name)

    else:
        bot.send_message(message.chat.id, f"Sorry, {message.chat.username}, you can't add posts")


# @bot.message_handler(commands=["reminder"])
# def reminder(message):
#     text = message.chat.text 


if int(os.environ["HEROKU"]) == 1:
    logger = telebot.logger
    telebot.logger.setLevel(logging.DEBUG)

    server = Flask(__name__)
    @server.route('/' + TOKEN, methods=['POST'])
    def getMessage():
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "!", 200

    # @server.route("/")
    # def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f'https://morning-beach-95188.herokuapp.com/{TOKEN}') # этот url нужно заменить на url вашего Хероку приложения
        # return "?", 200
    server.run(host="0.0.0.0", port=os.environ.get('PORT', 80))
else:
    bot.remove_webhook()
    bot.polling()