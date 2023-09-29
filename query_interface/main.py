import logging
import openai
from chat_utils import ask
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    while True:
        user_query = input("Enter your question: ")
        openai.api_key = os.getenv("OPENAI_API_KEY")
        logging.basicConfig(level=logging.WARNING,
                            format="%(asctime)s %(levelname)s %(message)s")

        first_query = ask(user_query).split("!MoreQuestion!")
        answer = first_query[0].strip()
        if len(first_query) > 1:
            follow_up = first_query[-1].strip()
            second_query = ask(follow_up).split("!MoreQuestion!")
            answer = f"{answer}\n\nMore question: {follow_up}\n{second_query[0]}".strip()
        print(answer)
