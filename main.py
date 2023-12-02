import json
import os
import random
import re
from typing import List
from urllib.parse import urlparse

import httpx
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass

import quart
import quart_cors
from quart import request

BASE_URL = "https://calscape.org"


@dataclass
class PlantDetails:
    common_name: str
    species: str
    # image_url: str
    description: str
    plant_type: str
    size: str
    form: str
    growth_rate: str
    dormancy: str
    fragrance: str
    flower_color: str
    flowering_season: str
    wildlife_supported: str
    sun: str
    moisture: str
    summer_irrigation: str
    ease_of_care: str
    cold_tolerance: str
    soil_drainage: str
    soil_description: str
    common_uses: str
    propagation: str
    sunset_zones: str
    site_type: str
    climate: str
    alternative_names: str


@dataclass
class PlantResult:
    id: int
    common_name: str
    species: str
    # image_url: str
    description: str
    slug: str


def get_last_path_fragment(url: str) -> str:
    parsed_url = urlparse(url)
    path_fragments = parsed_url.path.split('/')
    return path_fragments[-1] if path_fragments else ""


def parse_plant_results(html: str, limit: int = 20) -> List[PlantResult]:
    soup = BeautifulSoup(html, 'html.parser')
    plant_rows = soup.select('.content.view_list .row')
    results = []
    for row in plant_rows:
        plant_id = int(row.get('id').split('__')[-1])
        common_name = row.select_one('.common_name').text.strip()
        species = row.select_one('.species').text.strip()
        # image_url = row.select_one('.image img').get('src')
        description = row.select_one('.desc').text.strip()
        url = row.select_one('.image a').get('onclick')
        match = re.search(r"url:'(.+?)'", url)
        slug = match.group(1) if match else ""
        slug = get_last_path_fragment(slug)
        results.append(PlantResult(
            id=plant_id,
            common_name=common_name,
            species=species,
            # image_url=BASE_URL + image_url,
            description=description,
            slug=slug
        ))
    return random.sample(results, min(limit, len(results)))


def parse_plant_details(html: str) -> PlantDetails:
    soup = BeautifulSoup(html, 'html.parser')

    def extract_text(selector: str) -> str:
        element = soup.select_one(selector)
        return element.text.strip() if element else ""

    # def extract_attr(selector: str, attr: str) -> str:
    #     element = soup.select_one(selector)
    #     return element.get(attr) if element else ""

    plant_details = {
        "common_name": extract_text(".common_name"),
        "species": extract_text(".species_info .sub_header1"),
        # "image_url": extract_attr("#slideshow img", "src"),
        "description": extract_text("fieldset.about"),
        "plant_type": extract_text(".plant_info .plant_type .info"),
        "size": extract_text(".plant_info .size .info"),
        "form": extract_text(".plant_info .form .info"),
        "growth_rate": extract_text(".plant_info .growth_rate .info"),
        "dormancy": extract_text(".plant_info .dormancy .info"),
        "fragrance": extract_text(".plant_info .fragrance .info"),
        "flower_color": extract_text(".plant_info .flower_color .info"),
        "flowering_season": extract_text(".plant_info .flowering_season .info"),
        "wildlife_supported": extract_text(".plant_info .wildlife_supported .info"),
        "sun": extract_text(".plant_info .sun .info"),
        "moisture": extract_text(".plant_info .moisture .info"),
        "summer_irrigation": extract_text(".plant_info .summer_irrigation .info"),
        "ease_of_care": extract_text(".plant_info .ease_of_care .info"),
        "cold_tolerance": extract_text(".plant_info .cold_tolerance .info"),
        "soil_drainage": extract_text(".plant_info .soil_drainage .info"),
        "soil_description": extract_text(".plant_info .soil_description .info"),
        "common_uses": extract_text(".plant_info .common_uses .info"),
        "propagation": extract_text(".plant_info .propagation .info"),
        "sunset_zones": extract_text(".plant_info .sunset_zones .info"),
        "site_type": extract_text(".plant_info .site_type .info"),
        "climate": extract_text(".plant_info .climate .info"),
        "alternative_names": extract_text(".plant_info .alternative_names .info"),
    }

    return PlantDetails(**plant_details)


# Note: Setting CORS to allow chat.openapi.com is required for ChatGPT to access your plugin
app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")


@app.get("/detail/<string:slug>")
async def detail(slug: str):
    url = f"{BASE_URL}/search/x/{slug}"
    resp = requests.get(url)
    plant_details = parse_plant_details(resp.text)
    return quart.Response(json.dumps(plant_details.__dict__), content_type="application/json")


@app.post("/search")
async def search():
    form_data = await request.get_data()
    async with httpx.AsyncClient() as client:
        res1 = await client.post(
            BASE_URL + "/search/vw-list",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if res1.status_code != 302:
            return parse_plant_results(res1.text)
        redirected_url = res1.headers.get("Location")
        res2 = await client.get(f"{BASE_URL}{redirected_url}")
    return parse_plant_results(res2.text)


@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    with open("ai-plugin.json") as f:
        text = f.read()
        protocol = "http" if os.getenv("DEV") else "https"
        text = text.replace("PLUGIN_HOSTNAME", f"{protocol}://{request.headers['Host']}")
        return quart.Response(text, mimetype="text/json")


@app.get("/openapi.yaml")
async def openapi_spec():
    with open("calscape.yaml") as f:
        text = f.read()
        protocol = "http" if os.getenv("DEV") else "https"
        text = text.replace("PLUGIN_HOSTNAME", f"{protocol}://{request.headers['Host']}")
        return quart.Response(text, mimetype="text/yaml")


@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')


def main():
    app.run(debug=True, host="0.0.0.0", port=5002)


if __name__ == "__main__":
    main()
