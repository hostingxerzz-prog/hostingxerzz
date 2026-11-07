import os, re, hmac, hashlib, json, random
from urllib.parse import parse_qsl
from datetime import datetime, timedelta
from fastapi import FastAPI, Header, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from backend import api_client as api
from backend import db
from products import CATALOG, PRICES, USD_KZT, USD_RUB, RESET_RULES

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# ─── Бот константалары (дәл сол) ───
RESELLER_SHARE = 0.5
REF_BONUS = 0.1
LUCKY_MIN, LUCKY_MAX = 0.01, 0.10
LUCKY_DAYS = 7
RESET_LIMIT = 3
TS_FMT = "%Y-%m-%d %H:%M:%S"
BINANCE_ID = "1254750465"
KASPI_PHONE = "87782935178"
KASPI_NAME = "Қанат Б"

db.init()
app = FastAPI(title="XERZZ Mini App")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ═══════════════════ Telegram initData тексеру ═══════════════════
def verify_init_data(init_data: str) -> dict:
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(401, "No hash in initData")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if calc != received_hash:
        raise HTTPException(401, "Invalid initData hash")
    user = json.loads(parsed.get("user", "{}"))
    return user


def auth(x_init_data: str = Header(None)):
    if not x_init_data:
        raise HTTPException(401, "No initData")
    u = verify_init_data(x_init_data)
    if not u.get("id"):
        raise HTTPException(401, "No user in initData")
    db.get_user(u["id"], u.get("first_name"))
    return u


# ═══════════════════ Баға логикасы (боттан көшірілген) ═══════════════════
def norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


PRICE_BY_NORM, EMOJI_BY_NORM = {}, {}
for _c, _name, _emoji, _aliases in CATALOG:
    for _a in (_aliases or [_name]):
        PRICE_BY_NORM.setdefault(norm(_a), PRICES.get(_name))
        EMOJI_BY_NORM.setdefault(norm(_a), _emoji)


def vkey(v):
    unit = str(v.get("validity_unit") or "").lower()
    try:
        n = float(v.get("validity"))
    except (TypeError, ValueError):
        n = None
    if n is not None and n > 0:
        if unit.startswith("hour"):
            return ("h", n)
        if unit.startswith("day"):
            return ("d", n)
        if unit.startswith("month"):
            return ("d", n * 30)
    return ("t", norm(str(v.get("variant_name", ""))))


def retail_usd(v):
    t = PRICE_BY_NORM.get(norm(v["product_name"]))
    return t.get(vkey(v)) if t else None


def unit_price(v, uid):
    cost = float(v["price"])
    if uid == ADMIN_ID:
        return cost
    retail = retail_usd(v)
    if retail is None:
        return None
    if db.tier(uid, ADMIN_ID) == "RESELLER" and retail > cost:
        return round(cost + (retail - cost) * RESELLER_SHARE, 2)
    return retail


def out_of_stock(v):
    return (not v.get("unlimited")) and (v.get("in_stock") or 0) <= 0


def max_qty(v):
    m = 1 if (v.get("requires_android_id") or v.get("is_balamod")) else 3
    if not v.get("unlimited"):
        m = min(m, int(v.get("in_stock") or 0))
    return max(m, 0)


def label_variant(v):
    k = vkey(v)
    if k[0] == "h":
        return f"{k[1]:g} hours"
    if k[0] == "d":
        return f"{k[1]:g} days"
    return str(v.get("variant_name", ""))


def strip_balance(x):
    if isinstance(x, dict):
        return {k: strip_balance(v) for k, v in x.items() if "balance" not in k.lower()}
    if isinstance(x, list):
        return [strip_balance(i) for i in x]
    return x


KEY_FIELDS = {"key", "keys", "license", "license_key", "licence",
              "licence_key", "serial", "username"}


def extract_keys(data):
    out = []

    def walk(o, field=None):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, str(k).lower())
        elif isinstance(o, list):
            for i in o:
                walk(i, field)
        elif isinstance(o, str) and field in KEY_FIELDS and o.strip():
            out.append(o.strip())

    walk(data)
    return list(dict.fromkeys(out))


# ═══════════════════ ROUTES ═══════════════════

@app.get("/api/me")
async def me(x_init_data: str = Header(None)):
    u = auth(x_init_data)
    info = db.get_user(u["id"])
    return dict(
        id=u["id"], name=info.get("name") or u.get("first_name"),
        lang=info.get("lang") or "kk",
        balance=round(info["balance"] or 0, 2),
        tier=db.tier(u["id"], ADMIN_ID),
        spent=info.get("spent") or 0,
        orders=info.get("orders") or 0,
        referrals=info.get("referrals") or 0,
        ref_earned=info.get("ref_earned") or 0,
        created=info.get("created_at"),
    )


@app.post("/api/lang")
async def set_lang(payload: dict = Body(...), x_init_data: str = Header(None)):
    u = auth(x_init_data)
    if payload.get("lang") in ("kk", "ru", "en"):
        db.set_lang(u["id"], payload["lang"])
    return {"ok": True}


@app.get("/api/catalog")
async def catalog(cat: str = "NONROOT", x_init_data: str = Header(None)):
    u = auth(x_init_data)
    uid = u["id"]
    variants = await api.get_products()
    items = []
    known = set()

    for c, name, emoji, aliases in CATALOG:
        if c != cat:
            continue
        keys = {norm(a) for a in (aliases or [name])}
        known |= keys
        vs = [v for v in variants if norm(v["product_name"]) in keys]
        plans = []
        for v in vs:
            price = unit_price(v, uid)
            if price is None:
                continue
            plans.append(dict(
                variant_id=v["variant_id"],
                label=label_variant(v),
                price_usd=price,
                price_kzt=round(price * USD_KZT),
                price_rub=round(price * USD_RUB),
                stock=("∞" if v.get("unlimited") else int(v.get("in_stock") or 0)),
                out=out_of_stock(v),
                max_qty=max_qty(v),
                android=bool(v.get("requires_android_id")),
            ))
        plans.sort(key=lambda p: p["price_usd"])
        if plans:
            items.append(dict(name=name, emoji=emoji, plans=plans))

    # OTHER санатына API-да бар, бірақ каталогта жоқтарын қосу
    if cat == "OTHER":
        extra = {}
        for v in variants:
            if norm(v["product_name"]) not in known:
                extra.setdefault(v["product_id"], v["product_name"])
        for pid in sorted(extra):
            items.append(dict(name=extra[pid], emoji=None, plans=[]))

    return {"items": items}


@app.post("/api/buy")
async def buy(payload: dict = Body(...), x_init_data: str = Header(None)):
    u = auth(x_init_data)
    uid = u["id"]
    vid = int(payload["variant_id"])
    qty = int(payload.get("qty", 1))
    android_id = payload.get("android_id")

    variant = None
    for v in await api.get_products():
        if v["variant_id"] == vid:
            variant = v
            break
    if not variant:
        raise HTTPException(404, "Variant not found")
    unit = unit_price(variant, uid)
    if unit is None:
        raise HTTPException(400, "Unavailable")
    if out_of_stock(variant):
        raise HTTPException(400, "Out of stock")
    qty = max(1, min(qty, max_qty(variant)))
    if variant.get("requires_android_id") and not android_id:
        raise HTTPException(400, "android_id required")

    total = round(unit * qty, 2)
    if db.get_user(uid)["balance"] < total:
        raise HTTPException(402, "Not enough balance")

    db.change_balance(uid, -total)
    try:
        data = await api.generate(vid, qty, android_id=android_id)
    except Exception as ex:
        db.change_balance(uid, total)
        raise HTTPException(500, str(ex))

    keys = extract_keys(data)
    c = db.conn()
    c.execute("UPDATE users SET spent=ROUND(spent+?,2), orders=orders+1 WHERE id=?",
              (total, uid))
    for k in keys:
        c.execute("""INSERT INTO keys (uid, product, label, license, price, ts)
                     VALUES (?,?,?,?,?,?)""",
                  (uid, variant["product_name"], label_variant(variant), k, unit, db.now()))
    c.commit()
    c.close()

    return dict(
        ok=True,
        keys=keys,
        total=total,
        balance=round(db.get_user(uid)["balance"], 2),
        raw=None if keys else strip_balance(data),
    )


@app.get("/api/mykeys")
async def mykeys(x_init_data: str = Header(None)):
    u = auth(x_init_data)
    c = db.conn()
    rows = c.execute("""SELECT id, product, label, license, ts, resets
                        FROM keys WHERE uid=? ORDER BY id DESC LIMIT 50""",
                     (u["id"],)).fetchall()
    c.close()
    return {"keys": [dict(r) for r in rows]}


@app.post("/api/reset")
async def reset_key(payload: dict = Body(...), x_init_data: str = Header(None)):
    u = auth(x_init_data)
    uid = u["id"]
    key = payload.get("key", "").strip()
    c = db.conn()
    row = c.execute("""SELECT id, product, resets, uid FROM keys
                       WHERE license=? ORDER BY id DESC""", (key,)).fetchone()
    c.close()
    if not row or (row["uid"] != uid and uid != ADMIN_ID):
        raise HTTPException(404, "Key not found")
    if row["resets"] >= RESET_LIMIT and uid != ADMIN_ID:
        raise HTTPException(400, f"Reset limit reached ({RESET_LIMIT}/{RESET_LIMIT})")

    rule = None
    n = norm(row["product"])
    for kw, api_name, param in RESET_RULES:
        if kw in n:
            rule = (api_name, param)
            break
    if not rule:
        raise HTTPException(400, "Reset not available for this product")

    try:
        await api.call("reset_key.php", {"api": rule[0], rule[1]: key}, "POST")
    except Exception as ex:
        raise HTTPException(500, str(ex))

    c = db.conn()
    c.execute("UPDATE keys SET resets=resets+1 WHERE id=?", (row["id"],))
    c.commit()
    c.close()
    return {"ok": True, "left": max(0, RESET_LIMIT - row["resets"] - 1)}


@app.post("/api/lucky")
async def lucky(x_init_data: str = Header(None)):
    u = auth(x_init_data)
    uid = u["id"]
    info = db.get_user(uid)
    last = None
    if info.get("last_lucky"):
        try:
            last = datetime.strptime(info["last_lucky"], TS_FMT)
        except ValueError:
            last = None
    if last and datetime.now() - last < timedelta(days=LUCKY_DAYS):
        left = last + timedelta(days=LUCKY_DAYS) - datetime.now()
        raise HTTPException(400, f"Already claimed. {left.days}d {left.seconds // 3600}h left")
    amount = round(random.uniform(LUCKY_MIN, LUCKY_MAX), 2)
    db.change_balance(uid, amount)
    db.touch_lucky(uid)
    return {"ok": True, "amount": amount,
            "balance": round(db.get_user(uid)["balance"], 2)}


@app.get("/api/referral")
async def referral(x_init_data: str = Header(None)):
    u = auth(x_init_data)
    info = db.get_user(u["id"])
    import aiohttp
    async with aiohttp.ClientSession() as s:
        r = await s.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
        me = (await r.json()).get("result", {})
    return dict(
        link=f"https://t.me/{me.get('username')}?start=ref_{u['id']}",
        referrals=info.get("referrals") or 0,
        earned=info.get("ref_earned") or 0,
        bonus=REF_BONUS,
    )


@app.get("/api/top")
async def top(x_init_data: str = Header(None)):
    auth(x_init_data)
    month = datetime.now().strftime("%Y-%m")
    c = db.conn()
    rows = c.execute("""SELECT uid, COUNT(*) n FROM keys
                        WHERE substr(ts,1,7)=?
                        GROUP BY uid ORDER BY n DESC LIMIT 5""",
                     (month,)).fetchall()
    out = []
    for i, r in enumerate(rows, 1):
        u = c.execute("SELECT name, balance, reseller FROM users WHERE id=?",
                      (r["uid"],)).fetchone()
        out.append(dict(
            rank=i,
            name=(u["name"] if u else f"User {r['uid']}"),
            tier="RESELLER" if u and u["reseller"] else "USER",
            keys=r["n"],
            balance=round(u["balance"], 2) if u else 0,
        ))
    c.close()
    return {"top": out}


@app.post("/api/topup")
async def topup(payload: dict = Body(...), x_init_data: str = Header(None)):
    u = auth(x_init_data)
    amount = float(payload["amount"])
    method = payload["method"]
    if not (1 <= amount <= 100):
        raise HTTPException(400, "Amount must be 1-100 USD")
    if method not in ("binance", "kaspi"):
        raise HTTPException(400, "Bad method")
    c = db.conn()
    cur = c.execute("""INSERT INTO topups (uid, amount, method, status, ts)
                       VALUES (?,?,?,?,?)""",
                    (u["id"], amount, method, "pending", db.now()))
    c.commit()
    oid = cur.lastrowid
    c.close()
    details = ({"binance_id": BINANCE_ID} if method == "binance"
               else {"phone": KASPI_PHONE, "name": KASPI_NAME,
                     "kzt": round(amount * USD_KZT)})
    return dict(order_id=oid, amount=amount, method=method, details=details)


@app.post("/api/reseller")
async def become_reseller(payload: dict = Body(...), x_init_data: str = Header(None)):
    u = auth(x_init_data)
    uid = u["id"]
    if db.tier(uid, ADMIN_ID) != "USER":
        raise HTTPException(400, "Already reseller")
    login = payload.get("login", "").strip()
    password = payload.get("password", "").strip()
    c = db.conn()
    row = c.execute("SELECT password, used_by FROM resellers WHERE login=?",
                    (login,)).fetchone()
    if not row or row["password"] != password or row["used_by"] not in (None, uid):
        c.close()
        raise HTTPException(400, "Invalid credentials")
    c.execute("UPDATE resellers SET used_by=? WHERE login=?", (uid, login))
    c.execute("UPDATE users SET reseller=1 WHERE id=?", (uid,))
    c.commit()
    c.close()
    return {"ok": True}


# Frontend-ті сол серверден беру
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)