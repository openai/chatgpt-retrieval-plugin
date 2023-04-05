from services.openai import get_chat_completion
from models.models import Document

NUM_MIN_WORDS_FOR_SUMMARY = 10

def get_summary(document: Document, num_words: int) -> Document:
    """Summarize the given document by using at most {num_words}"""

    assert num_words >= NUM_MIN_WORDS_FOR_SUMMARY, f"num_words must be greater than {NUM_MIN_WORDS_FOR_SUMMARY}"

    summary = _get_summary(document.text, num_words)
    return Document(
        id=document.id,
        metadata=document.metadata,
        text=summary,
    )

def _get_summary(text: str, num_words: int) -> str:
    """Summarize the given text by using at most {num_words}"""

    messages = [
        {
            "role": "system",
            "content": f"""
            Your task is to summarize the text by using at most {num_words} words while preserving the meaning of the text as much as possible.
            If the text is already fewer than {num_words} words or cannot be summarized give me the text as it is.
            Your only possible responses are either the initial text or its summary.
            Do not explain your response. Do not tell me how many words the text has.
            """,
        },
        {"role": "user", "content": text},
    ]

    return get_chat_completion(messages)
