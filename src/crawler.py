import asyncio
import os
import sys
from dotenv import load_dotenv
from search_module import google_search
from eval import evaluate_search_results_with_gemini
from crawl4ai import AsyncWebCrawler
from markdown_cleaner import clean_markdown  # Import our markdown cleaning function

# Load environment variables from the .env file
load_dotenv()

async def crawl_company_links(relevant_links, max_depth=2):
    """
    Crawls a list of URLs concurrently using AsyncWebCrawler from crawl4ai.

    Parameters:
      relevant_links (list): List of starting URLs.
      max_depth (int): The maximum crawling depth (set to 2).

    Returns:
      dict: A mapping of each URL to its full markdown content.
      
    Note (Aus): This function crawls each URL (and its sublinks up to depth 2)
    and returns all the text (in markdown format) from each website.
    """
    crawled_data = {}
    async with AsyncWebCrawler() as crawler:
        tasks = []
        for url in relevant_links:
            # Assume the arun method accepts a max_depth parameter.
            tasks.append(crawler.arun(url=url, max_depth=max_depth))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for url, result in zip(relevant_links, results):
            if isinstance(result, Exception):
                continue
            # Assume result.markdown contains the raw crawled Markdown text.
            crawled_data[url] = result.markdown
    return crawled_data

async def main():
    """
    Orchestrates the asynchronous crawling and cleaning process:
      1. Obtains a company name (via command-line or prompt).
      2. Performs a Google search for company information.
      3. Uses Gemini (via evaluate_search_results_with_gemini) to extract relevant links.
      4. Uses AsyncWebCrawler to crawl these links (and their sublinks) with max_depth=2.
      5. Cleans the raw Markdown output using the Markdown cleaner.
      6. Outputs the final, super clean Markdown for each URL.
      
    Note (Aus): This flexible approach works for any company.
    """
    # Retrieve API keys from environment variables
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    CUSTOM_SEARCH_CX = os.getenv("CUSTOM_SEARCH_CX")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not all([GOOGLE_API_KEY, CUSTOM_SEARCH_CX, GEMINI_API_KEY]):
        print("Missing one or more API keys.")
        return

    # Get the company name from command-line arguments or user input
    if len(sys.argv) > 1:
        company = " ".join(sys.argv[1:])
    else:
        company = input("Enter the company name: ").strip()

    query = f"company information about {company}"

    # Perform the Google search
    search_results = google_search(query, GOOGLE_API_KEY, CUSTOM_SEARCH_CX, num_results=5)
    if not search_results:
        print("No search results returned.")
        return

    # Evaluate search results with Gemini to obtain relevant links (as a comma-separated string)
    eval_response = evaluate_search_results_with_gemini(search_results, GEMINI_API_KEY, company)
    relevant_links = [link.strip() for link in eval_response.split(",") if link.strip().startswith("http")]
    if not relevant_links:
        print("No relevant links extracted.")
        return

    print("Relevant links found:", relevant_links)

    # Crawl the relevant links and their sublinks with a maximum depth of 2
    crawled_data = await crawl_company_links(relevant_links, max_depth=2)
    
    # Clean the crawled markdown using the clean_markdown function and print the output.
    for url, content in crawled_data.items():
        clean_output = clean_markdown(content)
        print(f"URL: {url}")
        print(clean_output)
        print("\n---\n")

if __name__ == "__main__":
    asyncio.run(main())
