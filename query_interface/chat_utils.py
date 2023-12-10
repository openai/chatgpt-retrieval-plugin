from typing import Any, List, Dict
import openai
import requests
import logging
import os
from dotenv import load_dotenv


load_dotenv()

DATABASE_INTERFACE_BEAR_TOKEN = os.getenv("BEARER_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

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
        You are a Vietnamese agricultural expert, trying to explain things in simple terms to Vietnamese farmers.
        By only considering the above input from me, answer the following question in Vietnamese: {question}.
        You are designed to provide accurate information in Vietnamese to questions that are based on the input given.
        If the information directly or indirectly exists in the input, the response must reflect that.
        However, if the information does not exist in the input, you can make up information that is consistent with the input.
    """
    
    return prompt



def apply_queries_prompt_template(question: str) -> str:
    """
        A helper function that applies additional template on user's question.
        Prompt engineering could be done here to improve the result. Here I will just use a minimal example.
    """
    prompt = f"""
        You have a vector database of agricultural information.
        You are trying to answer the question: {question}.
        Please come up with at most 3 queries in english for the database which will help you to answer the question above.
        Please do not number them, and organise them separated by newlines. Do not provide justification for the questions.
        Here is an example of a good query: "What is the best way to grow durian trees?"
    """
    
    return prompt

def get_queries(user_question: str) -> List[str]:
    """
    Generates queries for the vector database
    """
    try:
        messages = [{
            "role": "user",
            "content": apply_queries_prompt_template(user_question)
        }]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=messages,
            max_tokens=1024,
            temperature=0.1,  # High temperature leads to a more creative response.
        )

        queries = response["choices"][0]["message"]["content"].split("\n")

        filtered_queries = [s.split('. ', 1)[1] if s.split('. ')[0].isdigit() else s for s in queries]
        
        return filtered_queries
    except Exception as e:
        print(e)

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

    if len(chunks) == 0:
        return "Có thể đã xảy ra lỗi. Vui lòng thử lại."
    
    logging.info("User's questions: %s", user_question)
    logging.info("Retrieved chunks: %s", chunks)
    
    response = call_chatgpt_api(user_question, chunks)
    logging.info("Response: %s", response)
    
    return response["choices"][0]["message"]["content"]

if __name__ == "__main__":
    print(get_queries("What disease causes yellow leaves on my durian tree?"))