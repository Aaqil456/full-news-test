import os
import requests
import json
from datetime import datetime

# Define Gemini API URL
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Function to translate text using Gemini API (via HTTP request)
def translate_text_gemini(text):
    if not text:
        return ""

    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Translate this text '{text}' into Malay. Only return the translated text, structured like an article."}]
        }]
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            response_data = response.json()
            translated_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Translation failed")
            return translated_text.strip() if translated_text != "Translation failed" else "Translation failed"
        else:
            print(f"Gemini API error: {response.status_code}, {response.text}")
            return "Translation failed"
    except Exception as e:
        print(f"[ERROR] Gemini API request failed: {e}")
        return "Translation failed"

# Function to fetch news from Apify Actor API
def fetch_news_from_apify(api_token):
    url = f"https://api.apify.com/v2/acts/buseta~crypto-news/run-sync-get-dataset-items?token={api_token}"
    try:
        print("Triggering the Apify Actor...")
        response = requests.post(url, timeout=600)
        if response.status_code == 201:
            news_data = response.json()
            return news_data
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
    translated_news = []
    success_count = 0
    
    for news in fetched_news:
        original_title = news.get("title", "Untitled")
        original_description = news.get("description", "No description available.")
        original_content = news.get("content", "No content available.")

        translated_title = translate_text_gemini(original_title)
        translated_description = translate_text_gemini(original_description)
        translated_content = translate_text_gemini(original_content)

        if translated_title != "Translation failed" and translated_description != "Translation failed" and translated_content != "Translation failed":
            news["title"] = translated_title
            news["description"] = translated_description
            news["content"] = translated_content
            translated_news.append(news)
            success_count += 1
            print(f"- Successfully Translated: {translated_title}")
        else:
            print(f"Skipping news (translation failed for at least one field): {original_title}")

    existing_data = load_existing_data()
    combined_news = remove_duplicates(translated_news + existing_data.get("all_news", []))
    save_to_json(combined_news)
    
    print(f"\nSuccessfully translated and saved {success_count} news articles.")

if __name__ == "__main__":
    main()
