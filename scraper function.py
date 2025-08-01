import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def scrape_wuzzuf_jobs(query="python", location="Cairo", pages=1):
    headers = {"User-Agent": UserAgent().random}
    jobs = []

    for page in range(pages):
        url = f"https://wuzzuf.net/search/jobs/?a=navbg&q={query}&start={page * 10}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        for card in soup.select("div.css-1gatmva.e1v1l3u10"):
            title_tag = card.find("h2")
            company_tag = card.find("a", {"class": "css-17s97q8"})
            location_tag = card.find("span", {"class": "css-5wys0k"})
            link_tag = card.find("a", {"class": "css-o171kl"})

            if title_tag and company_tag and link_tag:
                jobs.append({
                    "title": title_tag.text.strip(),
                    "company": company_tag.text.strip(),
                    "location": location_tag.text.strip() if location_tag else "N/A",
                    "url": "https://wuzzuf.net" + link_tag["href"]
                })

    return jobs

