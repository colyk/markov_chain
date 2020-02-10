import logging
import os
import os.path as op
import random

import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from markov_chain import MarkovChain, MarkovState
from text_propabilities import get_words_propabilities


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BAD_FILE_ERROR = "Bad file."
MAX_SENTENCE_COUNT = 100
MIN_SENTENCE_COUNT = 1


def send_typing_action(func):
    def wrapper(self, update, context):
        context.bot.send_chat_action(
            chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING
        )
        func(self, update, context)

    return wrapper


class Bot:
    def __init__(self):
        self.token = os.getenv("telegram_token")
        if self.token is None:
            logger.error('Set "telegram_token" environment variable.')
            logger.error("export telegram_token=example_token")
            exit(os.EX_CONFIG)

        self.last_command = ""
        self.sentence_count = 5
        self.updater = Updater(self.token, use_context=True)
        self.set_commands_handlers()

        self.static_dir = op.join(".", "static")
        if not op.isdir(self.static_dir):
            os.mkdir(self.static_dir)

    def local_run(self):
        self.updater.start_polling()
        self.updater.idle()

    def web_run(self):
        port = int(os.environ.get("PORT", 5000))
        self.updater.start_webhook(
            listen="0.0.0.0", port=port, url_path=self.token,
        )
        self.updater.bot.setWebhook(
            "https://markov-chain-bulgakov.herokuapp.com/{}".format(self.token)
        )
        self.updater.idle()

    def text_to_channel(self, chat_id, text):
        self.updater.bot.sendMessage(chat_id=chat_id, text=text)

    def set_commands_handlers(self):
        dp = self.updater.dispatcher

        dp.add_handler(CommandHandler("start", self.on_start))
        dp.add_handler(CommandHandler("help", self.on_help))
        dp.add_handler(CommandHandler("load", self.on_load))
        dp.add_handler(CommandHandler("list", self.on_list))
        dp.add_handler(CommandHandler("markov", self.on_markov))
        dp.add_handler(CommandHandler("setSentenceCount", self.on_set_sentence_count))

        dp.add_handler(MessageHandler(Filters.text, self.on_unknown))

        dp.add_handler(MessageHandler(Filters.document, self.on_file))
        dp.add_error_handler(self.on_error)

    def on_start(self, update, context):
        self.on_help(update, context)
        self.last_command = ""

    def on_help(self, update, context):
        help_text = (
            "/load - load new file\n"
            "/list - list of available files\n"
            "/markov - generate text using markov chain\n"
            "/setSentenceCount - set sentence count\n"
        )
        update.message.reply_text(help_text)
        self.last_command = ""

    @send_typing_action
    def on_unknown(self, update, context):
        msg = update.message.text

        if self.last_command == "markov":
            r = self.calc_markov(op.join(self.user_dir(update), msg))
            update.message.reply_text(r)
        elif self.last_command == "sentence_count":
            try:
                sentence_count = int(msg)
            except Exception as e:
                update.message.reply_text("Bad value.")
            else:
                if MIN_SENTENCE_COUNT < int(msg) < MAX_SENTENCE_COUNT:
                    self.sentence_count = int(msg)
                update.message.reply_text(f"New sentence count: {self.sentence_count}")
        else:
            update.message.reply_text(f'on unknown command "{msg}"')
        self.last_command = ""

    def on_error(self, update, context):
        logger.warning('Update "%s" caused error "%s"', update, context.error)
        self.last_command = ""

    def on_load(self, update, context):
        update.message.reply_text(f"Load your file.")
        self.last_command = ""

    def on_file(self, update, context):
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
        file = context.bot.getFile(file_id)
        file.download(op.join(self.user_dir(update), file_name))
        update.message.reply_text(f"File successfully downloaded.")
        self.last_command = ""

    def on_list(self, update, context):
        files = ", ".join(os.listdir(self.user_dir(update)))
        update.message.reply_text(files)
        self.last_command = ""

    def on_markov(self, update, context):
        self.last_command = "markov"

        menu_keyboard = [os.listdir(self.user_dir(update))]
        menu_markup = telegram.ReplyKeyboardMarkup(
            menu_keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        self.updater.bot.sendMessage(
            chat_id=update.message.chat_id,
            text="Choose file:",
            reply_markup=menu_markup,
        )

    def calc_markov(self, file):
        try:
            with open(file, encoding="utf-8") as f:
                propabilities = get_words_propabilities(f.read())
        except FileNotFoundError:
            return BAD_FILE_ERROR

        init_word = random.choice(list(propabilities.keys()))
        mc = MarkovChain(MarkovState(init_word), history=200)
        for word, prop in propabilities.items():
            state_1 = MarkovState(word)
            for word_2, value in prop.items():
                state_2 = MarkovState(word_2)
                mc.add_probability(state_1, state_2, value)

        words_treshold = self.sentence_count * 25
        result = "."
        for word in mc:
            if result.count(".") > self.sentence_count:
                break
            if result.count(" ") > words_treshold:
                return BAD_FILE_ERROR
            if result.endswith("."):
                word = word.capitalize()
            result += f" {word}"

        return f"Started from word: {init_word}\n{result[1:]}"

    def user_dir(self, update):
        user_dir_path = op.join(self.static_dir, str(update.message.chat_id))
        if not op.isdir(user_dir_path):
            os.mkdir(user_dir_path)
            example_file = op.join(".", "example_text.txt")
            os.link(example_file, op.join(user_dir_path, "example_OSHO"))
        return user_dir_path

    def on_set_sentence_count(self, update, context):
        self.last_command = "sentence_count"

        response = f"Old sentence count: {self.sentence_count}\nProvide new value"
        update.message.reply_text(response)


if __name__ == "__main__":
    bot = Bot()
    bot.local_run()
