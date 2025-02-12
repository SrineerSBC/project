import os
import re
import requests
from dotenv import load_dotenv
from search_module import google_search  # <-- your search function here

# Load environment variables from .env
load_dotenv()

def evaluate_search_results_with_gemini(results, gemini_api_key):
    """
    Takes a list of search results and calls Google Gemini to evaluate them.
    Then extracts only the relevant links from the JSON response and returns them
    in comma-separated format 
    """
    # Build the prompt from the search results
    prompt_text = (
        "We have these search results about the company:\n\n"
    )
    for idx, item in enumerate(results, start=1):
        prompt_text += (
            f"{idx}. Title: {item['title']}\n"
            f"   Link: {item['link']}\n"
            f"   Snippet: {item['snippet']}\n\n"
        )

    # Instructions for the LLM
    prompt_text += (
        "Your task:\n"
        "1. Identify which links and snippets are most relevant to understanding this company's key details.\n"
        "2. Output all relevant links in a list format."
    )

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
        # Raise HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()

        # Parse the JSON to extract the LLM's text
        data = response.json()
        # Gemini typically puts the output text here:
        # data["candidates"][0]["content"]["parts"][0]["text"]
        # but that can vary by version.

        # Safely navigate the JSON structure:
        if (
            "candidates" in data
            and data["candidates"]
            and "content" in data["candidates"][0]
            and "parts" in data["candidates"][0]["content"]
            and data["candidates"][0]["content"]["parts"]
            and "text" in data["candidates"][0]["content"]["parts"][0]
        ):
            # Extract the LLM's output text
            llm_output = data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            # Fallback or error
            return ""

        # Regex to find all URLs in the text
        # This pattern matches http or https, then any chars that aren't spaces or parentheses
        links = re.findall(r"https?://[^\s)]+", llm_output)

        # If we just want the domain part (e.g., link1.com), you could parse further,
        # but typically returning the full URL is safer/more accurate.
        if not links:
            return ""

        # Return comma-separated links
        return ", ".join(links)

    except requests.exceptions.RequestException:
        # Handle request exceptions (e.g., network errors)
        return ""
    except Exception:
        # Handle other exceptions (e.g., JSON parsing errors)
        return ""

def validate_search_results(results):
    """
    Validates the format of the search results.
    Returns True if the format is correct, False otherwise.
    """
    if not isinstance(results, list):
        # Check if the results are a list
        return False
    for item in results:
        if not isinstance(item, dict):
            # Check if each item in the list is a dictionary
            return False
        if not all(key in item for key in ("title", "link", "snippet")):
            # Check if each dictionary contains the required keys
            return False
    return True

if __name__ == "__main__":
    # Read credentials from environment variables
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    CUSTOM_SEARCH_CX = os.getenv("CUSTOM_SEARCH_CX")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Exit if any API key is missing
    if not all([GOOGLE_API_KEY, CUSTOM_SEARCH_CX, GEMINI_API_KEY]):
        exit()

    query = "Startupbootcamp"
    # Perform the Google search
    search_results = google_search(query, GOOGLE_API_KEY, CUSTOM_SEARCH_CX, num_results=5)

    # Exit if no search results are returned
    if not search_results:
        exit()

    # Validate the search results structure
    if not validate_search_results(search_results):
        exit()

    # Evaluate with Gemini: only print the relevant links in comma-separated format
    evaluation_response = evaluate_search_results_with_gemini(search_results, GEMINI_API_KEY)
    print(evaluation_response)