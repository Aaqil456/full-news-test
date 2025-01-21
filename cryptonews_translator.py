# Import required libraries
import os
import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup

# Function to fetch news from CryptoPanic API
def fetch_news(api_key, filter_type=None):
    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={api_key}&metadata=true&approved=true"
    if filter_type:
        url += f"&filter={filter_type}"
    response = requests.get(url)
    if response.status_code == 200:
        news_data = response.json()
        news_list = []
        for news in news_data.get("results", []):
            source_url = news.get("source", {}).get("url", "")  # Get the original source URL
            full_content = fetch_news_content(source_url) if source_url else "Source content unavailable"
            news_list.append({
                "title": news["title"],
                "url": source_url,
                "description": news.get("description", ""),
                "image": news.get("metadata", {}).get("image", ""),
                "full_content": full_content,  # Add the fetched full content
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
            return content
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

# Function to save news data to JSON
def save_to_json(data, filename="translated_news.json"):
    output = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "all_news": data}
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print(f"Translated news saved to {filename}")

# Function to remove duplicates
def remove_duplicates(news_list):
    seen_urls = set()
    unique_news = []
    for news in news_list:
        if news["url"] not in seen_urls:
            unique_news.append(news)
            seen_urls.add(news["url"])
    return unique_news

# Function to load existing data
def load_existing_data(filename="translated_news.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"all_news": []}

# Main function
def main():
    CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")

    if not CRYPTOPANIC_API_KEY:
        print("API key is missing! Please set it as an environment variable.")
        return

    # Fetch all news and hot news
    print("Fetching all news from CryptoPanic...")
    all_news = fetch_news(CRYPTOPANIC_API_KEY)

    print("Fetching hot news from CryptoPanic...")
    hot_news = fetch_news(CRYPTOPANIC_API_KEY, filter_type="hot")

    # Combine all news and hot news
    combined_news = remove_duplicates(hot_news + all_news)

    # Load existing data and merge
    existing_data = load_existing_data()
    final_news_list = remove_duplicates(combined_news + existing_data.get("all_news", []))

    # Save the combined news data
    save_to_json(final_news_list)

    # Print newly added news
    print("\nNewly Added News:")
    new_news = [news for news in final_news_list if news not in existing_data.get("all_news", [])]
    for news in new_news:
        print(f"Title: {news['title']}\nURL: {news['url']}\nContent Snippet: {news['full_content'][:100]}...\n")

if __name__ == "__main__":
    main()
