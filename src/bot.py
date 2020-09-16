from telebot import TeleBot, logger, types
import logging
import os
import boto3
from flask import Flask, request
from json import dump, load


class Bot(TeleBot):
    """
    Class for handling bot operations
    """

    def __init__(self):
        self.BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
        self.ENV = os.environ["ENV"] if "ENV" in os.environ.keys() else "stage"
        self.WEBHOOK_URL = (
            os.environ["WEBHOOK_URL"]
            if "WEBHOOK_URL" in os.environ.keys()
            else None
        )
        self.my_chat_id = 320130425  # for sending some messages to me
        self.s3 = boto3.client("s3")
        self.TOKEN = os.environ["TELEGRAM_TOKEN"]
        super().__init__(self.TOKEN)

    def start_env(self):
        """
        Seetup corresponding environment (dev or prod ) and star bot
        """
        if "LOCAL" in os.environ.keys():
            self.remove_webhook()
            self.polling()
        else:
            # logger = log
            logger.setLevel(logging.DEBUG)

            server = Flask(__name__)

            @server.route("/" + self.TOKEN, methods=["POST"])
            def getMessage():
                self.process_new_updates(
                    [
                        types.Update.de_json(
                            request.stream.read().decode("utf-8")
                        )
                    ]
                )
                return "!", 200

            self.remove_webhook()
            self.set_webhook(url=f"{self.WEBHOOK_URL}/{self.TOKEN}")
            server.run(host="0.0.0.0", port=os.environ.get("PORT", 80))

    def check_bot(self, message):
        if message.from_user.is_bot:
            self.kick_chat_member(message.chat.id, message.from_user.user_id)
            return False
        return True

    def update_data(self, file_name, data):
        # If there is json file, so it should be overwritten, but in case of
        with open(file_name, "w") as f:
            dump(data, f, ensure_ascii=False)

        with open(file_name, "rb") as f:
            self.s3.upload_fileobj(
                f, self.BUCKET_NAME, f"{self.ENV}/{file_name}"
            )

    def get_data(self, file_name) -> list:
        if not os.path.exists(file_name):
            with open(file_name, "wb") as f:
                self.s3.download_fileobj(
                    self.BUCKET_NAME, f"{self.ENV}/{file_name}", f
                )

        with open(file_name, "r") as f:
            if file_name.endswith(".json"):
                return load(f)
            return f.read()
