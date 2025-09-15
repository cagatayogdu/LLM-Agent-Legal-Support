import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()

def _create_gpt():
    api_key = os.getenv("OPENAI_API_KEY")
    return ChatOpenAI(
        model_name="gpt-4o-mini",
        openai_api_key=api_key,
        temperature=0.4,
        request_timeout=60
    )
