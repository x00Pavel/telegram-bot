import telebot
from telebot import types
import os
from flask import Flask, request
import logging
import json
import boto3


BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
ENV = os.environ["ENV"] if "ENV" in os.environ.keys() else "stage"
TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"] if "WEBHOOK_URL" in os.environ.keys() else None


bot = telebot.TeleBot(TOKEN)
my_chat_id = 320130425 # for sending some messages to me
s3 = boto3.client('s3')

posts_file = f"posts.json"
idea_file = f"ideas.txt"


@bot.message_handler(commands=["start", "help"])
def help(message):
    """Send a message when the command /help or /start 
    are sent."""
    if message.from_user.username == "plov_ec" and \
        message.chat.type == "private":
        global my_chat_id
        my_chat_id = message.chat.id
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
    if not os.path.exists(posts_file):
        with open(posts_file, "wb") as f:
            s3.download_fileobj(BUCKET_NAME, f"{ENV}/{posts_file}", f)

        
    with open(posts_file, "r") as f:
        data = json.load(f)
        for post in data["posts"]:
            text = text + f"{post[0]} - {post[1]}\n"
    bot.send_message(message.chat.id, "All posts:\n" + text)

        
@bot.message_handler(commands=["add_post"])
def add_post(message):
    if message.chat.username == "plov_ec":
        # Download file if it does not exist - only in first use after restart
        if not os.path.exists(posts_file):
            with open(posts_file, "wb") as f:
                s3.download_fileobj(BUCKET_NAME, posts_file, f)

        # Parse message -> insert to file -> upload to S3
        with open(posts_file, "w+") as f:
            data = json.load(f)
            words = message.text.split("/add_post ").split("|")
            data["posts"].append([words[0], words[1]])
            json.dump(data, f)

        with open(posts_file, "rb") as f:
            s3.upload_fileobj(f, BUCKET_NAME, posts_file)

    else:
        bot.send_message(message.chat.id, 
        f"Sorry, {message.chat.username}, you can't add posts")


@bot.message_handler(commands=["idea"])
def idea(message):
    # If user have any idea how to improve or what he want to add to bot 
    if not os.path.exists(idea_file):
        with open(idea_file, "wb") as f:
            s3.download_fileobj(BUCKET_NAME, f"{ENV}/{idea_file}", f)

    # Parse message -> insert to file -> upload to S3
    with open(idea_file, "a+") as f:
        words = message.text.split("/idea ")[1]
        f.write(f"From {message.chat.username}: {words}\n\n")

    with open(idea_file, "rb") as f:
        s3.upload_fileobj(f, BUCKET_NAME, f"{ENV}/{idea_file}")



if "LOCAL" in os.environ.keys():
    bot.remove_webhook()
    bot.polling()
else:
    logger = telebot.logger
    telebot.logger.setLevel(logging.DEBUG)

    server = Flask(__name__)
    @server.route('/' + TOKEN, methods=['POST'])
    def getMessage():
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "!", 200

    bot.remove_webhook()
    bot.set_webhook(url=f'{WEBHOOK_URL}/{TOKEN}')
    server.run(host="0.0.0.0", port=os.environ.get('PORT', 80))
