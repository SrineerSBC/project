import asyncio
import os
import sys
import json
import requests
from dotenv import load_dotenv
from search_module import google_search
from eval import evaluate_search_results_with_gemini
from crawl4ai import AsyncWebCrawler
from markdown_cleaner import clean_markdown

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
      
    Note: This function crawls each URL (and its sublinks, up to depth 2)
    and returns the full text from each website.
    """
    crawled_data = {}
    # Use AsyncWebCrawler to crawl the web asynchronously
    async with AsyncWebCrawler() as crawler:
        # Create a list of tasks to crawl each URL
        tasks = [crawler.arun(url=url, max_depth=max_depth) for url in relevant_links]
        # Gather the results of all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Process the results
        for url, result in zip(relevant_links, results):
            # If there was an exception during crawling, skip this URL
            if isinstance(result, Exception):
                continue
            # Assume result.markdown contains the full text from the site.
            crawled_data[url] = result.markdown
    # Return the crawled data
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

    Note: The prompt instructs Gemini to output exactly valid JSON.
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
        # Make the API request to Google Gemini
        response = requests.post(url, json=payload, headers=headers, params=params)
        # Raise HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()
        # Parse the JSON response
        data = response.json()
        # Safely navigate the JSON structure to extract the LLM's output
        if ("candidates" in data and data["candidates"] and
            "content" in data["candidates"][0] and
            "parts" in data["candidates"][0]["content"] and
            data["candidates"][0]["content"]["parts"] and
            "text" in data["candidates"][0]["content"]["parts"][0]):
            # Extract the LLM's output text
            llm_output = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            try:
                # Attempt to parse the LLM's output as JSON
                structured_output = json.loads(llm_output)
                # Return the structured output
                return structured_output
            except json.JSONDecodeError:
                # If the LLM's output is not valid JSON, return the raw output
                return llm_output
        # If the LLM's output is not found, return an empty dictionary
        return {}
    except Exception as e:
        # Handle any exceptions that occur during the API request
        print("Error in final_summary:", e)
        # Return an empty dictionary if an error occurred
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
      
    Note: This unified process gathers comprehensive online data about a company and produces a structured evaluation.
    """
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    CUSTOM_SEARCH_CX = os.getenv("CUSTOM_SEARCH_CX")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # Check if all required API keys are available
    if not all([GOOGLE_API_KEY, CUSTOM_SEARCH_CX, GEMINI_API_KEY]):
        print("Missing one or more API keys.")
        return

    # Get the company name from the command line or prompt the user
    if len(sys.argv) > 1:
        company = " ".join(sys.argv[1:])
    else:
        company = input("Enter the company name: ").strip()

    # Construct the search query
    query = f"company information about {company}"

    # Perform the Google search
    search_results = google_search(query, GOOGLE_API_KEY, CUSTOM_SEARCH_CX, num_results=5)
    # If no search results are returned, exit
    if not search_results:
        print("No search results returned.")
        return

    # Evaluate the search results with Gemini to extract relevant links
    eval_response = evaluate_search_results_with_gemini(search_results, GEMINI_API_KEY, company)
    # Extract the relevant links from the evaluation response
    relevant_links = [link.strip() for link in eval_response.split(",") if link.strip().startswith("http")]
    # If no relevant links are extracted, exit
    if not relevant_links:
        print("No relevant links extracted.")
        return

    print("Relevant links found:", relevant_links)

    # Crawl the relevant links to gather text data
    crawled_data = await crawl_company_links(relevant_links, max_depth=2)
    # Aggregate the crawled text into a single string
    aggregated_text = "\n".join(crawled_data.values())
    # If no crawled text is found, exit
    if not aggregated_text:
        print("No crawled text found.")
        return

    # Clean the aggregated text using the markdown cleaner for efficient processing.
    cleaned_text = clean_markdown(aggregated_text)
    
    # Generate a structured summary of the cleaned text using Gemini
    structured_summary = final_summary(cleaned_text, GEMINI_API_KEY)
    # If a structured summary is generated, print it to the console
    if structured_summary:
        print("Final Structured Summary:")
        print(json.dumps(structured_summary, indent=2))
    else:
        # If no structured summary is generated, print an error message
        print("No structured summary generated.")

if __name__ == "__main__":
    # Run the main function asynchronously
    asyncio.run(summarise_company())