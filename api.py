import os, time, aiohttp
from dotenv import load_dotenv

load_dotenv()
API_BASE = "https://dripclientofficial.shop/api/v1"
HEADERS = {"X-API-Token": os.getenv("API_TOKEN"), "Accept": "application/json"}

_cache = {}
CACHE_TTL = 300  # 5 минут

async def call(endpoint, params=None, method="GET"):
    url = f"{API_BASE}/{endpoint}"
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        if method == "GET":
            r = await s.get(url, params=params, timeout=30)
        else:
            r = await s.post(url, data=params, timeout=30)
        data = await r.json(content_type=None)
    if not data.get("success", True):
        raise Exception(data.get("error", "API қатесі"))
    return data

async def cached(endpoint):
    now = time.time()
    if endpoint in _cache and now - _cache[endpoint][0] < CACHE_TTL:
        return _cache[endpoint][1]
    data = await call(endpoint)
    _cache[endpoint] = (now, data)
    return data

async def get_products():
    data = await cached("products.php")
    return (data.get("data") or {}).get("products") or data.get("products") or []

async def get_balance():
    return await call("balance.php")

async def generate(variant_id, quantity=1, android_id=None, api_version=None):
    body = {"variant_id": variant_id, "quantity": quantity}
    if android_id: body["android_id"] = android_id
    if api_version: body["api_version"] = api_version
    return await call("generate_key.php", body, "POST")