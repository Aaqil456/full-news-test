import os
import requests
import json
import time
import base64
from datetime import datetime

# === ENV VARIABLES ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
WP_URL = os.getenv("WP_URL", "https://teknologiblockchain.com/wp-json/wp/v2")
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")

NEWS_CATEGORY_ID = 1413  # WordPress category


# === GEMINI TRANSLATION HELPERS ===
def query_gemini(prompt):
    if not prompt or not isinstance(prompt, str):
        return "Translation failed"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for attempt in range(5):
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            elif response.status_code == 429:
                print(f"[Rate Limit] Retry {attempt+1}...")
                time.sleep(2 ** attempt)
            else:
                print(f"[Gemini Error] {response.status_code}: {response.text}")
                break
        except Exception as e:
            print(f"[Gemini Exception] {e}")
            break
    return "Translation failed"


def translate_for_facebook(text):
    prompt = f"""
Translate the following news into Malay.  
Then, kindly write a short conclusion or summary of the news in less than 280 characters in 1 paragraph.  
Only return the short conclusion without any explanation, heading, or intro phrase.  
Use natural, conversational, friendly Malaysian Malay — like how a friend shares info.  
Keep it simple, relaxed, and easy to understand.  
Avoid using exaggerated slang words or interjections (such as "Eh," "Korang," "Woi," "Wooohooo," "Wooo," or anything similar).  
No shouting words or unnecessary excitement.  
Keep it informative, approachable, and casual — but clean and neutral.  
Do not use emojis unless they appear in the original text.  
Do not translate brand names or product names.  
Do not phrase the summary as if it is referring to a news source — write it as a general insight or observation instead.  
⚠️ Do NOT include phrases like "Terjemahan:", "Kesimpulan:", "Baiklah,", "Secara ringkas", "**Conclusion:**", "**Translation:**", or anything similar. Just give the final sentence.
 
Original news:
'{text}'
"""
    return query_gemini(prompt)


def translate_for_wordpress(text):
    prompt = f"Translate this text '{text}' into Malay. Only return the translated text, structured like an article. Please exclude or don't take any sentences that looks like an advertisement from the text"
    return query_gemini(prompt)


# === FETCH NEWS ===
def fetch_news():
    url = f"https://api.apify.com/v2/acts/buseta~crypto-news/run-sync-get-dataset-items?token={APIFY_API_TOKEN}"
    try:
        response = requests.post(url, timeout=600)
        if response.status_code == 201:
            return response.json()
    except Exception as e:
        print(f"[Apify Exception] {e}")
    return []


# === WORDPRESS ===
def upload_image_to_wp(image_url):
    if not image_url:
        return None, None
    try:
        response = requests.get(image_url)
        if response.status_code != 200:
            return None, None
        image_data = response.content
        credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
        token = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {token}",
            "Content-Disposition": f"attachment; filename={image_url.split('/')[-1]}",
            "Content-Type": "image/jpeg"
        }
        upload_response = requests.post(f"{WP_URL}/media", headers=headers, data=image_data)
        if upload_response.status_code == 201:
            media = upload_response.json()
            return media.get("id"), media.get("source_url")
    except Exception as e:
        print(f"[Upload Error] {e}")
    return None, None


def post_to_wp(title, content, original_url, image_url=None, media_id=None):
    credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    post_data = {
        "title": title,
        "content": f"<h1>{title}</h1><br><img src='{image_url}' alt='{title}'/><br>{content}<p>📌 Baca artikel asal di sini: <a href='{original_url}'>{original_url}</a></p>",
        "status": "publish",
        "categories": [NEWS_CATEGORY_ID]
    }
    if media_id:
        post_data["featured_media"] = media_id

    try:
        response = requests.post(f"{WP_URL}/posts", headers=headers, json=post_data)
        return response.status_code == 201
    except Exception as e:
        print(f"[Post Error] {e}")
    return False


# === FACEBOOK ===
def post_to_facebook(image_url, caption):
    if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID or not image_url:
        print("[SKIP FB] Missing config or image.")
        return False
    data = {
        "url": image_url,
        "message": caption,
        "access_token": FB_PAGE_ACCESS_TOKEN
    }
    try:
        response = requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/photos", data=data)
        return response.status_code == 200
    except Exception as e:
        print(f"[FB Post Error] {e}")
    return False


# === SAVE JSON ===
def save_to_json(data):
    with open("translated_news.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "all_news": data
        }, f, ensure_ascii=False, indent=4)


# === MAIN ===
def main():
    fetched_news = fetch_news()
    if not fetched_news:
        print("[NO NEWS]")
        return

    all_results = []

    for idx, news in enumerate(fetched_news[:20]):
        print(f"\n[{idx+1}] Processing: {news.get('title')}")

        source = news.get("source", "")
        title_raw = news.get("title", "")
        summary_raw = news.get("summary", "")
        content_raw = news.get("content", "")
        original_url = news.get("link", "")
        image_url = news.get("image", "")
        timestamp = news.get("time", datetime.now().isoformat())

        # === Facebook Translation ===
        full_text = f"{title_raw}\n\n{summary_raw}\n\n{content_raw}"
        fb_caption = translate_for_facebook(full_text)

        # === Facebook Post ===
        fb_status = "Skipped"
        if image_url and fb_caption != "Translation failed":
            fb_status = "Posted" if post_to_facebook(image_url, fb_caption) else "Failed"

        # === WordPress Translation ===
        wp_title, wp_content, wp_summary = "", "", ""
        wp_status = "Skipped"
        media_id, uploaded_image_url = None, None

        if source == "Cointelegraph.com News":
            for _ in range(3):  # Retry 3x
                wp_title = translate_for_wordpress(title_raw)
                wp_content = translate_for_wordpress(content_raw)
                wp_summary = translate_for_wordpress(summary_raw)
                if wp_title != "Translation failed" and wp_content != "Translation failed":
                    break
                time.sleep(2)

            media_id, uploaded_image_url = upload_image_to_wp(image_url)
            wp_status = "Posted" if post_to_wp(wp_title, wp_content, original_url, uploaded_image_url, media_id) else "Failed"

        # === Save
        all_results.append({
            "title": title_raw,
            "translated_facebook_post": fb_caption,
            "translated_title": wp_title,
            "translated_content": wp_content,
            "translated_summary": wp_summary,
            "original_url": original_url,
            "source": source,
            "image": image_url,
            "fb_status": fb_status,
            "wp_status": wp_status,
            "timestamp": timestamp
        })

        time.sleep(1)

    save_to_json(all_results)
    print(f"\n✅ Done! {len(all_results)} items saved to translated_news.json")


if __name__ == "__main__":
    main()
