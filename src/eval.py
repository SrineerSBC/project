import os
import re
import requests
from dotenv import load_dotenv
from search_module import google_search  # <-- your search function here

# Load environment variables from .env
load_dotenv()

def evaluate_search_results_with_gemini(results, gemini_api_key, company=None):
    """
    Takes a list of search results and calls Google Gemini to evaluate them.
    Extracts the relevant links from the JSON response and returns them in comma-separated format.
    
    Parameters:
      results (list): List of search results (each a dict with 'title', 'link', 'snippet').
      gemini_api_key (str): Your Google Gemini API key.
      company (str): Optional company name to include in the prompt.
    
    Note (Aus): This version dynamically builds the prompt based on the company name.
    """
    header = f"We have these search results about {company}:\n\n" if company else "We have these search results about the company:\n\n"
    prompt_text = header
    for idx, item in enumerate(results, start=1):
        prompt_text += (
            f"{idx}. Title: {item['title']}\n"
            f"   Link: {item['link']}\n"
            f"   Snippet: {item['snippet']}\n\n"
        )
    prompt_text += (
        "Your task:\n"
        "1. Identify which links and snippets are most relevant to understanding the company's key details.\n"
        "2. Output all relevant links in a list format."
    )
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    params = {"key": gemini_api_key}
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": prompt_text}]}
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if (
            "candidates" in data and data["candidates"] and
            "content" in data["candidates"][0] and
            "parts" in data["candidates"][0]["content"] and
            data["candidates"][0]["content"]["parts"] and
            "text" in data["candidates"][0]["content"]["parts"][0]
        ):
            llm_output = data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return ""
        
        # Extract URLs using regex
        links = re.findall(r"https?://[^\s)]+", llm_output)
        if not links:
            return ""
        return ", ".join(links)
    except requests.exceptions.RequestException:
        return ""
    except Exception:
        return ""

def validate_search_results(results):
    """
    Validates the format of the search results.
    Returns True if the format is correct, False otherwise.
    """
    if not isinstance(results, list):
        return False
    for item in results:
        if not isinstance(item, dict):
            return False
        if not all(key in item for key in ("title", "link", "snippet")):
            return False
    return True

if __name__ == "__main__":
    # Read API keys from environment variables
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    CUSTOM_SEARCH_CX = os.getenv("CUSTOM_SEARCH_CX")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Exit if any API key is missing
    if not all([GOOGLE_API_KEY, CUSTOM_SEARCH_CX, GEMINI_API_KEY]):
        exit()
    
    # Get company name from user input
    company = input("Enter the company name: ").strip()
    query = f"company information about {company}"
    
    # Perform the Google search
    search_results = google_search(query, GOOGLE_API_KEY, CUSTOM_SEARCH_CX, num_results=5)
    if not search_results:
        exit()
    
    if not validate_search_results(search_results):
        exit()
    
    # Evaluate search results with Gemini, passing the company name for a dynamic prompt
    evaluation_response = evaluate_search_results_with_gemini(search_results, GEMINI_API_KEY, company)
    print(evaluation_response)
