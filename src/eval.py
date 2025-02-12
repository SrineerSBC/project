# evaluation.py
import requests
from search_module import google_search  # <-- Import from search.py

def evaluate_search_results_with_gemini(results, gemini_api_key):
    """
    Takes a list of search results and calls Google Gemini Flash to evaluate them.
    """
    # Build your prompt from the search results
    prompt_text = "We have these search results:\n"
    for idx, item in enumerate(results, start=1):
        prompt_text += f"{idx}. Title: {item['title']}\n   Link: {item['link']}\n   Snippet: {item['snippet']}\n\n"
    prompt_text += "Please pick the most relevant link and explain why."

    # Set up Gemini API call
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
        response = requests.post(url, json=payload, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        # Parse Gemini's response structure
        # Example (adjust based on actual structure of the response)
        result_text = data.get("contents", [{}])[0].get("parts", [{}])[0].get("text", "")
        return result_text

    except requests.exceptions.RequestException as e:
        print("Error calling Gemini API:", e)
        return ""


if __name__ == "__main__":
    # Example usage:
    GOOGLE_API_KEY = "YOUR_GOOGLE_SEARCH_API_KEY"
    CUSTOM_SEARCH_CX = "YOUR_CUSTOM_SEARCH_ENGINE_ID"
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

    # 1) Get search results by calling google_search from search.py
    query = "startupbootcamp"
    search_results = google_search(query, GOOGLE_API_KEY, CUSTOM_SEARCH_CX, num_results=5)

    # 2) Evaluate results with Gemini
    evaluation_response = evaluate_search_results_with_gemini(search_results, GEMINI_API_KEY)
    print("Gemini Evaluation:\n", evaluation_response)
