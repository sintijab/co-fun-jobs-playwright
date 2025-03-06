import asyncio
import random
import urllib.parse
import json
from flask import Flask, Response, request, stream_with_context
from flask_cors import CORS, cross_origin
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "allow_headers": "*", "expose_headers": "*"}})

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.94 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.94 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.94 Safari/537.36"
]

COUNTRY_PATHS = {
    "united kingdom": "/en-gb/find-a-job/all-jobs/",
    "netherlands": "/nl-nl/werk-zoeken/alle-banen/",
    "germany": "/de-de/stellensuche/alle-jobs/",
    "france": "/fr-fr/trouver-un-job/tous-les-emplois/",
    "belgium": "/en-be/find-a-job/all-jobs/"
}

BASE_URL = "https://www.computerfutures.com"

async def fetch_page(url, browser):
    context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        return await page.content()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
    finally:
        await page.close()
        await context.close()

async def extract_job_details(url, browser):
    context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        title = await page.locator(".banner__title, .job-detail h1").text_content()
        content = await page.locator(".job__container, .job-detail").text_content()
        apply_links = await page.locator("a[href*='/apply']").all()
        apply_url = await apply_links[0].get_attribute("href") if apply_links else None
        return {
            "url": url,
            "title": title.strip() if title else "",
            "content": content.strip() if content else "",
            "apply": f"{BASE_URL}{apply_url}" if apply_url and apply_url.startswith("/") else apply_url
        }
    except Exception as e:
        print(f"Error fetching job details from {url}: {e}")
        return None
    finally:
        await page.close()
        await context.close()

async def extract_job_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = [a["href"] for a in soup.find_all("a", href=True) if "/job/" in a["href"]]
    return [f"{BASE_URL}{link}" if link.startswith("/") else link for link in links]

@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

@app.route('/health')
def hello_world():
    return 'OK'

@app.route('/api/scrape-jobs', methods=['GET'])
@cross_origin()
def scrape_jobs():
    country = request.args.get("country", "").strip().lower()
    country = urllib.parse.unquote(country)

    if country not in COUNTRY_PATHS:
        return Response(json.dumps({"error": "Invalid country. Supported countries: " + ", ".join(COUNTRY_PATHS.keys())}), mimetype='application/json', status=400)

    job_listings_url = BASE_URL + COUNTRY_PATHS[country]
    
    async def scrape():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--disable-gpu", "--no-sandbox"])
            html = await fetch_page(job_listings_url, browser)
            if not html:
                return json.dumps({"error": "Failed to fetch job listing page"})

            job_links = await extract_job_links(html)
            if not job_links:
                return json.dumps({"error": "No job links found"})

            jobs = []
            for job_link in job_links:
                job_detail = await extract_job_details(job_link, browser)
                if job_detail:
                    jobs.append(job_detail)
            await browser.close()
            return json.dumps({"job_listings_url": job_listings_url, "jobs": jobs})
    
    return Response(asyncio.run(scrape()), content_type='application/json')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
