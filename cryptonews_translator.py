import os
import requests
import json
import time
from datetime import datetime

# Define Gemini API URL
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Function to translate text using Gemini API with Exponential Backoff
def translate_text_gemini(text, max_retries=5, base_wait_time=2):
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

    retries = 0
    while retries < max_retries:
        try:
            response = requests.post(GEMINI_API_URL, headers=headers, json=payload)

            if response.status_code == 200:
                response_data = response.json()
                translated_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Translation failed")
                return translated_text.strip() if translated_text != "Translation failed" else "Translation failed"
            
            elif response.status_code == 429:  # Rate Limit Exceeded
                wait_time = base_wait_time * (2 ** retries)  # Exponential backoff
                print(f"[WARNING] Rate limit exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
                continue

            else:
                print(f"[ERROR] Gemini API error: {response.status_code}, {response.text}")
                return "Translation failed"

        except Exception as e:
            print(f"[ERROR] Gemini API request failed: {e}")
            return "Translation failed"

    print("[ERROR] Max retries reached. Skipping translation.")
    return "Translation failed"

# Function to fetch news from Apify Actor API
def fetch_news_from_apify(api_token):
    url = f"https://api.apify.com/v2/acts/buseta~crypto-news/run-sync-get-dataset-items?token={api_token}"
    try:
        print("Triggering the Apify Actor...")
        response = requests.post(url, timeout=600)
        if response.status_code == 201:
            return response.json()
        else:
            print(f"[ERROR] Failed to fetch news from Apify: {response.status_code}, {response.text}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Exception occurred while fetching data from Apify: {e}")
        return []

# Function to load existing data
def load_existing_data(filename="translated_news.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"all_news": []}  # Return empty structure if JSON is corrupted
    return {"all_news": []}

# Function to remove duplicates
def remove_duplicates(news_list):
    seen_urls = set()
    unique_news = []
    
    for news in news_list:
        url = news.get("url")
        title = news.get("title")
        
        if url and title and url not in seen_urls:
            unique_news.append(news)
            seen_urls.add(url)
    
    return unique_news

# Function to save news to JSON
def save_to_json(data, filename="translated_news.json"):
    if not data:
        print("\n[WARNING] No new articles to save. Skipping JSON update.")
        return  

    output = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "all_news": data
    }

    # 🔥 Debug: Print JSON content before saving
    print("\n[DEBUG] JSON data before saving:")
    print(json.dumps(output, indent=4, ensure_ascii=False))

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"\n[INFO] Successfully saved {len(data)} articles to {filename}")

    # 🔥 Debug: Check if file is saved
    with open(filename, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        print("\n[DEBUG] JSON data after saving:")
        print(json.dumps(saved_data, indent=4, ensure_ascii=False))


# Main function
def main():
    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
    if not APIFY_API_TOKEN:
        print("[ERROR] API token is missing! Please set APIFY_API_TOKEN as an environment variable.")
        return

    print("\n[INFO] Fetching news from Apify Actor API...")
    fetched_news = fetch_news_from_apify(APIFY_API_TOKEN)

    print("\n[INFO] Translating news content using Gemini API...")
    translated_news = []
    success_count = 0
    failed_count = 0

    for news in fetched_news:
        original_title = news.get("title", "Untitled")
        original_description = news.get("description", "No description available.")
        original_content = news.get("content", "No content available.")

        translated_title = translate_text_gemini(original_title)
        translated_description = translate_text_gemini(original_description)
        translated_content = translate_text_gemini(original_content)

        if "Translation failed" not in (translated_title, translated_description, translated_content):
            news["title"] = translated_title
            news["description"] = translated_description
            news["content"] = translated_content
            translated_news.append(news)
            success_count += 1
            print(f"✔ Successfully Translated: {translated_title}")
        else:
            failed_count += 1
            print(f"✖ Skipping news (translation failed or rate limit exceeded): {original_title}")

    # 🔥 Load existing data to ensure it's appended
    existing_data = load_existing_data()
    all_news = existing_data.get("all_news", [])

    # 🔥 Debug: Print current articles
    print("\n[DEBUG] Articles in existing JSON before adding new:")
    print(json.dumps(all_news, indent=4, ensure_ascii=False))

    # Append and remove duplicates
    combined_news = remove_duplicates(all_news + translated_news)

    # 🔥 Debug: Check articles after processing
    print("\n[DEBUG] Articles before saving:")
    print(json.dumps(combined_news, indent=4, ensure_ascii=False))

    if translated_news:  # Ensure at least one article was translated
        print(f"[DEBUG] Total articles before saving: {len(combined_news)}")
        save_to_json(combined_news)
    else:
        print("[WARNING] No new translations were added.")

    print("\n========== Translation Summary ==========")
    print(f"✔ Successfully Translated: {success_count} articles")
    print(f"✖ Failed to Translate: {failed_count} articles")
    print("========================================")


if __name__ == "__main__":
    main()
