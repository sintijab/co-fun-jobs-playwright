import pytest
import asyncio
import httpx
from Flask_Requests_Html import app, fetch_page, extract_job_links

BASE_URL = "http://127.0.0.1:8000"

@pytest.fixture
def test_client():
    """Fixture to provide a test client for the Flask app."""
    return httpx.Client(base_url=BASE_URL)

@pytest.mark.asyncio
async def test_fetch_page():
    url = "https://www.computerfutures.com/en-gb/find-a-job/all-jobs/"
    html = await fetch_page(url)
    
    assert html is not None
    assert "<html" in html.lower()

@pytest.mark.asyncio
async def test_extract_job_links():
    sample_html = '''
        <html>
        <body>
            <a href="/job/software-developer">Software Developer</a>
            <a href="/job/data-scientist">Data Scientist</a>
        </body>
        </html>
    '''
    job_links = await extract_job_links(sample_html)

    assert len(job_links) == 2
    assert job_links[0] == "https://www.computerfutures.com/job/software-developer"
    assert job_links[1] == "https://www.computerfutures.com/job/data-scientist"

def test_scrape_jobs_valid_country(test_client):
    response = test_client.get("/api/scrape-jobs?country=united kingdom")
    
    assert response.status_code == 200
    json_data = response.json()
    assert "jobs" in json_data
    assert isinstance(json_data["jobs"], list)

def test_scrape_jobs_invalid_country(test_client):
    response = test_client.get("/api/scrape-jobs?country=unknownland")
    
    assert response.status_code == 400
    json_data = response.json()
    assert "error" in json_data
