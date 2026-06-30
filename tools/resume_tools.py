from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_mistralai import ChatMistralAI

from agent.prompts import SKILL_EXTRACTION_PROMPT
from config import settings
from utils import safe_json_loads


_llm = ChatMistralAI(
    model=settings.MISTRAL_MODEL,
    temperature=settings.TEMPERATURE,
    api_key=settings.MISTRAL_API_KEY
)


def load_resume_text(file_path: str) -> str:
    """Load and extract text from a PDF resume."""
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    return "\n".join([page.page_content for page in pages])


def extract_skills_from_resume(resume_text: str) -> dict:
    """Use LLM to extract structured info from resume."""
    prompt = SKILL_EXTRACTION_PROMPT.format(resume_text=resume_text)
    response = _llm.invoke(prompt)
    return safe_json_loads(response.content)


@tool
def load_resume(file_path: str) -> str:
    """Load and read a PDF resume. Input: file path."""
    try:
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        return "\n".join([p.page_content for p in pages])
    except Exception as e:
        return f"Error: {str(e)}"