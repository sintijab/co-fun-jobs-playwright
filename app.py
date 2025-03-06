import asyncio
import urllib.parse
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from playwright.async_api import async_playwright

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
    "belgium": "/en-be/find-a-job/all-jobs/",
    "japan": "/ja-jp/job-search/すべてのジョブ/",
    "switzerland": "/de-de/stellensuche/?searchRadius=500km&country=Schweiz",
    "austria": "/de-de/stellensuche/?searchRadius=500km&country=Österreich",
    "czech republic": "/de-de/stellensuche/?searchRadius=500km&country=Tschechien"
}

BASE_URL = "https://www.computerfutures.com"

async def fetch_page(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENTS[0])
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        html = await page.content()
        await browser.close()
        return html

async def extract_job_links(html):
    job_links = []
    job_elements = html.split('<a href="')
    for element in job_elements:
        if "/job/" in element:
            link = element.split('"')[0]
            full_url = f"{BASE_URL}{link}" if link.startswith("/") else link
            job_links.append(full_url)
    return job_links

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
        return jsonify({"error": "Invalid country. Supported countries: " + ", ".join(COUNTRY_PATHS.keys())}), 400

    job_listings_url = BASE_URL + COUNTRY_PATHS[country]
    
    async def scrape():
        html = await fetch_page(job_listings_url)
        if not html:
            return {"error": "Failed to fetch job listing page"}, 500
        
        job_links = await extract_job_links(html)
        if not job_links:
            return {"error": "No job links found"}, 404
        
        return {"job_listings_url": job_listings_url, "jobs": [{"url": link} for link in job_links]}
    
    return jsonify(asyncio.run(scrape()))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
