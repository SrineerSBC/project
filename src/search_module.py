import os
import requests
from dotenv import load_dotenv

# Load variables from .env into the environment
load_dotenv()

def google_search(query, api_key, cx, num_results=5):
    """
    Perform a Google Search using the Custom Search JSON API.
    
    :param query: str, the search query term
    :param api_key: str, your Google API key
    :param cx: str, your Custom Search Engine ID
    :param num_results: int, how many results to fetch (default 5)
    :return: list of dict, each containing title, link, snippet
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": api_key,
        "cx": cx,
        "num": num_results
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # raises an HTTPError if status != 200
        data = response.json()

        items = data.get("items", [])
        results = []
        for item in items:
            search_result = {
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
            }
            results.append(search_result)
        return results

    except requests.exceptions.RequestException as e:
        print("Error calling Google Search API:", e)
        return []


if __name__ == "__main__":
    # Retrieve API keys from the environment (loaded from .env)
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    CUSTOM_SEARCH_CX = os.getenv("CUSTOM_SEARCH_CX")

    # Example query
    query = "startupbootcamp"

    # Fetch results
    search_results = google_search(query, GOOGLE_API_KEY, CUSTOM_SEARCH_CX, num_results=5)

    # Print them out
    for idx, result in enumerate(search_results, start=1):
        print(f"{idx}. {result['title']}")
        print(f"   Link: {result['link']}")
        print(f"   Snippet: {result['snippet']}\n")
