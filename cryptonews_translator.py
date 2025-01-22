# Import required libraries
import os
import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup

# Function to fetch news from CryptoPanic with metadata and optional filters
def fetch_news(api_key, filter_type=None):
    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={api_key}&metadata=true&approved=true"
    if filter_type:
        url += f"&filter={filter_type}"
    response = requests.get(url)
    if response.status_code == 200:
        news_data = response.json()
        news_list = []
        for news in news_data.get("results", []):
            # Get the original source URL
            source_url = news.get("source", {}).get("url", "")
            # Fetch full content from the source URL
            full_content = fetch_news_content(source_url) if source_url else "Source content unavailable"
            news_list.append({
                "title": news["title"],
                "url": source_url,
                "description": news.get("description", ""),
                "image": news.get("metadata", {}).get("image", ""),
                "panic_score": news.get("panic_score"),
                "full_content": full_content,  # Add fetched full content
                "timestamp": datetime.now().isoformat()
            })
        return news_list
    else:
        print(f"Failed to fetch news: {response.status_code}")
        return []

# Function to fetch and parse the full content of a news article
def fetch_news_content(url):
    if not url:
        return "No source URL provided."
    try:
        # Mimic a browser to avoid being blocked by the website
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Extract meaningful content - Adjust based on the website's structure
            content = " ".join(p.get_text() for p in soup.find_all('p'))

            # Split content into paragraphs for better readability
            structured_content = split_into_paragraphs(content)
            return structured_content
        elif response.status_code == 403:
            return "Access to the source URL is forbidden."
        elif response.status_code == 404:
            return "Source content not found."
        else:
            print(f"[ERROR] Failed to fetch content from {url} - Status Code: {response.status_code}")
            return f"Failed to fetch content: {response.status_code}"
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Exception occurred while fetching {url}: {e}")
        return "Error fetching content."

# Function to split content into paragraphs
def split_into_paragraphs(content, max_length=300):
    """Splits content into paragraphs with a max length for each paragraph."""
    words = content.split()
    paragraphs = []
    current_paragraph = []

    for word in words:
        current_paragraph.append(word)
        # Check if the current paragraph exceeds max length
        if len(" ".join(current_paragraph)) > max_length:
            paragraphs.append(" ".join(current_paragraph))
            current_paragraph = []

    # Append the remaining words as the last paragraph
    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))

    # Combine paragraphs into a structured format
    return "\n\n".join(paragraphs)

# Function to translate text using Easy Peasy API
def translate_text_easypeasy(api_key, text):
    if not text:
        return ""
    url = "https://bots.easy-peasy.ai/bot/e56f7685-30ed-4361-b6c1-8e17495b7faa/api"
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key
    }
    payload = {
        "message": f"translate this text '{text}' into Malay language. Your job is just to translate this text into Malay also if there are any repeating sentence that doesn't make sense with the overall text, remove that repeating sentence",
        "history": [],
        "stream": False
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        response_data = response.json()
        return response_data.get("bot", {}).get("text", "Translation failed")
    else:
        print(f"Translation API error: {response.status_code}, {response.text}")
        return "Translation failed"

# Function to load existing data
def load_existing_data(filename="translated_news.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"all_news": []}

# Function to remove duplicates
def remove_duplicates(news_list):
    seen_urls = set()
    unique_news = []
    for news in news_list:
        if news["url"] not in seen_urls:
            unique_news.append(news)
            seen_urls.add(news["url"])
    return unique_news

# Function to save news to JSON
def save_to_json(data, filename="translated_news.json"):
    output = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "all_news": data}
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print(f"Translated news saved to {filename}")

# Main function
def main():
    CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")
    EASY_PEASY_API_KEY = os.getenv("EASY_PEASY_API_KEY")

    if not CRYPTOPANIC_API_KEY or not EASY_PEASY_API_KEY:
        print("API keys are missing! Please set them as environment variables.")
        return

    # Fetch all news and hot news
    print("Fetching all news from CryptoPanic...")
    all_news = fetch_news(CRYPTOPANIC_API_KEY)

    print("Fetching hot news from CryptoPanic...")
    hot_news = fetch_news(CRYPTOPANIC_API_KEY, filter_type="hot")

    # Translate all news
    print("Translating all news titles, descriptions, and full content...")
    for news in all_news:
        news["title"] = translate_text_easypeasy(EASY_PEASY_API_KEY, news["title"])
        news["description"] = translate_text_easypeasy(EASY_PEASY_API_KEY, news["description"])
        news["full_content"] = translate_text_easypeasy(EASY_PEASY_API_KEY, news["full_content"])
        news["is_hot"] = False  # Default value

    # Translate hot news and mark them
    print("Translating hot news titles, descriptions, and full content...")
    for news in hot_news:
        news["title"] = translate_text_easypeasy(EASY_PEASY_API_KEY, news["title"])
        news["description"] = translate_text_easypeasy(EASY_PEASY_API_KEY, news["description"])
        news["full_content"] = translate_text_easypeasy(EASY_PEASY_API_KEY, news["full_content"])
        news["is_hot"] = True

    # Combine all news and hot news, ensuring hot news is part of all news
    combined_news = hot_news + all_news  # Hot news first
    combined_news = remove_duplicates(combined_news)

    # Load existing data and merge
    existing_data = load_existing_data()
    final_news_list = remove_duplicates(combined_news + existing_data.get("all_news", []))

    # Save combined data to JSON
    save_to_json(final_news_list)

    # Print newly added news
    print("\nNewly Added News:")
    new_news = [news for news in final_news_list if news not in existing_data.get("all_news", [])]
    for news in new_news:
        print(f"Title: {news['title']}\nURL: {news['url']}\nContent Snippet: {news.get('full_content', '')[:100]}...\n")

# Run the main script
if __name__ == "__main__":
    main()
