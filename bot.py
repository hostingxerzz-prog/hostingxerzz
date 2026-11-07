import os, re, io, json, html, random, sqlite3, asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                           InlineKeyboardButton, BufferedInputFile)
from dotenv import load_dotenv
import api
from products import CATALOG, PRICES, USD_KZT, USD_RUB, RESET_RULES

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
from aiogram.types import WebAppInfo

load_dotenv()
bot = Bot(os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ───────────── Баптаулар (өзгертуге болады) ─────────────
RESELLER_SHARE = 0.5      # реселлер үшін: өзіндік баға мен сату бағасы арасындағы үлес (0.5 = дәл ортасы)
REF_BONUS = 0.1           # әр шақырылған адам үшін ($)
LUCKY_MIN, LUCKY_MAX = 0.01, 0.10
LUCKY_DAYS = 7
RESET_LIMIT = 3
BINANCE_ID = "1254750465"
KASPI_PHONE = "87782935178"
KASPI_NAME = "Қанат Б"
SUPPORT = "@xerzcheat"
TS_FMT = "%Y-%m-%d %H:%M:%S"


def now():
    return datetime.now().strftime(TS_FMT)


def is_admin(uid):
    return uid == ADMIN_ID


# ───────────── Premium emoji ID-лері ─────────────
EM = dict(
    lang_hdr="6188045471118790922",
    kz="5228718354658769982", ru="5449408995691341691", en="5422520224085720580",
    shop="5264959791213586839", add="5278467510604160626", profile="5942901773088857071",
    reseller="5951766778861328139", language="5399898266265475100", lucky="5204076520963842994",
    share="5325613662965093403", support="5215668805199473901", top="5467406098367521267",
    admin="6129805886383723340", store="5983399041197675256", hi="5319007286004299794",
    excl="5467519850576354798", up="5287686383027114707", dash="5332447793451654491",
    red="6012736652831625680", ok1="5440372981501022181", smile="6217630318250168874",
    money="6298411471902608514", ok2="5337006433084912502", wallet="6176751090109784137",
    fire="6177030215739383438", bang="5893072412924187198", back="5253997076169115797",
    cart="5391266730620246169", phone="5832661262659493258", store2="5938274774756103272",
    fire2="6037603267934951990", tier="5767161061480340249",
    c_nonroot="6199417621100629765", c_root="6199417621100629765",
    c_pc="5967816500415827773", c_ios="5818920837645867167", c_other="6159146671998502143",
    # жаңа бөлімдер
    confirm="5456432998092133477", binance="5843689746538173057", kaspi="5264713728242231769",
    tel="5453965363286925977", users="5258486128742244085", id="5888781182249738113",
    type="5238133661705986706", trophy="5422546251587527850", cal="5816442787544964208",
    money2="5224257782013769471", orders="5373052667671093676", spent="5472030678633684592",
    star="5435957248314579621", key="5454386656628991407", lock="6019523512908124649",
    user1="5256143829672672750", minus="5305765300535311154", chart="5449872877929127395",
    mega="5890997763331591703", reset="5809915618371050638",
)


def e(key, ch):
    """key — EM ішіндегі атау немесе тікелей emoji ID."""
    return f'<tg-emoji emoji-id="{EM.get(key, key)}">{ch}</tg-emoji>'


# ───────────── Мәтіндер (3 тіл) ─────────────
T = {
    "kk": dict(
        welcome="Қош келдің", highlights="ДҮКЕН АРТЫҚШЫЛЫҚТАРЫ",
        l1="Премиум ойын кілттері", l2="24/7 лезде жеткізу", l3="100% қауіпсіз төлем",
        l4="Сенімді әрі қауіпсіз", l5="Кәсіби қолдау",
        wallet="Әмиян балансы", tap="Бастау үшін «Дүкен» батырмасын бас",
        shop="Дүкен / Өнімдер", add="Балансты толтыру", profile="Профиль",
        reseller="Реселлер болу", lang="Тіл", lucky="Лаки", share="Бөлісу",
        support="Қолдау", top="Айдың топ 5 сатушысы", admin="Админ аккаунт",
        back="Артқа",
        nofunds="❌ Балансың жеткіліксіз. Алдымен балансты толтыр.",
        confirm="Балансыңнан шегеріледі. Растайсың ба?", gen="✅ Сатып алу",
        cancel="❌ Болдырмау", android="Android ID жібер (6-64 таңба):",
        android_bad="❌ Android ID дұрыс емес. Қайта жібер.",
        unavailable="Қазір қолжетімсіз", oos="❌ Қорда жоқ",
    ),
    "ru": dict(
        welcome="Добро пожаловать", highlights="ПРЕИМУЩЕСТВА МАГАЗИНА",
        l1="Премиум игровые ключи", l2="Мгновенная выдача 24/7", l3="100% безопасная оплата",
        l4="Надёжно и безопасно", l5="Профессиональная поддержка",
        wallet="Баланс кошелька", tap="Нажми «Магазин», чтобы начать",
        shop="Магазин / Товары", add="Пополнить баланс", profile="Профиль",
        reseller="Стать реселлером", lang="Язык", lucky="Лаки", share="Поделиться",
        support="Поддержка", top="Топ 5 продавцов месяца", admin="Админ аккаунт",
        back="Назад",
        nofunds="❌ Недостаточно средств. Сначала пополни баланс.",
        confirm="Сумма будет списана с баланса. Подтверждаешь?", gen="✅ Купить",
        cancel="❌ Отмена", android="Отправь Android ID (6-64 символа):",
        android_bad="❌ Неверный Android ID. Отправь ещё раз.",
        unavailable="Сейчас недоступно", oos="❌ Нет в наличии",
    ),
    "en": dict(
        welcome="Welcome", highlights="STORE HIGHLIGHTS",
        l1="Premium Game Keys", l2="Instant Delivery 24/7", l3="100% Secure Payment",
        l4="Safe and Trusted", l5="Professional Support",
        wallet="Wallet Balance", tap="Tap Shop Now to Start",
        shop="Shop / Product", add="Add balance", profile="My Profile",
        reseller="Upgrade to Reseller", lang="Language", lucky="Lucky", share="Share",
        support="Support", top="Top 5 Sellers Monthly", admin="Admin Account",
        back="Back",
        nofunds="❌ Not enough balance. Please add balance first.",
        confirm="The price will be deducted from your balance. Confirm?", gen="✅ Buy",
        cancel="❌ Cancel", android="Send your Android ID (6-64 characters):",
        android_bad="❌ Invalid Android ID. Send it again.",
        unavailable="Currently unavailable", oos="❌ Out of stock",
    ),
}


# ───────────── Дерекқор ─────────────
db = sqlite3.connect("users.db")
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT, balance REAL DEFAULT 0)")
for _col in ("reseller INTEGER DEFAULT 0", "created_at TEXT", "name TEXT",
             "spent REAL DEFAULT 0", "orders INTEGER DEFAULT 0", "referrals INTEGER DEFAULT 0",
             "ref_earned REAL DEFAULT 0", "ref_by INTEGER", "last_lucky TEXT"):
    try:
        db.execute(f"ALTER TABLE users ADD COLUMN {_col}")
    except sqlite3.OperationalError:
        pass
db.execute("""CREATE TABLE IF NOT EXISTS keys (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER,
              product TEXT, label TEXT, license TEXT, price REAL, ts TEXT, resets INTEGER DEFAULT 0)""")
db.execute("""CREATE TABLE IF NOT EXISTS topups (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER,
              amount REAL, method TEXT, status TEXT, ts TEXT)""")
db.execute("CREATE TABLE IF NOT EXISTS resellers (login TEXT PRIMARY KEY, password TEXT, used_by INTEGER)")
db.commit()


def get_user(uid):
    row = db.execute("SELECT lang, balance FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        db.execute("INSERT INTO users (id, created_at) VALUES (?, ?)", (uid, now()))
        db.commit()
        return None, 0.0
    return row[0], row[1]


def touch(u):
    db.execute("UPDATE users SET name=?, created_at=COALESCE(created_at, ?) WHERE id=?",
               (u.first_name or "User", now(), u.id))
    db.commit()


def set_lang(uid, lang):
    get_user(uid)
    db.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))
    db.commit()


def change_balance(uid, delta):
    get_user(uid)
    db.execute("UPDATE users SET balance=ROUND(balance+?, 2) WHERE id=?", (delta, uid))
    db.commit()


def tier(uid):
    if is_admin(uid):
        return "ADMIN"
    row = db.execute("SELECT reseller FROM users WHERE id=?", (uid,)).fetchone()
    return "RESELLER" if row and row[0] else "USER"


def achievement(spent):
    for lim, name in ((500, "Diamond"), (250, "Platinum"), (100, "Gold"), (25, "Silver"), (5, "Bronze")):
        if spent >= lim:
            return name
    return "Newbie"


def fmt(x):
    return f"{x:g}$"


def cur_lang(uid):
    return get_user(uid)[0] or "kk"


class Touch(BaseMiddleware):
    async def __call__(self, handler, event, data):
        u = getattr(event, "from_user", None)
        if u:
            touch(u)
        return await handler(event, data)


dp.message.outer_middleware(Touch())
dp.callback_query.outer_middleware(Touch())


# ───────────── Көмекші функциялар ─────────────
def btn(text, cb, style=None, icon=None):
    d = dict(text=text, callback_data=cb)
    if style:
        d["style"] = style              # primary / success / danger
    if icon:
        d["icon_custom_emoji_id"] = EM.get(icon, icon)
    return InlineKeyboardButton(**d)


def back_kb(cb="back", text="🔙 Back"):
    return InlineKeyboardMarkup(inline_keyboard=[[btn(text, cb, "danger", "back")]])


async def safe_edit(msg, text, kb=None):
    try:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except TelegramBadRequest:
        pass


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


# ───────────── Баға, мерзім, формат ─────────────
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


def sort_key(v):
    k = vkey(v)
    return k[1] if k[0] == "h" else (k[1] * 24 if k[0] == "d" else 1e9)


def retail_usd(v):
    table = PRICE_BY_NORM.get(norm(v["product_name"]))
    return table.get(vkey(v)) if table else None


def unit_price(v, uid):
    """Бір кілттің бағасы (USD): admin — API өзіндік бағасы, reseller — арзандатылған, user — сату бағасы."""
    cost = float(v["price"])
    if is_admin(uid):
        return cost
    retail = retail_usd(v)
    if retail is None:
        return None
    if tier(uid) == "RESELLER" and retail > cost:
        return round(cost + (retail - cost) * RESELLER_SHARE, 2)
    return retail


def list_price(v, uid):
    return retail_usd(v) if is_admin(uid) else unit_price(v, uid)


def out_of_stock(v):
    return (not v.get("unlimited")) and (v.get("in_stock") or 0) <= 0


def max_qty(v):
    m = 1 if (v.get("requires_android_id") or v.get("is_balamod")) else 3
    if not v.get("unlimited"):
        m = min(m, int(v.get("in_stock") or 0))
    return max(m, 0)


def ru_plural(n, one, few, many):
    n = int(n)
    if 11 <= n % 100 <= 14:
        return many
    if n % 10 == 1:
        return one
    if 2 <= n % 10 <= 4:
        return few
    return many


def label(v, lang):
    k = vkey(v)
    if k[0] == "h":
        n = f"{k[1]:g}"
        if lang == "kk":
            return f"{n} сағат"
        if lang == "ru":
            return f"{n} {ru_plural(k[1], 'час', 'часа', 'часов')}"
        return f"{n} {'Hour' if k[1] == 1 else 'Hours'}"
    if k[0] == "d":
        n = f"{k[1]:g}"
        if lang == "kk":
            return f"{n} күн"
        if lang == "ru":
            return f"{n} {ru_plural(k[1], 'день', 'дня', 'дней')}"
        return f"{n} {'Day' if k[1] == 1 else 'Days'}"
    return str(v.get("variant_name", ""))


def money(usd, lang):
    if lang == "kk":
        return f"{round(usd * USD_KZT):,} ₸".replace(",", " ")
    if lang == "ru":
        return f"{round(usd * USD_RUB):,} ₽".replace(",", " ")
    return f"{usd:.2f} USD"


# ───────────── Тіл таңдау және басты мәзір ─────────────
def lang_screen():
    text = f'{e("lang_hdr", "🌍")} <b>Тіл / Язык / Language</b>'
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        btn("Қазақша", "setlang:kk", "success", "kz"),
        btn("Русский", "setlang:ru", "primary", "ru"),
        btn("English", "setlang:en", "danger", "en"),
    ]])
    return text, kb


def welcome_text(name, lang, balance):
    t = T[lang]
    d = e("dash", "➖")
    return (
        f'{e("store", "🏪")} <b>XERZZ SHOP</b> {e("store", "🏪")}\n\n'
        f'{e("hi", "👋")} <i>{t["welcome"]}</i>, {html.escape(name)} {e("excl", "❕")}\n\n'
        f'{e("up", "🔝")} <b>{t["highlights"]}</b> {e("up", "🔝")}\n\n'
        f'{d}{e("red", "🔴")} <b>{t["l1"]}</b>\n'
        f'{d} {e("ok1", "✅")} <b>{t["l2"]}</b>\n'
        f'{d}{e("smile", "😄")} <b>{t["l3"]}</b>\n'
        f'{d}{e("money", "💰")} <b>{t["l4"]}</b>\n'
        f'{d}{e("ok2", "✅")} <b>{t["l5"]}</b>\n\n\n'
        f'{e("wallet", "💰")} <b>{t["wallet"]}: {fmt(balance)}</b>\n\n'
        f'{e("fire", "🔥")} <i>{t["tap"]}</i> {e("bang", "❗️")}'
    )


def main_kb(uid, lang):
    t = T[lang]
    WEBAPP_URL = os.getenv("WEBAPP_URL", "")
    rows = []
    # 🚀 Mini App кнопкасы — ең жоғарыда
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton(
            text="🚀 Ашу / Открыть / Open",
            web_app=WebAppInfo(url=WEBAPP_URL))])
    rows += [
        [btn(t["shop"], "products", "success", "shop")],
        [btn(t["add"], "add", "success", "add"), btn(t["profile"], "profile", "primary", "profile")],
        [btn(t["reseller"], "reseller", "primary", "reseller")],
        [btn(t["lang"], "lang", "primary", "language"), btn(t["lucky"], "lucky", "danger", "lucky")],
        [btn(t["share"], "share", "primary", "share"), btn(t["support"], "support", "primary", "support")],
        [btn(t["top"], "top", "danger", "top")],
    ]
    if is_admin(uid):
        rows.append([btn(t["admin"], "admin", "danger", "admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_main(c_or_m, uid, name, edit=False):
    lang, bal = get_user(uid)
    lang = lang or "kk"
    text, kb = welcome_text(name, lang, bal), main_kb(uid, lang)
    if edit:
        await safe_edit(c_or_m, text, kb)
    else:
        await c_or_m.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.message(CommandStart())
async def start(m: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    existed = db.execute("SELECT 1 FROM users WHERE id=?", (uid,)).fetchone()
    lang, _ = get_user(uid)
    # реферал: тек жаңа қолданушы үшін
    if not existed and command.args and command.args.startswith("ref_"):
        try:
            ref = int(command.args[4:])
        except ValueError:
            ref = None
        if ref and ref != uid and db.execute("SELECT 1 FROM users WHERE id=?", (ref,)).fetchone():
            db.execute("UPDATE users SET ref_by=? WHERE id=?", (ref, uid))
            db.execute("UPDATE users SET referrals=referrals+1, ref_earned=ROUND(ref_earned+?,2), "
                       "balance=ROUND(balance+?,2) WHERE id=?", (REF_BONUS, REF_BONUS, ref))
            db.commit()
            try:
                await bot.send_message(ref, f"👥 New referral! +{REF_BONUS}$")
            except Exception:
                pass
    if lang is None:
        text, kb = lang_screen()
        return await m.answer(text, parse_mode="HTML", reply_markup=kb)
    await show_main(m, uid, m.from_user.first_name)


@dp.callback_query(F.data == "lang")
async def open_lang(c: CallbackQuery):
    text, kb = lang_screen()
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data.startswith("setlang:"))
async def set_language(c: CallbackQuery):
    set_lang(c.from_user.id, c.data.split(":")[1])
    await show_main(c.message, c.from_user.id, c.from_user.first_name, edit=True)
    await c.answer()


@dp.callback_query(F.data == "back")
async def back(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main(c.message, c.from_user.id, c.from_user.first_name, edit=True)
    await c.answer()


# ═════════════════════ ADD BALANCE ═════════════════════
class Topup(StatesGroup):
    receipt = State()


KEYPAD, PENDING_AMT = {}, {}


def topup_text(uid):
    _, bal = get_user(uid)
    return (f'{e("money2", "💰")} <b>Current balance :</b> {fmt(bal)}\n\n'
            f'Pick a quick amount below , or enter a custom amount.\n'
            f'<b>Min : 1 USD • Max : 100 USD</b>')


def topup_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("1 USD", "amt:1", "primary"), btn("5 USD", "amt:5", "primary")],
        [btn("10 USD", "amt:10", "primary"), btn("100 USD", "amt:100", "primary")],
        [btn("Custom Amount", "custom", "success")],
        [btn("🔙 Back", "back", "danger", "back")],
    ])


@dp.callback_query(F.data == "add")
async def add_balance(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(c.message, topup_text(c.from_user.id), topup_kb())
    await c.answer()


def keypad_view(uid):
    cur = KEYPAD.get(uid, "")
    text = topup_text(uid) + f"\n\n<b>Amount : {cur or 0} USD</b>"
    rows = [[btn(str(n), f"k:{n}", "primary") for n in (1, 2, 3)],
            [btn(str(n), f"k:{n}", "primary") for n in (4, 5, 6)],
            [btn(str(n), f"k:{n}", "primary") for n in (7, 8, 9)],
            [btn("C", "k:C", "danger"), btn("0", "k:0", "primary"), btn("⌫", "k:X", "danger")],
            [btn("Confirm", "k:ok", "success", "confirm")],
            [btn("🔙 Back", "add", "danger", "back")]]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data == "custom")
async def custom_amount(c: CallbackQuery):
    KEYPAD[c.from_user.id] = ""
    text, kb = keypad_view(c.from_user.id)
    await safe_edit(c.message, text, kb)
    await c.answer()


async def show_methods(c: CallbackQuery):
    amt = PENDING_AMT[c.from_user.id]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [btn("Binance", "pay:binance", "primary", "binance")],
        [btn("Kaspi KZ", "pay:kaspi", "success", "kaspi")],
        [btn("🔙 Back", "add", "danger", "back")],
    ])
    await safe_edit(c.message, f'{e("money2", "💰")} <b>Amount :</b> {amt} USD\n\n<b>Select payment method:</b>', kb)
    await c.answer()


@dp.callback_query(F.data.startswith("amt:"))
async def quick_amount(c: CallbackQuery):
    PENDING_AMT[c.from_user.id] = int(c.data[4:])
    await show_methods(c)


@dp.callback_query(F.data.startswith("k:"))
async def keypress(c: CallbackQuery):
    uid, k = c.from_user.id, c.data[2:]
    cur = KEYPAD.get(uid, "")
    if k == "C":
        cur = ""
    elif k == "X":
        cur = cur[:-1]
    elif k == "ok":
        if not cur or not (1 <= int(cur) <= 100):
            return await c.answer("Min : 1 USD • Max : 100 USD", show_alert=True)
        PENDING_AMT[uid] = int(cur)
        KEYPAD.pop(uid, None)
        return await show_methods(c)
    else:
        new = (cur + k).lstrip("0")
        if new == "":
            return await c.answer()
        if int(new) > 100:
            return await c.answer("Max : 100 USD", show_alert=True)
        cur = new
    KEYPAD[uid] = cur
    text, kb = keypad_view(uid)
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data.startswith("pay:"))
async def pay(c: CallbackQuery, state: FSMContext):
    uid, method = c.from_user.id, c.data[4:]
    amt = PENDING_AMT.get(uid)
    if not amt:
        return await add_balance(c, state)
    cur = db.execute("INSERT INTO topups (uid, amount, method, status, ts) VALUES (?,?,?,?,?)",
                     (uid, amt, method, "pending", now()))
    db.commit()
    oid = cur.lastrowid
    if method == "binance":
        text = (f'{e("binance", "😀")} <b>Binance</b>\n\n'
                f'<b>Amount :</b> {amt} USD\n'
                f'<b>Binance ID :</b> <code>{BINANCE_ID}</code>\n'
                f'<b>Order :</b> <code>#{oid}</code>\n\n'
                f'Write the order number in the payment note, then send the receipt screenshot here.')
    else:
        kzt = round(amt * USD_KZT)
        text = (f'{e("kaspi", "💳")} <b>Kaspi KZ</b>\n\n'
                f'<b>Amount :</b> {kzt:,} ₸ ({amt} USD)\n'.replace(",", " ") +
                f'{e("tel", "📞")} <code>{KASPI_PHONE}</code>\n'
                f'{e("users", "👥")} {KASPI_NAME}\n'
                f'<b>Order :</b> <code>#{oid}</code>\n\n'
                f'After payment send the receipt (photo or file) here. '
                f'The admin will confirm it and add your balance.')
    await state.set_state(Topup.receipt)
    await state.update_data(order_id=oid)
    await safe_edit(c.message, text, back_kb())
    await c.answer()


@dp.message(Topup.receipt)
async def receipt(m: Message, state: FSMContext):
    if not (m.photo or m.document):
        return await m.answer("Please send the receipt as a photo or file.")
    oid = (await state.get_data()).get("order_id")
    row = db.execute("SELECT amount, method FROM topups WHERE id=?", (oid,)).fetchone()
    await state.clear()
    if not row:
        return await m.answer("❌ Order not found. Start again from Add balance.")
    caption = (f"💰 <b>Top-up #{oid}</b>\n👤 {html.escape(m.from_user.full_name)} "
               f"(<code>{m.from_user.id}</code>)\nMethod: {row[1]}\nAmount: {row[0]:g} USD")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        btn("Approve", f"tp:ok:{oid}", "success"), btn("Reject", f"tp:no:{oid}", "danger")]])
    await bot.copy_message(ADMIN_ID, m.chat.id, m.message_id, caption=caption,
                           parse_mode="HTML", reply_markup=kb)
    await m.answer("✅ Receipt sent. The admin will confirm it soon.")


@dp.callback_query(F.data.startswith("tp:"))
async def topup_decide(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer()
    _, act, oid = c.data.split(":")
    row = db.execute("SELECT uid, amount, status FROM topups WHERE id=?", (int(oid),)).fetchone()
    if not row or row[2] != "pending":
        return await c.answer("Already processed", show_alert=True)
    uid, amount = row[0], row[1]
    if act == "ok":
        db.execute("UPDATE topups SET status='paid' WHERE id=?", (int(oid),))
        db.commit()
        change_balance(uid, amount)
        note, user_msg = "✅ APPROVED", f"✅ Top-up #{oid} confirmed: +{amount:g}$"
    else:
        db.execute("UPDATE topups SET status='rejected' WHERE id=?", (int(oid),))
        db.commit()
        note, user_msg = "❌ REJECTED", f"❌ Top-up #{oid} was rejected. Contact support: {SUPPORT}"
    try:
        await bot.send_message(uid, user_msg)
    except Exception:
        pass
    try:
        await c.message.edit_caption(caption=(c.message.caption or "") + f"\n\n{note}", reply_markup=None)
    except TelegramBadRequest:
        pass
    await c.answer(note)


# ═════════════════════ PROFILE / MY KEY / RESET ═════════════════════
@dp.callback_query(F.data == "profile")
async def profile(c: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = c.from_user.id
    get_user(uid)
    bal, spent, orders, refs, created = db.execute(
        "SELECT balance, spent, orders, referrals, created_at FROM users WHERE id=?", (uid,)).fetchone()
    text = (f'{e("profile", "👑")} <b>Your Profile</b>\n\n'
            f'•••••••••••••••••••••••••••••\n\n'
            f'{e("id", "🆔")} <b>ID :</b> <code>{uid}</code>\n'
            f'{e("type", "🤩")} <b>Type :</b> {e("users", "👥")}{tier(uid).title()}\n'
            f'{e("trophy", "🏆")} <b>Tier :</b> {achievement(spent)}\n'
            f'{e("cal", "🗓")} <b>Member Since :</b> {created or "-"}\n\n'
            f'{e("money2", "💰")} <b>Balance :</b> {fmt(bal)}\n'
            f'{e("orders", "🛍")} <b>Total Orders :</b> {orders}\n'
            f'{e("spent", "💸")} <b>Total Spent :</b> {fmt(spent)}\n'
            f'{e("star", "⭐️")} <b>Referrals :</b> {refs}\n\n'
            f'{e("key", "🔑")} Want to see your purchased keys? Tap “My key “ from the main menu')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [btn("My Key", "mykeys", "primary", "key")],
        [btn("🔙 Back", "back", "danger", "back")]])
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "mykeys")
async def mykeys(c: CallbackQuery):
    rows = db.execute("SELECT product, label, license, ts FROM keys WHERE uid=? ORDER BY id DESC LIMIT 5",
                      (c.from_user.id,)).fetchall()
    text = f'{e("key", "🔑")} <b>My Keys</b> (last 5)\n\n'
    if not rows:
        text += "No keys yet."
    for product, lbl, lic, ts in rows:
        text += f'<b>{html.escape(product)}</b> — {html.escape(lbl or "")}\n<code>{html.escape(lic)}</code>\n{ts}\n\n'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [btn("Reset", "reset", "primary", "reset")],
        [btn("🔙 Back", "profile", "danger", "back")]])
    await safe_edit(c.message, text, kb)
    await c.answer()


class Reset(StatesGroup):
    key = State()


def reset_rule(product):
    n = norm(product)
    for kw, api_name, param in RESET_RULES:
        if kw in n:
            return api_name, param


@dp.callback_query(F.data == "reset")
async def reset_start(c: CallbackQuery, state: FSMContext):
    await state.set_state(Reset.key)
    await safe_edit(c.message, f'{e("reset", "🔑")} <b>Reset</b>\n\nSend the key you want to reset.\n'
                               f'Limit : {RESET_LIMIT} resets per key.', back_kb("back"))
    await c.answer()


@dp.message(Reset.key)
async def reset_key(m: Message, state: FSMContext):
    uid, key = m.from_user.id, (m.text or "").strip()
    await state.clear()
    row = db.execute("SELECT id, product, resets, uid FROM keys WHERE license=? ORDER BY id DESC",
                     (key,)).fetchone()
    if not row or (row[3] != uid and not is_admin(uid)):
        return await m.answer("❌ This key was not found in your purchases.")
    rule = reset_rule(row[1])
    if not rule:
        return await m.answer("❌ Reset is not available for this product.")
    if row[2] >= RESET_LIMIT and not is_admin(uid):
        return await m.answer(f"❌ Reset limit reached ({RESET_LIMIT}/{RESET_LIMIT}).")
    try:
        await api.call("reset_key.php", {"api": rule[0], rule[1]: key}, "POST")
    except Exception as ex:
        return await m.answer(f"❌ {html.escape(str(ex))}")
    db.execute("UPDATE keys SET resets=resets+1 WHERE id=?", (row[0],))
    db.commit()
    left = max(0, RESET_LIMIT - row[2] - 1)
    await m.answer(f'{e("reset", "🔑")} <b>Key reset successfully.</b>\nResets left : {left}', parse_mode="HTML")


# ═════════════════════ UPGRADE TO RESELLER ═════════════════════
class ResLogin(StatesGroup):
    creds = State()


RES_FAILS = {}


@dp.callback_query(F.data == "reseller")
async def reseller_start(c: CallbackQuery, state: FSMContext):
    if tier(c.from_user.id) != "USER":
        return await c.answer("You already have reseller access.", show_alert=True)
    await state.set_state(ResLogin.creds)
    text = (f'{e("lock", "🔒")} <b>Enter the credentials provided by the administrator '
            f'in the following format.</b>\n\n{e("user1", "👤")} LOGIN\n{e("key", "🔑")} PASSWORD')
    await safe_edit(c.message, text, back_kb())
    await c.answer()


@dp.message(ResLogin.creds)
async def reseller_creds(m: Message, state: FSMContext):
    uid = m.from_user.id
    cnt, until = RES_FAILS.get(uid, (0, None))
    if until and datetime.now() < until:
        return await m.answer("⛔ Too many attempts. Try again later.")
    parts = (m.text or "").split()
    ok = False
    if len(parts) == 2:
        row = db.execute("SELECT password, used_by FROM resellers WHERE login=?", (parts[0],)).fetchone()
        ok = bool(row and row[0] == parts[1] and row[1] in (None, uid))
    try:
        await m.delete()                     # парольді чаттан өшіреміз
    except Exception:
        pass
    if not ok:
        cnt += 1
        RES_FAILS[uid] = (cnt, datetime.now() + timedelta(minutes=10) if cnt >= 5 else None)
        return await m.answer("❌ Invalid credentials.")
    RES_FAILS.pop(uid, None)
    db.execute("UPDATE resellers SET used_by=? WHERE login=?", (uid, parts[0]))
    db.execute("UPDATE users SET reseller=1 WHERE id=?", (uid,))
    db.commit()
    await state.clear()
    await m.answer("✅ Reseller access activated! Reseller prices are now applied in the shop.")
    text, kb = categories_view(uid)
    await m.answer(text, parse_mode="HTML", reply_markup=kb)


# ═════════════════════ LUCKY / SHARE / SUPPORT / TOP 5 ═════════════════════
@dp.callback_query(F.data == "lucky")
async def lucky(c: CallbackQuery):
    uid = c.from_user.id
    get_user(uid)
    row = db.execute("SELECT last_lucky FROM users WHERE id=?", (uid,)).fetchone()
    last = datetime.strptime(row[0], TS_FMT) if row and row[0] else None
    if last and datetime.now() - last < timedelta(days=LUCKY_DAYS):
        left = last + timedelta(days=LUCKY_DAYS) - datetime.now()
        return await c.answer(f"🎁 Already claimed. Come back in {left.days}d {left.seconds // 3600}h.",
                              show_alert=True)
    amount = round(random.uniform(LUCKY_MIN, LUCKY_MAX), 2)
    change_balance(uid, amount)
    db.execute("UPDATE users SET last_lucky=? WHERE id=?", (now(), uid))
    db.commit()
    await c.answer(f"🎁 You won {amount:.2f}$!", show_alert=True)
    await show_main(c.message, uid, c.from_user.first_name, edit=True)


@dp.callback_query(F.data == "share")
async def share(c: CallbackQuery):
    uid = c.from_user.id
    get_user(uid)
    refs, earned = db.execute("SELECT referrals, ref_earned FROM users WHERE id=?", (uid,)).fetchone()
    me = await bot.me()
    text = (f'{e("share", "➡️")} <b>Share & Earn</b>\n\n'
            f'Invite friends with your link and get {REF_BONUS}$ for every new user.\n\n'
            f'🔗 <code>https://t.me/{me.username}?start=ref_{uid}</code>\n\n'
            f'{e("money2", "💰")} : {fmt(earned)}\n{e("users", "👥")} : {refs}')
    await safe_edit(c.message, text, back_kb())
    await c.answer()


@dp.callback_query(F.data == "support")
async def support(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open chat", url=f"https://t.me/{SUPPORT.lstrip('@')}")],
        [btn("🔙 Back", "back", "danger", "back")]])
    await safe_edit(c.message, f'{e("admin", "👑")} : {SUPPORT}', kb)
    await c.answer()


@dp.callback_query(F.data == "top")
async def top5(c: CallbackQuery):
    month = datetime.now().strftime("%Y-%m")
    rows = db.execute("SELECT uid, COUNT(*) n FROM keys WHERE substr(ts,1,7)=? "
                      "GROUP BY uid ORDER BY n DESC LIMIT 5", (month,)).fetchall()
    text = f'{e("top", "👑")} <b>Top 5 Sellers Monthly</b>\n\n'
    if not rows:
        text += "No sales yet this month."
    for i, (uid, n) in enumerate(rows, 1):
        u = db.execute("SELECT name, balance FROM users WHERE id=?", (uid,)).fetchone()
        name = html.escape((u[0] if u else None) or f"User {uid}")
        text += (f'<b>{i}.</b> {e("users", "👥")} <b>Name :</b> {name}\n'
                 f'{e("users", "👥")} <b>Type :</b> {tier(uid).title()}\n'
                 f'{e("key", "🔑")} : {n}\n'
                 f'{e("money2", "💰")} : {fmt(u[1] if u else 0)}\n\n')
    await safe_edit(c.message, text, back_kb())
    await c.answer()


# ═════════════════════ ADMIN ACCOUNT ═════════════════════
class AdminAct(StatesGroup):
    add = State()
    sub = State()
    res = State()
    bc = State()


@dp.callback_query(F.data == "admin")
async def admin_panel(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer()
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [btn("Add balance", "adm:add", "success", "money2"), btn("Subtract", "adm:sub", "danger", "minus")],
        [btn("Reseller Account", "adm:res", "primary", "user1")],
        [btn("Statistics", "adm:stats", "primary", "chart"), btn("Broadcast", "adm:bc", "primary", "mega")],
        [btn("Reset", "reset", "success", "reset")],
        [btn("🔙 Back", "back", "danger", "back")],
    ])
    await safe_edit(c.message, f'{e("admin", "👑")} <b>Admin Account</b>', kb)
    await c.answer()


ADMIN_PROMPTS = {
    "add": (f'{e("money2", "💰")} <b>Add balance</b>\n\nSend: <code>USER_ID AMOUNT</code>\nExample: <code>123456789 5</code>', AdminAct.add),
    "sub": (f'{e("minus", "➖")} <b>Subtract balance</b>\n\nSend: <code>USER_ID AMOUNT</code>', AdminAct.sub),
    "res": (f'{e("user1", "👤")} <b>Reseller Account</b>\n\nSend: <code>LOGIN 1234</code>\n(login + 4-digit password)', AdminAct.res),
    "bc": (f'{e("mega", "🔊")} <b>Broadcast</b>\n\nSend the message (text, photo...) to deliver to all users.', AdminAct.bc),
}


@dp.callback_query(F.data.startswith("adm:"))
async def admin_action(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer()
    act = c.data[4:]
    if act == "stats":
        users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        resellers = db.execute("SELECT COUNT(*) FROM users WHERE reseller=1").fetchone()[0]
        kn, revenue = db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM keys").fetchone()
        bal_sum = db.execute("SELECT COALESCE(SUM(balance),0) FROM users").fetchone()[0]
        paid_sum, paid_n = db.execute("SELECT COALESCE(SUM(amount),0), COUNT(*) FROM topups WHERE status='paid'").fetchone()
        text = (f'{e("chart", "📈")} <b>Statistics</b>\n\n'
                f'{e("users", "👥")} Users : <b>{users}</b> (resellers : {resellers})\n'
                f'{e("key", "🔑")} Keys sold : <b>{kn}</b>\n'
                f'{e("spent", "💸")} Balance spent : <b>{revenue:.2f}$</b>\n'
                f'{e("money2", "💰")} Balances now : <b>{bal_sum:.2f}$</b>\n'
                f'{e("orders", "🛍")} Top-ups : <b>{paid_n}</b> ({paid_sum:.2f}$)')
        try:
            data = await api.get_balance()
            text += f'\n\nDRIP API:\n<pre>{html.escape(json.dumps(data, indent=2, ensure_ascii=False))}</pre>'
        except Exception:
            pass
        await safe_edit(c.message, text, back_kb("admin"))
        return await c.answer()
    prompt, st = ADMIN_PROMPTS[act]
    await state.set_state(st)
    await safe_edit(c.message, prompt, back_kb("admin"))
    await c.answer()


@dp.message(AdminAct.add)
@dp.message(AdminAct.sub)
async def admin_balance(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    sign = 1 if await state.get_state() == AdminAct.add.state else -1
    try:
        uid, amount = m.text.split()
        uid, amount = int(uid), float(amount)
        if db.execute("SELECT 1 FROM users WHERE id=?", (uid,)).fetchone() is None:
            return await m.answer("❌ User not found.")
        if sign < 0 and get_user(uid)[1] < amount:
            return await m.answer("❌ Not enough balance on that account.")
    except Exception:
        return await m.answer("Format: USER_ID AMOUNT")
    change_balance(uid, sign * amount)
    await state.clear()
    await m.answer(f"✅ {uid}: {fmt(get_user(uid)[1])}")
    try:
        await bot.send_message(uid, f"{'💰 +' if sign > 0 else '➖ -'}{amount:g}$ — balance: {fmt(get_user(uid)[1])}")
    except Exception:
        pass


@dp.message(AdminAct.res)
async def admin_reseller(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    parts = (m.text or "").split()
    if len(parts) != 2 or not re.fullmatch(r"[A-Za-z0-9_]{3,20}", parts[0]) or not re.fullmatch(r"\d{4}", parts[1]):
        return await m.answer("Format: LOGIN 1234 (login 3-20 chars, password 4 digits)")
    try:
        db.execute("INSERT INTO resellers (login, password) VALUES (?, ?)", parts)
        db.commit()
    except sqlite3.IntegrityError:
        return await m.answer("❌ This login already exists.")
    await state.clear()
    await m.answer(f"✅ Reseller account created.\n\n👤 LOGIN: <code>{parts[0]}</code>\n🔑 PASSWORD: <code>{parts[1]}</code>",
                   parse_mode="HTML")


@dp.message(AdminAct.bc)
async def admin_broadcast(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    ok = fail = 0
    for (uid,) in db.execute("SELECT id FROM users").fetchall():
        try:
            await bot.copy_message(uid, m.chat.id, m.message_id)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await m.answer(f"🔊 Done: {ok} delivered, {fail} failed.")


@dp.message(Command("addbalance"))
async def addbalance(m: Message):
    if not is_admin(m.from_user.id):
        return
    try:
        _, uid, amount = m.text.split()
        change_balance(int(uid), float(amount))
    except Exception:
        return await m.answer("Қолданылуы: /addbalance USER_ID СОМА")
    await m.answer(f"✅ {uid} балансы: {fmt(get_user(int(uid))[1])}")


# ═════════════════════ ДҮКЕН ═════════════════════
CATS = {
    "NONROOT": ("NON ROOT", "c_nonroot", "success"),
    "ROOT": ("ROOT", "c_root", "danger"),
    "PC": ("PC / COMPUTER", "c_pc", "primary"),
    "IOS": ("IOS / IPHONE", "c_ios", "primary"),
    "OTHER": ("OTHER", "c_other", "success"),
}


def items_for(cat, variants, show_extra=False):
    items = []
    for c, name, emoji, aliases in CATALOG:
        if c == cat:
            items.append(dict(name=name, emoji=emoji, keys={norm(a) for a in (aliases or [name])}))
    if cat == "OTHER" and show_extra:
        known = {norm(a) for _, n, _, al in CATALOG for a in (al or [n])}
        extra = {}
        for v in variants:
            if norm(v["product_name"]) not in known:
                extra.setdefault(v["product_id"], v["product_name"])
        for pid in sorted(extra):
            items.append(dict(name=extra[pid], emoji=None, keys={norm(extra[pid])}))
    return items


def categories_view(uid):
    t = T[cur_lang(uid)]

    def cb(key):
        title, icon, style = CATS[key]
        return btn(title, f"cat:{key}", style, icon)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [cb("NONROOT")], [cb("ROOT")], [cb("PC"), cb("IOS"), cb("OTHER")],
        [btn("🔙 " + t["back"], "back", "danger", "back")],
    ])
    text = (f'{e("cart", "🛒")} <b>PRODUCT STORE - SHOP</b> {e("cart", "🛒")}\n\n'
            f'{e("phone", "📱")} <b>Select your category:</b>')
    return text, kb


@dp.callback_query(F.data == "products")
async def categories(c: CallbackQuery, state: FSMContext):
    await state.clear()
    text, kb = categories_view(c.from_user.id)
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data.startswith("cat:"))
async def category(c: CallbackQuery):
    t = T[cur_lang(c.from_user.id)]
    cat = c.data.split(":")[1]
    variants = await api.get_products()
    items = items_for(cat, variants, is_admin(c.from_user.id))
    rows = [[btn(it["name"], f"i:{cat}:{n}", "primary", it["emoji"])] for n, it in enumerate(items)]
    rows.append([btn("🔙 " + t["back"], "products", "danger", "back")])
    text = (f'{e("store2", "🏪")} <b>PRODUCT STORE - SHOP</b> {e("store2", "🏪")}\n\n'
            f'{e("fire2", "🔥")} Choose a product:')
    await safe_edit(c.message, text, InlineKeyboardMarkup(inline_keyboard=rows))
    await c.answer()


@dp.callback_query(F.data.startswith("i:"))
async def item_page(c: CallbackQuery):
    uid = c.from_user.id
    lang = cur_lang(uid)
    t = T[lang]
    _, cat, idx = c.data.split(":")
    variants = await api.get_products()
    items = items_for(cat, variants, is_admin(uid))
    if int(idx) >= len(items):
        return await c.answer("❌", show_alert=True)
    it = items[int(idx)]
    vs = [v for v in variants if norm(v["product_name"]) in it["keys"]]
    vs = [v for v in vs if retail_usd(v) is not None or is_admin(uid)]
    if not vs:
        return await c.answer(t["unavailable"], show_alert=True)
    vs.sort(key=sort_key)
    rows = []
    for v in vs:
        usd = list_price(v, uid)
        if usd is None:
            text = f"⚠ {v['variant_name']} — {v['price']} {v['currency']} (API)"
        else:
            text = f"{label(v, lang)} — {money(usd, lang)}"
        if out_of_stock(v):
            text = "❌ " + text
        rows.append([btn(text, f"v:{v['variant_id']}", "success")])
    rows.append([btn("🔙 " + t["back"], f"cat:{cat}", "danger", "back")])
    title = e(it["emoji"], "👻") if it["emoji"] else "📦"
    text = (f'{title} <b>{html.escape(it["name"])}</b>\n\n'
            f'{e("tier", "👑")} <b>Your Account Tier :</b> {tier(uid)}')
    await safe_edit(c.message, text, InlineKeyboardMarkup(inline_keyboard=rows))
    await c.answer()


class Buy(StatesGroup):
    android_id = State()


async def find_variant(vid):
    for v in await api.get_products():
        if v["variant_id"] == vid:
            return v


def confirm_view(v, uid, qty):
    lang = cur_lang(uid)
    t = T[lang]
    mq = max_qty(v)
    qty = max(1, min(qty, mq))
    unit = unit_price(v, uid)
    total = round(unit * qty, 2)
    text = (f"<b>{html.escape(v['product_name'])}</b> — {html.escape(label(v, lang))}\n"
            f"{money(unit, lang)} × {qty} = <b>{money(total, lang)}</b> ({total:g}$)\n\n{t['confirm']}")
    rows = []
    if mq > 1:
        rows.append([btn(("✅ " if q == qty else "") + str(q), f"q:{v['variant_id']}:{q}", "primary")
                     for q in range(1, mq + 1)])
    rows.append([btn(t["gen"], f"g:{v['variant_id']}:{qty}", "success"),
                 btn(t["cancel"], "products", "danger")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data.startswith("v:"))
@dp.callback_query(F.data.startswith("q:"))
async def variant(c: CallbackQuery):
    uid = c.from_user.id
    t = T[cur_lang(uid)]
    parts = c.data.split(":")
    v = await find_variant(int(parts[1]))
    qty = int(parts[2]) if parts[0] == "q" else 1
    if not v:
        return await c.answer("❌", show_alert=True)
    if unit_price(v, uid) is None:
        return await c.answer(t["unavailable"], show_alert=True)
    if out_of_stock(v):
        return await c.answer(t["oos"], show_alert=True)
    text, kb = confirm_view(v, uid, qty)
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data.startswith("g:"))
async def generate(c: CallbackQuery, state: FSMContext):
    uid = c.from_user.id
    t = T[cur_lang(uid)]
    _, vid, qty = c.data.split(":")
    v = await find_variant(int(vid))
    if not v:
        return await c.answer("❌", show_alert=True)
    unit = unit_price(v, uid)
    if unit is None:
        return await c.answer(t["unavailable"], show_alert=True)
    if out_of_stock(v):
        return await c.answer(t["oos"], show_alert=True)
    qty = max(1, min(int(qty), max_qty(v)))
    if get_user(uid)[1] < round(unit * qty, 2):
        return await c.answer(t["nofunds"], show_alert=True)
    if v.get("requires_android_id"):
        await state.update_data(variant_id=int(vid), qty=1)
        await state.set_state(Buy.android_id)
        await c.message.answer(t["android"])
        return await c.answer()
    await do_generate(c.message, c.from_user, int(vid), qty)
    await c.answer()


@dp.message(Buy.android_id)
async def got_android(m: Message, state: FSMContext):
    t = T[cur_lang(m.from_user.id)]
    aid = (m.text or "").strip()
    if not re.match(r"^[A-Za-z0-9:_\-\.]{6,64}$", aid):
        return await m.answer(t["android_bad"])
    data = await state.get_data()
    await state.clear()
    await do_generate(m, m.from_user, data["variant_id"], data.get("qty", 1), android_id=aid)


def strip_balance(x):
    if isinstance(x, dict):
        return {k: strip_balance(v) for k, v in x.items() if "balance" not in k.lower()}
    if isinstance(x, list):
        return [strip_balance(i) for i in x]
    return x


KEY_FIELDS = {"key", "keys", "license", "license_key", "licence", "licence_key", "serial", "username"}


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


async def do_generate(msg: Message, user, vid, qty, android_id=None):
    uid = user.id
    lang = cur_lang(uid)
    t = T[lang]
    v = await find_variant(vid)
    if not v:
        return await msg.answer("❌")
    unit = unit_price(v, uid)
    if unit is None:
        return await msg.answer(t["unavailable"])
    qty = max(1, min(qty, max_qty(v)))
    total = round(unit * qty, 2)
    if get_user(uid)[1] < total:
        return await msg.answer(t["nofunds"])
    change_balance(uid, -total)             # алдымен шегереміз
    try:
        data = await api.generate(vid, qty, android_id=android_id)
    except Exception as ex:
        change_balance(uid, total)          # қате болса, қайтарамыз
        return await msg.answer(f"❌ {html.escape(str(ex))}")
    keys = extract_keys(data)
    lbl = label(v, lang)
    db.execute("UPDATE users SET spent=ROUND(spent+?,2), orders=orders+1 WHERE id=?", (total, uid))
    for k in keys:
        db.execute("INSERT INTO keys (uid, product, label, license, price, ts) VALUES (?,?,?,?,?,?)",
                   (uid, v["product_name"], lbl, k, unit, now()))
    db.commit()
    left = get_user(uid)[1]
    emoji = EMOJI_BY_NORM.get(norm(v["product_name"]))
    title = e(emoji, "👻") if emoji else "📦"
    lines = [f'{title} <b>{html.escape(v["product_name"])}</b> — {html.escape(lbl)}', ""]
    if keys:
        lines += [f'{e("key", "🔑")}: <code>{html.escape(k)}</code>' for k in keys]
    else:
        raw = json.dumps(strip_balance(data), indent=2, ensure_ascii=False)
        lines.append(f"<pre>{html.escape(raw)}</pre>")
    lines += [f'{e("users", "👥")}: {tier(uid).title()}', "",
              f'{e("money2", "💰")}: -{total:g}$', f'{e("money2", "💰")}: {left:g}$']
    await msg.answer("\n".join(lines), parse_mode="HTML")
    asyncio.create_task(send_review(v["product_name"], label(v, "en"), user.first_name or "User"))


# ───────────── Автоматты review (кілті жабық сурет) ─────────────
def _font(size):
    for p in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def make_review_image(product, lbl, name):
    W, H = 900, 500
    img = Image.new("RGB", (W, H), (18, 20, 32))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, W - 20, H - 20], outline=(90, 110, 255), width=4)
    d.text((50, 50), "XERZZ SHOP  -  REVIEW", font=_font(40), fill=(120, 150, 255))
    size = 48 if len(product) <= 20 else 36 if len(product) <= 30 else 28
    d.text((50, 140), product, font=_font(size), fill=(255, 255, 255))
    d.text((50, 215), f"Plan: {lbl}", font=_font(36), fill=(200, 200, 210))
    d.text((50, 290), "Key: " + "*" * 16, font=_font(40), fill=(255, 200, 60))
    masked = (name[:1] or "U") + "***"
    d.text((50, 370), f"Buyer: {masked}", font=_font(32), fill=(200, 200, 210))
    d.text((50, 420), "Delivered instantly  -  5/5", font=_font(30), fill=(90, 220, 120))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


async def send_review(product, lbl, name):
    ch = os.getenv("REVIEW_CHANNEL_ID")
    if not ch or Image is None:
        return
    try:
        png = make_review_image(product, lbl, name)
        await bot.send_photo(int(ch), BufferedInputFile(png, "review.png"),
                             caption=f"✅ {product} — {lbl}")
    except Exception as ex:
        print("review error:", ex)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())