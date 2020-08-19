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
qa_file = f"qa.json"

def check_bot(message):
    if message.from_user.is_bot:
        bot.kick_chat_member(message.chat.id, message.from_user.user_id)
        return False
    return True


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
            s3.download_fileobj(BUCKET_NAME, idea_file, f)

    # Parse message -> insert to file -> upload to S3
    with open(idea_file, "a+") as f:
        words = message.text.split("/idea ")[1]
        f.write(f"From {message.chat.username}: {words}\n\n")

    with open(idea_file, "rb") as f:
        s3.upload_fileobj(f, BUCKET_NAME, idea_file)


@bot.message_handler(commands=["help_me"])
def help_me(message):
    if not os.path.exists(qa_file):
            with open(qa_file, "wb") as f:
                s3.download_fileobj(BUCKET_NAME, qa_file, f)

    # I don't know why, but here 'with' statement doesn't work
    f = open(qa_file, "r")
    data = json.load(f)
    f.close()
    q = message.text.split("/help_me ")

    if len(q) < 2:
        bot.send_message(message.chat.id, "Repeat command with question, please")
    else:
        q = q[1]
        q_id = abs(hash(q)) % (10 ** 8)
        # TODO search algorithm and run search of patterns in another thread
        # Search question ID in list of all IDs
        if q_id not in [int(i["id"]) for i in data["qa"]]:
            # If not present, then and new question entry and send my message with question
            data["qa"].append({"id": q_id, "question": q, "answer": ""})
            sorted(data["qa"], key=lambda i: i["id"])

            f = open(qa_file, "w")
            json.dump(data, f)
            f.close()
            # with open(qa_file, "rb") as f:
            #     s3.upload_fileobj(f, BUCKET_NAME, qa_file)

            markup = types.InlineKeyboardMarkup(row_width=2)

            cb_data_send = f"send#{message.chat.id}" 
            # If message is not from private chat, then username would be saved
            # to ping user in future
            if message.chat.type != "private":
                cb_data_send += f"|{message.from_user.username}"

            markup.add(
                types.InlineKeyboardButton("Answer", 
                                           callback_data=f"answer#{q_id}"),
                types.InlineKeyboardButton("Send", 
                                           callback_data=cb_data_send),
            )
            bot.send_message(my_chat_id, 
                            f"Question from {message.from_user.username}: {q}",
                            reply_markup=markup)
            bot.reply_to(message, "Thanks for your question. I will answer you as soon as possible")

        else:
            # If ID exists, then send corresponding answer
            answer = [i["answer"] for i in data["qa"] if int(i["id"]) == q_id][0]
            bot.send_message(message.chat.id, answer)


@bot.callback_query_handler(func=lambda call: True)
def process_step(call, *args):
    # Args is used for returning answer from process_answer function
    try:
        step, data = call.data.split("#")
        if step == "answer":
            msg = bot.send_message(my_chat_id, "Type answer")
            bot.register_next_step_handler(msg, process_answer, int(call.data))
        elif step == "send":
            # Split data to extract chat_id and username
            data = data.split("|")
            if len(data) == 1:
                bot.send_message(int(data[0]), f"Hi! Here is answer on your question: {args[0]}")
            else:
                bot.send_message(int(data[0]), f"Hi, @{data[1]}! Here is answer on your question: {args[0]}")
    except ValueError:
        pass


def process_answer(message, q_id):
    with open(qa_file, "w+") as f:
        data = json.load(f)
        entry = [int(entry["id"]) for entry in data["qa"] if int(entry["id"]) == q_id][0]
        index = data["qa"].index(entry)
        entry["answer"] = message.text
        data["qa"][index] = entry
        json.dump(data, f)
    bot.register_next_step_handler(message, process_step, message.text)


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
