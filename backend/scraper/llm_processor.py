import re
import logging
from langchain_ollama import OllamaLLM

ollama_llm = OllamaLLM(model="llama3")
logger = logging.getLogger(__name__)

def get_relevance_score(text: str, keyword: str) -> float:
    """
    Analyze the given text and assign a rigorous relevance score for the keyword,
    considering that we are specifically looking for contact information and file/document references.
    """
    prompt = (
        f"Your goal is to analyze the following text and rigorously evaluate its relevance to the keyword '{keyword}'.\n\n"
        "Instructions:\n"
        "1. If the text contains clear contact information (such as name, email, phone) or direct references to files/documents related to the keyword, "
        "assign a high score.\n"
        "2. If the text is ambiguous, irrelevant, or does not provide any contact or file-related information, assign a low score.\n"
        "3. Use a scale from 0 to 100, where 100 means the text is extremely relevant and 0 means there is no relevance.\n"
        "4. Return ONLY the number, with no additional commentary or text.\n\n"
        f"Text: {text}\n\nScore:"
    )
    try:
        response = ollama_llm.invoke(prompt).strip()
        logger.info(f"LLM response: {response}")
        
        # Extract the first number found in the response
        match = re.search(r"(\d+(?:\.\d+)?)", response)
        if match:
            score_raw = float(match.group(1))
            # Convert the score to a range of 0 to 1 (by dividing by 100)
            score = max(0.0, min(score_raw / 100.0, 1.0))
        else:
            score = 0.0
    except Exception as e:
        logger.error(f"Error obtaining LLM score: {e}")
        score = 0.0
    return score

def classify_link_type(text: str) -> str:
    prompt = f"""Analyze this link text and classify it into one of these categories:
    - document: for files, reports, budgets, policies, forms
    - contact: for contact information, staff directories, departments
    - service: for public services, applications, permits
    - news: for news, announcements, updates
    - unknown: if none of the above apply
    
    Link text: "{text}"
    
    Return only the category name, nothing else."""

    try:
        response = ollama_llm.invoke(prompt).strip()
        logger.info(f"Link classification response: {response}")
        
        category = response.strip().lower()
        if category in ['document', 'contact', 'service', 'news', 'unknown']:
            return category
        return 'unknown'
    except Exception as e:
        logger.error(f"Error classifying link type: {e}")
        return 'unknown'