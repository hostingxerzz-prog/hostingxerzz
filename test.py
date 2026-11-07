import asyncio
import api

async def main():
    seen = {}
    for v in await api.get_products():
        seen.setdefault(v["product_id"], (v["product_name"], v["platform"]))
    for pid, (n, p) in sorted(seen.items()):
        print(pid, "|", n, "|", p)

asyncio.run(main())