import logging
import openai
from chat_utils import ask
import os

if __name__ == "__main__":
    while True:
        user_query = input("Enter your question: ")
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        logging.basicConfig(level=logging.WARNING,
                            format="%(asctime)s %(levelname)s %(message)s")
        print(ask(user_query))