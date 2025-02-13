import asyncio
import os
import sys
import json
import requests
from dotenv import load_dotenv
from search_module import google_search
from eval import evaluate_search_results_with_gemini
from crawl4ai import AsyncWebCrawler
from markdown_cleaner import clean_markdown  # Ensure this file exists and defines clean_markdown()

# Load environment variables from the .env file
load_dotenv()

async def crawl_company_links(relevant_links, max_depth=2):
    """
    Crawls a list of URLs concurrently using AsyncWebCrawler from crawl4ai.

    Parameters:
      relevant_links (list): List of starting URLs.
      max_depth (int): Maximum crawling depth (set to 2).

    Returns:
      dict: A mapping of each URL to its full crawled text (in Markdown format).
      
    Note (Aus): This function crawls each URL (and its sublinks, up to depth 2)
    and returns the full text from each website.
    """
    crawled_data = {}
    async with AsyncWebCrawler() as crawler:
        tasks = [crawler.arun(url=url, max_depth=max_depth) for url in relevant_links]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for url, result in zip(relevant_links, results):
            if isinstance(result, Exception):
                continue
            # Assume result.markdown contains the full text from the site.
            crawled_data[url] = result.markdown
    return crawled_data

def final_summary(aggregated_text, gemini_api_key):
    """
    Uses the Gemini API to generate a structured JSON summary of the aggregated text.

    Parameters:
      aggregated_text (str): The cleaned and aggregated text from the crawler.
      gemini_api_key (str): Your Google Gemini API key.
      
    Returns:
      dict: A structured JSON summary with keys:
            - company_history
            - business_model
            - funding_status
            - key_achievements

    Note (Aus): The prompt instructs Gemini to output exactly valid JSON.
    """
    prompt = (
        "Please analyse the following text and produce a structured JSON object with exactly the following keys:\n"
        "- company_history: A summary of the company's history.\n"
        "- business_model: A description of the company's business model.\n"
        "- funding_status: Details on the company's funding, if available.\n"
        "- key_achievements: A list of the company's key achievements.\n\n"
        "Output only valid JSON without any additional text. For example:\n"
        '{"company_history": "history here", "business_model": "model here", "funding_status": "funding details", "key_achievements": ["achievement 1", "achievement 2"]}\n\n'
        "Text:\n" + aggregated_text
    )
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    params = {"key": gemini_api_key}
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if ("candidates" in data and data["candidates"] and
            "content" in data["candidates"][0] and
            "parts" in data["candidates"][0]["content"] and
            data["candidates"][0]["content"]["parts"] and
            "text" in data["candidates"][0]["content"]["parts"][0]):
            llm_output = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            try:
                structured_output = json.loads(llm_output)
                return structured_output
            except json.JSONDecodeError:
                return llm_output
        return {}
    except Exception as e:
        print("Error in final_summary:", e)
        return {}

async def summarise_company():
    """
    Orchestrates the full process:
      1. Obtains a company name from the user (via command-line or prompt).
      2. Performs a Google search for company information.
      3. Uses Gemini (via evaluate_search_results_with_gemini) to extract relevant links.
      4. Uses AsyncWebCrawler to crawl these links (and their sublinks) with max_depth=2.
      5. Aggregates all crawled text and cleans it with the markdown cleaner.
      6. Sends the cleaned, aggregated text to Gemini to produce a structured summary.
      7. Outputs the final structured summary.
      
    Note (Aus): This unified process gathers comprehensive online data about a company and produces a structured evaluation.
    """
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    CUSTOM_SEARCH_CX = os.getenv("CUSTOM_SEARCH_CX")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not all([GOOGLE_API_KEY, CUSTOM_SEARCH_CX, GEMINI_API_KEY]):
        print("Missing one or more API keys.")
        return

    if len(sys.argv) > 1:
        company = " ".join(sys.argv[1:])
    else:
        company = input("Enter the company name: ").strip()

    query = f"company information about {company}"

    search_results = google_search(query, GOOGLE_API_KEY, CUSTOM_SEARCH_CX, num_results=5)
    if not search_results:
        print("No search results returned.")
        return

    eval_response = evaluate_search_results_with_gemini(search_results, GEMINI_API_KEY, company)
    relevant_links = [link.strip() for link in eval_response.split(",") if link.strip().startswith("http")]
    if not relevant_links:
        print("No relevant links extracted.")
        return

    print("Relevant links found:", relevant_links)

    crawled_data = await crawl_company_links(relevant_links, max_depth=2)
    aggregated_text = "\n".join(crawled_data.values())
    if not aggregated_text:
        print("No crawled text found.")
        return

    # Clean the aggregated text using the markdown cleaner for efficient processing.
    cleaned_text = clean_markdown(aggregated_text)
    
    structured_summary = final_summary(cleaned_text, GEMINI_API_KEY)
    if structured_summary:
        print("Final Structured Summary:")
        print(json.dumps(structured_summary, indent=2))
    else:
        print("No structured summary generated.")

if __name__ == "__main__":
    asyncio.run(summarise_company())
