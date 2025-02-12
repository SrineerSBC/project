import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
from search_module import google_search
from eval import evaluate_search_results_with_gemini
import nltk
from nltk.stem import PorterStemmer, WordNetLemmatizer


# Load environment variables from the .env file
load_dotenv()

# Maximum depth for recursive crawling
MAX_DEPTH = 2
stemmer = PorterStemmer()
lemmatizer = WordNetLemmatizer()

def preprocess_text(text):
    """Stems and lemmatizes the given text."""
    words = nltk.word_tokenize(text)
    processed_words = [lemmatizer.lemmatize(stemmer.stem(word)) for word in words]
    return ' '.join(processed_words)

def get_page_content_and_links(url):
    """Retrieves the HTML content of the given URL and extracts text and internal sublinks."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract text content from paragraph tags
        paragraphs = soup.find_all('p')
        page_text = "\n".join(p.get_text(strip=True) for p in paragraphs)
        
        # Extract sublinks from the same domain
        base_domain = urlparse(url).netloc
        sublinks = {urljoin(url, link.get('href')) for link in soup.find_all('a', href=True)
                    if urlparse(urljoin(url, link.get('href'))).netloc == base_domain}
        
        return page_text, sublinks
    except requests.RequestException:
        return "", set()

def crawl_links(links, depth=1, visited=None):
    """Recursively crawls the provided links up to a maximum depth."""
    if visited is None:
        visited = set()
    
    if depth > MAX_DEPTH:
        return {}
    
    crawled_data = {}
    for url in links:
        if url in visited:
            continue
        
        visited.add(url)
        page_text, sublinks = get_page_content_and_links(url)
        if page_text:
            crawled_data[url] = preprocess_text(page_text)  # Apply stemming and lemmatization
        
        # Recursively crawl sublinks found on the page
        crawled_data.update(crawl_links(sublinks, depth + 1, visited))
    
    return crawled_data

def main():
    """Main function to orchestrate the crawling process."""
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    CUSTOM_SEARCH_CX = os.getenv("CUSTOM_SEARCH_CX")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    if not all([GOOGLE_API_KEY, CUSTOM_SEARCH_CX, GEMINI_API_KEY]):
        return  # Exit if any API key is missing

    query = "company information about startupbootcamp"
    
    # Perform the Google search
    search_results = google_search(query, GOOGLE_API_KEY, CUSTOM_SEARCH_CX, num_results=5)
    if not search_results:
        return
    
    # Evaluate search results with Gemini to obtain relevant links
    eval_response = evaluate_search_results_with_gemini(search_results, GEMINI_API_KEY)
    
    # Convert the comma-separated string into a list of URLs
    relevant_links = [link.strip() for link in eval_response.split(",") if link.strip().startswith("http")]
    if not relevant_links:
        return
    
    # Crawl the relevant links and their sublinks
    crawled_data = crawl_links(relevant_links, depth=1)
    
    # Output the crawled data
    for url, text in crawled_data.items():
        print(f"URL: {url}")
        print(text[:500])  # Print the first 500 characters of the processed text
        print("\n---\n")

if __name__ == "__main__":
    main()