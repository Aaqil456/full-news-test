# Import required libraries
import os
import requests
import json
from datetime import datetime
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel("gemini-1.5-flash")

def translate_text_gemini(text):
    if not text:
        return ""
    response = model.generate_content(f"Translate this text '{text}' into Malay. Only return the translated text, structured like an article.")
    return response.text.strip()

# Function to fetch news from Apify Actor API
def fetch_news_from_apify(api_token):
    url = f"https://api.apify.com/v2/acts/buseta~crypto-news/run-sync-get-dataset-items?token={api_token}"
    try:
        print("Triggering the Apify Actor...")
        response = requests.post(url, timeout=600)
        if response.status_code == 201:
            news_data = response.json()
            news_list = []
            for news in news_data:
                news_list.append({
                    "title": news.get("title", "Untitled"),
                    "url": news.get("link", "#"),
                    "description": news.get("summary", "No summary available."),
                    "image": news.get("image", ""),
                    "content": news.get("content", "No content available."),
                    "timestamp": news.get("time", datetime.now().isoformat())
                })
            return news_list
        else:
            print(f"Failed to fetch news from Apify: {response.status_code}, {response.text}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Exception occurred while fetching data from Apify: {e}")
        return []

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
    if not APIFY_API_TOKEN:
        print("API token is missing! Please set APIFY_API_TOKEN as an environment variable.")
        return

    print("Fetching news from Apify Actor API...")
    fetched_news = fetch_news_from_apify(APIFY_API_TOKEN)

    print("Translating news content using Gemini API...")
    for news in fetched_news:
        news["title"] = translate_text_gemini(news["title"])
        news["description"] = translate_text_gemini(news["description"])
        news["content"] = translate_text_gemini(news["content"])

    existing_data = load_existing_data()
    combined_news = remove_duplicates(fetched_news + existing_data.get("all_news", []))

    save_to_json(combined_news)

    print("\nNewly Added News:")
    new_news = [news for news in combined_news if news not in existing_data.get("all_news", [])]
    for news in new_news:
        print(f"Title: {news['title']}\nURL: {news['url']}\nContent Snippet: {news.get('content', '')[:100]}...\n")

if __name__ == "__main__":
    main()
