import os
import requests
import json
import time
from datetime import datetime

# Define Gemini API URL
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Function to translate text using Gemini API with batch processing and exponential backoff
def translate_text_gemini(texts, max_retries=5):
    if not texts:
        return []
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": f"Translate this text '{text}' into Malay. Only return the translated text, structured like an article."} for text in texts]
        }]
    }

    wait_time = 10  # Initial wait time for exponential backoff
    for attempt in range(max_retries):
        try:
            response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                translations = [part.get("text", "Translation failed") for part in response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])]
                return [t.strip() if t != "Translation failed" else "Translation failed" for t in translations]
            
            elif response.status_code == 429:
                print(f"[WARNING] Rate limit exceeded. Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, 120)  # Exponential backoff (max wait time: 120s)
            
            else:
                print(f"Gemini API error: {response.status_code}, {response.text}")
                return ["Translation failed"] * len(texts)
        
        except Exception as e:
            print(f"[ERROR] Gemini API request failed: {e}")
            return ["Translation failed"] * len(texts)
    
    return ["Translation failed"] * len(texts)

# Function to fetch news from Apify Actor API
def fetch_news_from_apify(api_token):
    url = f"https://api.apify.com/v2/acts/buseta~crypto-news/run-sync-get-dataset-items?token={api_token}"
    try:
        print("Triggering the Apify Actor...")
        response = requests.post(url, timeout=600)
        if response.status_code == 201:
            return response.json()
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
        url = news.get("url", "#")  # Default to '#' if URL is missing
        if url not in seen_urls:
            unique_news.append(news)
            seen_urls.add(url)
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

    print("Translating news content using Gemini API in batches...")
    translated_news = []
    batch_size = 5  # Process 5 articles per batch
    
    for i in range(0, len(fetched_news), batch_size):
        batch = fetched_news[i:i + batch_size]
        titles = [news.get("title", "Untitled") for news in batch]
        descriptions = [news.get("description", "No description available.") for news in batch]
        contents = [news.get("content", "No content available.") for news in batch]

        translated_titles = translate_text_gemini(titles)
        translated_descriptions = translate_text_gemini(descriptions)
        translated_contents = translate_text_gemini(contents)

        for j, news in enumerate(batch):
            news["title"] = translated_titles[j] if translated_titles[j] != "Translation failed" else titles[j]
            news["description"] = translated_descriptions[j] if translated_descriptions[j] != "Translation failed" else descriptions[j]
            news["content"] = translated_contents[j] if translated_contents[j] != "Translation failed" else contents[j]
            translated_news.append(news)

    existing_data = load_existing_data()
    combined_news = remove_duplicates(translated_news + existing_data.get("all_news", []))
    save_to_json(combined_news)

    print("\nNewly Added News:")
    new_news = [news for news in combined_news if news not in existing_data.get("all_news", [])]
    for news in new_news:
        print(f"Title: {news['title']}\nURL: {news.get('url', '#')}\nContent Snippet: {news.get('content', '')[:100]}...\n")

if __name__ == "__main__":
    main()
