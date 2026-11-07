import re

# ───────────── Валюта бағамы (қолмен жаңартып тұр) ─────────────
USD_KZT = 470    # 1 USD = ? тенге
USD_RUB = 80.5   # 1 USD = ? рубль


def _n(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


# ───────────── Өнімдер тізімі ─────────────
# (санат, көрінетін аты, premium emoji ID, API-дағы атаулар (қаласаң))
# aliases болмаса, API-дағы product_name осы көрінетін атпен бірдей деп іздейді
CATALOG = [
    # ───── NON ROOT ─────
    ("NONROOT", "DRIP APKMOD", "5789935155632151161", None),
    ("NONROOT", "DRIP WIRE ANDROID + IOS", "5789935155632151161", None),
    ("NONROOT", "Phantom Android + IOS", "6249149038831084817",
     ["Phantom Android + IOS", "Phanthom Android + IOS"]),
    ("NONROOT", "BALAMOD ANDROID", "6314573644290859187", None),
    ("NONROOT", "GBOX ESGIN CERTIFICATE", "6055365955591085075", None),
    ("NONROOT", "XREG ANDROID+ IOS", "6084549047186628949", None),
    ("NONROOT", "ZREX ANDROID + IOS", "6113985756601000561", None),
    ("NONROOT", "HG CHEATS APKMOD SAFE NORMAL", "6258011527752720019", None),
    ("NONROOT", "RAPID CORE NON ROOT", "6269364646734471084",
     ["RAPID CORE NON ROOT", "RAPID CORE ROOT+ NON ROOT"]),
    ("NONROOT", "PATO ORANGE APKMOD", "6185844583847435637", None),
    ("NONROOT", "PUBG ZOLO ANDROID", "6057504754815213279", None),
    ("NONROOT", "XYZ CHEATS ANDROID", "6163201099651097962", None),
    ("NONROOT", "PRIME HOOK APKMOD", "6055345760654859808",
     ["PRIME HOOK APKMOD", "PRIME HOOK APKMKD"]),
    ("NONROOT", "HG PROXY ANDROID", "6179177403034640311", None),
    ("NONROOT", "SILENT CHEAT PROXY NON ROOT", "6107106382928944986", None),
    ("NONROOT", "PATO YELLOW APKMOD", "6057540261309849187", None),
    ("NONROOT", "AIM HACK ANDROID + IOS", "6082561130163609059", None),

    # ───── ROOT ─────
    ("ROOT", "RAPID CORE ROOT", "6273984287788245654",
     ["RAPID CORE ROOT", "RAPID CORE ROOT+ NON ROOT"]),
    ("ROOT", "SILENT CHEAT ROOT BRUTAL", "6055528159325985815", None),
    ("ROOT", "SILENT CHEAT ROOT SAFE", "6055528159325985815", None),
    ("ROOT", "SKB MOD ROOT MOBILE", "6235487843079168234", None),
    ("ROOT", "DRIP MOBILE ROOT", "5789935155632151161", None),

    # ───── PC / COMPUTER ─────
    ("PC", "BR MODS SILENTAIM PC", "6176806052806271278", None),
    ("PC", "DUSTU AIMKILL PC", "6179007906445272674", None),

    # ───── IOS / IPHONE ─────
    ("IOS", "DRIP WIRE + IOS", "6057514817923587887",
     ["DRIP WIRE + IOS", "DRIP WIRE ANDROID + IOS"]),
    ("IOS", "Phantom + IOS", "6249149038831084817",
     ["Phantom + IOS", "Phanthom + IOS", "Phantom Android + IOS", "Phanthom Android + IOS"]),
    ("IOS", "ZREX + IOS", "6160968734564426582",
     ["ZREX + IOS", "ZREX ANDROID + IOS"]),
    ("IOS", "XREG + IOS", "6084549047186628949",
     ["XREG + IOS", "XREG ANDROID+ IOS"]),
    ("IOS", "VELORA EXTERNAL IOS", "6176786515000041742", None),
    ("IOS", "Flourite 8BP IOS", "6239858857066109763",
     ["Flourite 8BP IOS", "Fluorite 8BP IOS"]),
    ("IOS", "Flourite MLBB IOS", "6239858857066109763",
     ["Flourite MLBB IOS", "Fluorite MLBB IOS"]),
    ("IOS", "Cloud CODM IOS", "6057454971849284543", None),
    ("IOS", "DELTA PROXY IOS", "6215370229149605521", None),
    ("IOS", "MIGUL- INDIA PRO VERSION", "6208270648209318297", None),
    ("IOS", "MIGUL- INDIA BASIC", "6208270648209318297", None),
    ("IOS", "MIGUL - MONITE BASIC", "6208244693721948599",
     ["MIGUL - MONITE BASIC", "MIGUL - MONTIE BASIC"]),
    ("IOS", "MIGUL - MONITE PRO", "6057680595071278635",
     ["MIGUL - MONITE PRO", "MIGUL - MONTIE PRO"]),
    ("IOS", "SOPHIA CHEAT PROXY IOS", "6057515359089467488",
     ["SOPHIA CHEAT PROXY IOS", "SOPHIYA CHEAT PROXY IOS"]),
    ("IOS", "MIGUL-Vietnam BASIC", "6055312869795309310", None),
    ("IOS", "MIGUL- Vietnam PRO", "6208287643394908534", None),
    ("IOS", "AIM HACK + IOS", "6114095024863977054",
     ["AIM HACK + IOS", "AIM HACK ANDROID + IOS"]),

    # ───── OTHER ─────
    ("OTHER", "GUILD GLORY BOT", "6176910592310256107", None),
]


# ───────────── Сату бағалары (USD) ─────────────
# hours=[(сағат, баға)], days=[(күн, баға)], text=[("API-дағы вариант аты", баға)]
def P(hours=(), days=(), text=()):
    t = {}
    for n, p in hours:
        t[("h", n)] = p
    for n, p in days:
        t[("d", n)] = p
    for k, p in text:
        t[("t", _n(k))] = p
    return t


PRICES = {
    # ───── NON ROOT ─────
    "DRIP APKMOD": P(days=[(1, 0.89), (3, 1.5), (7, 4.47), (15, 11.19), (30, 15.4)]),
    "DRIP WIRE ANDROID + IOS": P(hours=[(3, 0.45), (6, 0.78), (12, 1.56)],
                                 days=[(1, 2.68), (7, 5.59), (30, 11.19)]),
    "Phantom Android + IOS": P(hours=[(1, 0.22), (3, 0.45), (6, 0.89), (12, 1.34)],
                               days=[(1, 1.79), (3, 3.24), (7, 5.12), (30, 7.89)]),
    "BALAMOD ANDROID": P(hours=[(1, 0.34), (3, 0.56), (6, 1.01), (12, 1.57)],
                         days=[(1, 2.24), (2, 3.05), (3, 4.60), (7, 6.30)]),
    "GBOX ESGIN CERTIFICATE": P(text=[("0 Month No warranty", 3),
                                      ("1 Yers Month Warenty", 5),
                                      ("1 Year Warranty", 5)]),
    "XREG ANDROID+ IOS": P(hours=[(1, 0.60), (3, 0.89), (6, 1.01), (12, 1.50)],
                           days=[(1, 2.00), (3, 3.00)]),
    "ZREX ANDROID + IOS": P(days=[(1, 1.00), (3, 2.00), (7, 4.00)]),
    "HG CHEATS APKMOD SAFE NORMAL": P(days=[(1, 1.00), (3, 2.00), (7, 4.00), (10, 5.00), (30, 7.00)]),
    "RAPID CORE NON ROOT": P(days=[(1, 1.00), (7, 3.00), (14, 5.00), (30, 7.00)]),
    "PATO ORANGE APKMOD": P(days=[(3, 2.00), (7, 4.00)]),
    "PUBG ZOLO ANDROID": P(days=[(1, 1.50), (7, 3.00), (30, 6.00)]),
    "XYZ CHEATS ANDROID": P(hours=[(1, 0.50), (2, 0.80), (4, 1.00), (6, 1.20), (12, 1.50)],
                            days=[(1, 2.00), (3, 3.00)]),
    "PRIME HOOK APKMOD": P(days=[(1, 1.00), (3, 2.00), (7, 3.00), (10, 4.00)]),
    "HG PROXY ANDROID": P(hours=[(2, 0.20)],
                          days=[(1, 0.50), (3, 1), (7, 3), (10, 4), (15, 6), (30, 8)]),
    "SILENT CHEAT PROXY NON ROOT": P(hours=[(1, 0.20), (3, 0.40), (6, 0.60), (12, 0.80)],
                                     days=[(1, 1.00), (3, 2.00), (7, 4.00), (14, 6.00), (28, 8.00)]),
    "PATO YELLOW APKMOD": P(days=[(31, 6.00)]),
    "AIM HACK ANDROID + IOS": P(hours=[(1, 0.20), (3, 0.50), (6, 0.70), (12, 1.00)],
                                days=[(1, 1.30), (3, 2.00), (7, 4.00), (30, 6.00)]),

    # ───── ROOT ─────
    "RAPID CORE ROOT": P(days=[(1, 1.00), (7, 3.00), (14, 5.00), (30, 7.00)]),
    "SILENT CHEAT ROOT BRUTAL": P(days=[(1, 1.00), (3, 2.00), (7, 4.00), (14, 6.00), (28, 8.00)]),
    "SILENT CHEAT ROOT SAFE": P(days=[(1, 1.00), (3, 2.00), (7, 4.00), (14, 6.00), (28, 8.00)]),
    "SKB MOD ROOT MOBILE": P(days=[(1, 1.50), (3, 2.50), (7, 4.00)]),
    "DRIP MOBILE ROOT": P(days=[(1, 1.00), (7, 3.00), (30, 6.00)]),

    # ───── PC ─────
    "BR MODS SILENTAIM PC": P(days=[(1, 1.00), (10, 4.00), (30, 8.00)]),
    "DUSTU AIMKILL PC": P(days=[(1, 1.00), (7, 3.00), (15, 5.00), (30, 8.00)]),

    # ───── IOS ─────
    "VELORA EXTERNAL IOS": P(days=[(1, 1.00), (3, 2.00), (7, 4.00), (15, 6.00)]),
    "Flourite 8BP IOS": P(days=[(1, 3.00), (7, 6.00), (30, 15.00)]),
    "Flourite MLBB IOS": P(days=[(1, 3.00), (7, 6.00), (30, 15.00)]),
    "Cloud CODM IOS": P(days=[(1, 3.00), (7, 6.00), (30, 15.00)]),
    "DELTA PROXY IOS": P(days=[(1, 2.00), (7, 4.00), (30, 8.00)]),
    "MIGUL- INDIA PRO VERSION": P(days=[(1, 3.00), (7, 6.00), (30, 13.00)]),
    "MIGUL- INDIA BASIC": P(days=[(1, 3.00), (7, 6.00), (30, 13.00)]),
    "MIGUL - MONITE BASIC": P(days=[(1, 1.5), (7, 3.00), (30, 6.00)]),
    "MIGUL - MONITE PRO": P(days=[(1, 2.00), (7, 4.00), (30, 8.00)]),
    "SOPHIA CHEAT PROXY IOS": P(days=[(1, 1.00), (7, 3.00), (30, 6.00)]),
    "MIGUL-Vietnam BASIC": P(days=[(1, 1.50), (7, 3.00), (30, 5.00)]),
    "MIGUL- Vietnam PRO": P(days=[(1, 3.00), (7, 4.00), (30, 7.00)]),

    # ───── OTHER ─────
    "GUILD GLORY BOT": P(text=[("1 Basic", 2.5)]),
}

# Android + IOS өнімдері IOS санатында да сол бағамен тұр
PRICES["DRIP WIRE + IOS"] = PRICES["DRIP WIRE ANDROID + IOS"]
PRICES["Phantom + IOS"] = PRICES["Phantom Android + IOS"]
PRICES["ZREX + IOS"] = PRICES["ZREX ANDROID + IOS"]
PRICES["XREG + IOS"] = PRICES["XREG ANDROID+ IOS"]
PRICES["AIM HACK + IOS"] = PRICES["AIM HACK ANDROID + IOS"]
# Ресет үшін: (өнім атында кездесетін сөз, API-дағы "api" аты, кілт параметрі)
RESET_RULES = [
    ("BRMOD", "brmod", "username"),
    ("PHANTOM", "phantom", "username"),
    ("PHANTHOM", "phantom", "username"),
    ("DRIP", "drip", "key"),
]