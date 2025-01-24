# Import required libraries
import os
import requests
import json
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Function to fetch news from Apify Actor API
def fetch_news_from_apify(api_token):
    url = f"https://api.apify.com/v2/acts/buseta~crypto-news/run-sync-get-dataset-items?token={api_token}"
    try:
        print("Triggering the Apify Actor...")
        response = requests.post(url, timeout=600)  # Trigger the actor and wait for the response
        if response.status_code == 201:  # 201 indicates successful creation with data returned
            news_data = response.json()  # Parse the JSON response
            news_list = []
            for news in news_data:  # Iterate through the list of news articles
                news_list.append({
                    "title": news.get("title", "Untitled"),
                    "url": news.get("link", "#"),
                    "description": news.get("summary", "No summary available."),  # Using 'summary' for description
                    "image": news.get("image", ""),
                    "content": news.get("content", "No content available."),
                    "timestamp": news.get("time", datetime.now().isoformat())  # Use 'time' field if available
                })
            return news_list
        else:
            print(f"Failed to fetch news from Apify: {response.status_code}, {response.text}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Exception occurred while fetching data from Apify: {e}")
        return []


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
        "message": f"translate this text '{text}' into Malay language. Only return the translated text and make it structural like an article.",
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
    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
    EASY_PEASY_TRANSLATE_KEY = os.getenv("EASY_PEASY_TRANSLATE_KEY")

    if not APIFY_API_TOKEN:
        print("API token is missing! Please set APIFY_API_TOKEN as an environment variable.")
        return

    if not EASY_PEASY_TRANSLATE_KEY:
        print("Translation API key is missing! Please set EASY_PEASY_TRANSLATE_KEY as an environment variable.")
        return

    print("Fetching news from Apify Actor API...")
    fetched_news = fetch_news_from_apify(APIFY_API_TOKEN)

    print("Translating news content...")
    for news in fetched_news:
        news["title"] = translate_text_easypeasy(EASY_PEASY_TRANSLATE_KEY, news["title"])
        news["description"] = translate_text_easypeasy(EASY_PEASY_TRANSLATE_KEY, news["description"])
        news["content"] = translate_text_easypeasy(EASY_PEASY_TRANSLATE_KEY, news["content"])

    existing_data = load_existing_data()
    combined_news = remove_duplicates(fetched_news + existing_data.get("all_news", []))

    save_to_json(combined_news)

    print("\nNewly Added News:")
    new_news = [news for news in combined_news if news not in existing_data.get("all_news", [])]
    for news in new_news:
        print(f"Title: {news['title']}\nURL: {news['url']}\nContent Snippet: {news.get('content', '')[:100]}...\n")

if __name__ == "__main__":
    main()
