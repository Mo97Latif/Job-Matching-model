import json
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import boto3
import datetime
import re
from collections import Counter

S3_BUCKET = "your-bucket-name"  # Replace with your actual bucket name

# === 1. Basic NLP: Extract top keywords from plain text CV ===
def extract_keywords_from_text(text, top_n=5):
    # Convert to lowercase, remove punctuation/numbers
    text = re.sub(r"[^a-zA-Z\s]", "", text.lower())
    words = text.split()

    # Basic list of stop words (could be replaced with nltk/Spacy)
    stop_words = set([
        "the", "and", "for", "with", "you", "are", "that", "your", "have", "will", 
        "this", "from", "not", "but", "can", "all", "use", "has", "more", "our", 
        "such", "who", "they", "job", "role", "work", "also", "experience", "skills"
    ])

    # Count words excluding stop words
    filtered = [w for w in words if w not in stop_words and len(w) > 2]
    counts = Counter(filtered)

    # Return top N keywords
    return [word for word, _ in counts.most_common(top_n)]

# === 2. Scrape Wuzzuf jobs based on keyword search ===
def scrape_wuzzuf_jobs(query="python", pages=1):
    headers = {"User-Agent": UserAgent().random}
    jobs = []

    for page in range(pages):
        url = f"https://wuzzuf.net/search/jobs/?a=navbg&q={query}&start={page * 10}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        for card in soup.select("div.css-1gatmva.e1v1l3u10"):
            title = card.find("h2")
            company = card.find("a", {"class": "css-17s97q8"})
            location = card.find("span", {"class": "css-5wys0k"})
            link = card.find("a", {"class": "css-o171kl"})

            if title and company and link:
                jobs.append({
                    "title": title.text.strip(),
                    "company": company.text.strip(),
                    "location": location.text.strip() if location else "N/A",
                    "url": "https://wuzzuf.net" + link["href"]
                })

    return jobs

# === 3. Lambda entry point ===
def lambda_handler(event, context):
    # Example input:
    # {
    #   "cv_key": "cv-folder/user123.txt",
    #   "pages": 2
    # }

    cv_key = event.get("cv_key")
    pages = int(event.get("pages", 1))

    if not cv_key:
        return {"statusCode": 400, "body": "cv_key is required in the event."}

    # === Load the CV from S3 ===
    s3 = boto3.client("s3")
    cv_obj = s3.get_object(Bucket=S3_BUCKET, Key=cv_key)
    cv_text = cv_obj["Body"].read().decode("utf-8")

    # === Extract top keywords from the CV ===
    keywords = extract_keywords_from_text(cv_text)
    print("Extracted keywords:", keywords)

    # === Scrape jobs for each keyword ===
    all_jobs = []
    for kw in keywords:
        jobs = scrape_wuzzuf_jobs(query=kw, pages=pages)
        all_jobs.extend(jobs)

    # === Remove duplicates (by URL) ===
    unique_jobs = {job["url"]: job for job in all_jobs}.values()

    # === Save results to S3 ===
    timestamp = datetime.datetime.now().isoformat()
    out_key = f"wuzzuf_matched_jobs/{cv_key.replace('/', '_')}_{timestamp}.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=out_key,
        Body=json.dumps(list(unique_jobs)),
        ContentType="application/json"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Scraped based on CV",
            "cv_used": cv_key,
            "keywords": keywords,
            "results_file": out_key
        })
    }
