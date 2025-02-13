import re
from rank_bm25 import BM25Okapi

def clean_markdown(raw_markdown):
    """
    Generates super clean, structured Markdown from the raw input.
    
    Features:
      - Removes excessive whitespace and noise.
      - Uses BM25-based filtering to retain core, high-relevance sentences.
      - Converts all URLs into a numbered reference list with citations.
    
    Parameters:
      raw_markdown (str): The raw markdown text to be cleaned.
    
    Returns:
      str: The final cleaned Markdown output.
    """
    # Step 1: Basic cleaning – remove extra whitespace and normalise newlines.
    cleaned = re.sub(r'\n\s*\n', '\n\n', raw_markdown.strip())
    
    # Step 2: Extract URLs for citations.
    urls = re.findall(r"https?://[^\s)]+", cleaned)
    unique_urls = list(dict.fromkeys(urls))  # Remove duplicates while preserving order.
    
    # Replace URLs in the text with citation markers [1], [2], etc.
    citations = {}
    for idx, url in enumerate(unique_urls, start=1):
        citations[url] = idx
        cleaned = re.sub(re.escape(url), f"[{idx}]", cleaned)
    
    # Step 3: Split text into sentences and apply BM25 filtering.
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned) if s.strip()]
    if sentences:
        tokenized_sentences = [s.split() for s in sentences]
        bm25 = BM25Okapi(tokenized_sentences)
        query_tokens = cleaned.split()
        scores = bm25.get_scores(query_tokens)
        max_score = max(scores) if scores.size else 0
        threshold = 0.5 * max_score  # Adjust threshold as needed.
        filtered_sentences = [s for s, score in zip(sentences, scores) if score >= threshold]
        cleaned = " ".join(filtered_sentences)
    
    # Step 4: Append a references section.
    if citations:
        cleaned += "\n\n### References\n"
        for url, idx in citations.items():
            cleaned += f"{idx}. {url}\n"
    
    return cleaned
