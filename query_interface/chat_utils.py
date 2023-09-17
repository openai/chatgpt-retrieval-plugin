from typing import Any, List, Dict
import openai
import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_INTERFACE_BEAR_TOKEN = os.getenv("BEARER_TOKEN")

def query_database(query_prompt: str) -> Dict[str, Any]:
    """
    Query vector database to retrieve chunk with user's input questions.
    """
    url = "http://localhost:8000/query"
    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {DATABASE_INTERFACE_BEAR_TOKEN}",
    }
    data = {"queries": [{"query": query_prompt, "top_k": 5}]}

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        # process the result
        return result
    else:
        raise ValueError(f"Error: {response.status_code} : {response.content}")


def apply_prompt_template(question: str) -> str:
    """
        A helper function that applies additional template on user's question.
        Prompt engineering could be done here to improve the result. Here I will just use a minimal example.
    """
    prompt = f"""
        You are an Vietnamese agricultural expert, trying to explain things in simple terms to Vietnamese farmers.
        By only considering the above input from me, answer the question: {question}. If you cannot answer the question based on the input, please say "Tôi không biết".
    """
    
    """
        Bạn là một chuyên gia nông nghiệp Việt Nam, có nhiệm vụ giải thích bằng ngôn từ dễ hiểu cho các nông dân Việt Nam.
        Chỉ từ những dữ liệu được cung cấp bởi tôi ở phía trên, hãy trả lời câu hỏi sau: {question}. Nếu bạn không thể trả lời dựa trên dữ liệu được cung cấp, hãy trả lời "Tôi không biết".
    """

    
    return prompt

def call_chatgpt_api(user_question: str, chunks: List[str]) -> Dict[str, Any]:
    """
    Call chatgpt api with user's question and retrieved chunks.
    """
    # Send a request to the GPT-3 API
    messages = list(
        map(lambda chunk: {
            "role": "user",
            "content": chunk
        }, chunks))
    question = apply_prompt_template(user_question)
    messages.append({"role": "user", "content": question})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=messages,
        max_tokens=1024,
        temperature=0.1,  # High temperature leads to a more creative response.
    )
    return response


def ask(user_question: str) -> Dict[str, Any]:
    """
    Handle user's questions.
    """
    # Get chunks from database.
    chunks_response = query_database(user_question)
    chunks = []
    for result in chunks_response["results"]:
        for inner_result in result["results"]:
            chunks.append(inner_result["text"])
    
    logging.info("User's questions: %s", user_question)
    logging.info("Retrieved chunks: %s", chunks)
    
    response = call_chatgpt_api(user_question, chunks)
    logging.info("Response: %s", response)
    
    return response["choices"][0]["message"]["content"]

