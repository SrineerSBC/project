import os
import re
import requests
from dotenv import load_dotenv
from search_module import google_search  # Import the search function from our module

# Load environment variables from the .env file
load_dotenv()

def evaluate_search_results_with_gemini(results, gemini_api_key):
    """
    Takes a list of search results and calls Google Gemini to evaluate them.
    Returns only the relevant links as a comma‐separated string.
    
    Internal notes:
    - We build a prompt containing the search results details.
    - The Gemini model is instructed to identify the most relevant links.
    - We then extract any URLs from the LLM output.
    """
    # Construct the prompt text from the search results
    prompt_text = "We have these search results about the company:\n\n"
    for idx, item in enumerate(results, start=1):
        prompt_text += (
            f"{idx}. Title: {item['title']}\n"
            f"   Link: {item['link']}\n"
            f"   Snippet: {item['snippet']}\n\n"
        )
    
    # Provide clear instructions to the LLM
    prompt_text += (
        "Your task:\n"
        "1. Identify which links and snippets are most relevant to understanding this company's key details.\n"
        "2. Output all relevant links in a list format.\n"
        "For example: [\"https://example.com\", \"https://another-example.com\"]"
    )
    
    # Set up the Gemini API call details
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    params = {"key": gemini_api_key}
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt_text
                    }
                ]
            }
        ]
    }
    
    try:
        # Make the API request to Google Gemini
        response = requests.post(url, json=payload, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the JSON response to extract the LLM's output text
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
        
        # Use a regular expression to extract all URLs from the LLM output
        links = re.findall(r"https?://[^\s)]+", llm_output)
        if not links:
            return ""
        
        # Return the relevant links as a comma-separated string
        return ", ".join(links)
    
    except requests.exceptions.RequestException:
        # On network or API errors, return an empty string
        return ""
    except Exception:
        # Handle any other unexpected exceptions by returning an empty string
        return ""

def validate_search_results(results):
    """
    Validates the format of the search results.
    Returns True if the format is correct, False otherwise.
    
    Note:
    - Each search result should be a dictionary containing 'title', 'link', and 'snippet'.
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
    # Read credentials from environment variables
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    CUSTOM_SEARCH_CX = os.getenv("CUSTOM_SEARCH_CX")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Exit silently if any required API key is missing
    if not all([GOOGLE_API_KEY, CUSTOM_SEARCH_CX, GEMINI_API_KEY]):
        exit()
    
    query = "company information about startupbootcamp"
    # Perform the Google search using our search function
    search_results = google_search(query, GOOGLE_API_KEY, CUSTOM_SEARCH_CX, num_results=5)
    
    # Exit if no search results are returned or the format is invalid
    if not search_results or not validate_search_results(search_results):
        exit()
    
    # Evaluate the search results with Gemini and output only the relevant links
    evaluation_response = evaluate_search_results_with_gemini(search_results, GEMINI_API_KEY)
    print(evaluation_response)
