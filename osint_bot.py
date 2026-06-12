#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import logging
import asyncio
from urllib.parse import quote
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ========== ТОКЕН ИЗ ПЕРЕМЕННОЙ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in environment")

# ========== API-КЛЮЧИ ВСТРОЕНЫ (как в файле) ==========
VK_ACCESS_TOKEN = "0af157510af157510af15751aa0a89e69600af10af157516a0bc15996e74fe2b440998c"
VK_API_VERSION = "5.131"

SNUSBASE_API_KEY = "sbmevohou6ecsn9fd9wcvnwwvsvwnc"
SNUSBASE_API_SECRET = "sby0b7crtq98od7efbb8zr70788n2h"

NUMVERIFY_API_KEY = "c84bb45a28c15b8c66911354c091106c"
SMSC_API_KEY = "9fcd3e6622f96a780f0908ce414bb16360d3779d8253f484f319e02cc5c25065"
OFDATA_API_KEY = "KBnpz1CHKNngFXxK"
VERIPHONE_API_KEY = "D997B34B302B4A06B3AB815312852E51"
IPGEOLOCATION_API_KEY = "73d99145d2e948779263360bfeb67ecc"
IP2LOCATION_API_KEY = "965108E0429BB3E9329066D8D015564C"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def make_request(session, url, params=None, headers=None, timeout=15):
    try:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        logger.error(f"Request error {url}: {e}")
    return None

def format_output(data, max_len=4000):
    if not data:
        return "❌ Нет данных"
    try:
        text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        if len(text) > max_len:
            text = text[:max_len-100] + "\n... (обрезано)"
        return f"<pre>{text}</pre>"
    except:
        return "❌ Ошибка форматирования"

# ----- VK -----
async def vk_get_user(user_id):
    params = {"access_token": VK_ACCESS_TOKEN, "v": VK_API_VERSION, "user_ids": user_id,
              "fields": "first_name,last_name,status,sex,country,city,bdate"}
    async with aiohttp.ClientSession() as session:
        result = await make_request(session, "https://api.vk.com/method/users.get", params=params)
        if result and "response" in result and result["response"]:
            return result["response"][0]
    return None

async def vk_lookup_looka(user_id):
    url = f"https://looka.one/vk_user/id{user_id}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    import re
                    m = re.search(r'<title>(.*?)</title>', html)
                    return m.group(1) if m else None
        except:
            return None

async def vk_lookup_murix(user_id):
    url = f"http://api.murix.ru/eye?v=1&user={user_id}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

# ----- Snusbase -----
async def snusbase_search(query, search_type="email"):
    url = "https://snusbase.com/api/search"
    auth = aiohttp.BasicAuth(SNUSBASE_API_KEY, SNUSBASE_API_SECRET)
    headers = {"Content-Type": "application/json"}
    payload = {"query": query, "type": search_type}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, auth=auth, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Snusbase error: {e}")
    return None

# ----- NumVerify -----
async def numverify_lookup(phone):
    params = {"access_key": NUMVERIFY_API_KEY, "number": phone, "format": 1}
    async with aiohttp.ClientSession() as session:
        return await make_request(session, "http://apilayer.net/api/validate", params=params)

# ----- SMSC -----
async def smsc_lookup(phone):
    params = {"login": "api", "psw": SMSC_API_KEY, "phone": phone, "fmt": 3, "op": 1}
    async with aiohttp.ClientSession() as session:
        return await make_request(session, "https://smsc.ru/sys/info.php", params=params)

# ----- VeriPhone -----
async def veriphone_check(phone):
    params = {"key": VERIPHONE_API_KEY, "phone": phone, "format": "json"}
    async with aiohttp.ClientSession() as session:
        return await make_request(session, "https://veriphone.io/api/v2/verify", params=params)

# ----- HudsonRock -----
async def hudsonrock_ip(ip):
    url = f"https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-ip?ip={ip}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

async def hudsonrock_username(username):
    url = f"https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-username?username={username}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

# ----- psbdmp -----
async def psbdmp_email(email):
    url = f"https://psbdmp.ws/api/search/email/{quote(email)}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

async def psbdmp_domain(domain):
    url = f"https://psbdmp.ws/api/search/domain/{domain}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

# ----- ProxyNova -----
async def proxynova_search(query):
    url = f"https://api.proxynova.com/comb?query={quote(query)}&start=0&limit=100"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

# ----- IP геолокация (5 сервисов) -----
async def ipgeolocation_lookup(ip):
    url = f"https://api.ipgeolocation.io/ipgeo?apiKey={IPGEOLOCATION_API_KEY}&ip={ip}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

async def ip2location_lookup(ip):
    url = f"https://api.ip2location.io/?key={IP2LOCATION_API_KEY}&ip={ip}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

async def ipleak_lookup(ip):
    url = f"https://ipleak.net/json/{ip}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

async def sypexgeo_lookup(ip):
    url = f"https://api.sypexgeo.net/json/{ip}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

async def geoplugin_lookup(ip):
    url = f"http://www.geoplugin.net/json.gp?ip={ip}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

# ----- Дополнительные -----
async def breachdb_search(query):
    url = f"https://breachdb.org/search?q={quote(query)}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

async def phonedb_lookup(phone):
    url = f"https://phonedb.global/lookup/{phone}"
    async with aiohttp.ClientSession() as session:
        return await make_request(session, url)

# ==================== КОМАНДЫ БОТА ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 **OSINT Aggregator Bot**\n\n"
        "Команды:\n"
        "/vk <id|username>\n"
        "/looka <id>\n"
        "/murix <id>\n"
        "/snusbase <email>\n"
        "/numverify <phone>\n"
        "/smsc <phone>\n"
        "/veriphone <phone>\n"
        "/ip <ip>\n"
        "/email <email>\n"
        "/domain <domain>\n"
        "/proxynova <query>\n"
        "/hudsonuser <username>\n"
        "/breach <query>\n"
        "/phone <phone>\n"
        "/all <email>"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_vk(update, context):
    if not context.args:
        await update.message.reply_text("/vk <id>")
        return
    data = await vk_get_user(context.args[0])
    await update.message.reply_text(format_output(data), parse_mode="HTML") if data else await update.message.reply_text("❌ Не найдено")

async def cmd_looka(update, context):
    if not context.args:
        await update.message.reply_text("/looka <id>")
        return
    res = await vk_lookup_looka(context.args[0])
    await update.message.reply_text(res or "❌ Нет данных")

async def cmd_murix(update, context):
    if not context.args:
        await update.message.reply_text("/murix <id>")
        return
    data = await vk_lookup_murix(context.args[0])
    await update.message.reply_text(format_output(data), parse_mode="HTML") if data else await update.message.reply_text("❌ Нет")

async def cmd_snusbase(update, context):
    if not context.args:
        await update.message.reply_text("/snusbase <email>")
        return
    data = await snusbase_search(context.args[0])
    await update.message.reply_text(format_output(data), parse_mode="HTML") if data else await update.message.reply_text("❌ Ничего")

async def cmd_numverify(update, context):
    if not context.args:
        await update.message.reply_text("/numverify <phone>")
        return
    data = await numverify_lookup(context.args[0])
    if data and data.get("valid"):
        await update.message.reply_text(format_output(data), parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Невалидный номер")

async def cmd_smsc(update, context):
    if not context.args:
        await update.message.reply_text("/smsc <phone>")
        return
    data = await smsc_lookup(context.args[0])
    await update.message.reply_text(format_output(data), parse_mode="HTML") if data else await update.message.reply_text("❌ Ошибка")

async def cmd_veriphone(update, context):
    if not context.args:
        await update.message.reply_text("/veriphone <phone>")
        return
    data = await veriphone_check(context.args[0])
    await update.message.reply_text(format_output(data), parse_mode="HTML") if data else await update.message.reply_text("❌ Ошибка")

async def cmd_ip(update, context):
    if not context.args:
        await update.message.reply_text("/ip <ip>")
        return
    ip = context.args[0]
    await update.message.reply_text("🔍 Сбор данных...")
    tasks = [
        ipgeolocation_lookup(ip), ip2location_lookup(ip), ipleak_lookup(ip),
        sypexgeo_lookup(ip), geoplugin_lookup(ip), hudsonrock_ip(ip)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = ""
    names = ["ipgeolocation", "ip2location", "ipleak", "sypexgeo", "geoplugin", "hudsonrock"]
    for name, res in zip(names, results):
        if isinstance(res, Exception) or not res:
            continue
        out += f"\n<b>{name}:</b>\n{json.dumps(res, ensure_ascii=False, indent=2)[:500]}\n"
    await update.message.reply_text(f"🌍 IP {ip}\n{out[:4000] or 'Нет данных'}", parse_mode="HTML")

async def cmd_email(update, context):
    if not context.args:
        await update.message.reply_text("/email <email>")
        return
    data = await psbdmp_email(context.args[0])
    await update.message.reply_text(format_output(data), parse_mode="HTML") if data else await update.message.reply_text("❌ Утечек нет")

async def cmd_domain(update, context):
    if not context.args:
        await update.message.reply_text("/domain <domain>")
        return
    data = await psbdmp_domain(context.args[0])
    await update.message.reply_text(format_output(data), parse_mode="HTML") if data else await update.message.reply_text("❌ Нет")

async def cmd_proxynova(update, context):
    if not context.args:
        await update.message.reply_text("/proxynova <query>")
        return
    data = await proxynova_search(" ".join(context.args))
    await update.message.reply_text(format_output(data), parse_mode="HTML") if data else await update.message.reply_text("❌ Ничего")

async def cmd_hudsonuser(update, context):
    if not context.args:
        await update.message.reply_text("/hudsonuser <username>")
        return
    data = await hudsonrock_username(context.args[0])
    await update.message.reply_text(format_output(data), parse_mode="HTML") if data else await update.message.reply_text("❌ Не найден")

async def cmd_breach(update, context):
    if not context.args:
        await update.message.reply_text("/breach <query>")
        return
    data = await breachdb_search(" ".join(context.args))
    await update.message.reply_text(format_output(data), parse_mode="HTML") if data else await update.message.reply_text("❌ Нет")

async def cmd_phone(update, context):
    if not context.args:
        await update.message.reply_text("/phone <phone>")
        return
    phone = context.args[0]
    await update.message.reply_text("📞 Проверка...")
    nv, sc, vp, pd = await asyncio.gather(
        numverify_lookup(phone), smsc_lookup(phone),
        veriphone_check(phone), phonedb_lookup(phone)
    )
    out = ""
    if nv and nv.get("valid"):
        out += f"<b>NumVerify:</b>\n{json.dumps(nv, ensure_ascii=False)[:600]}\n\n"
    if sc:
        out += f"<b>SMSC:</b>\n{json.dumps(sc, ensure_ascii=False)[:600]}\n\n"
    if vp:
        out += f"<b>VeriPhone:</b>\n{json.dumps(vp, ensure_ascii=False)[:600]}\n\n"
    if pd:
        out += f"<b>PhoneDB:</b>\n{json.dumps(pd, ensure_ascii=False)[:600]}"
    await update.message.reply_text(out[:4000] or "❌ Нет данных", parse_mode="HTML")

async def cmd_all(update, context):
    if not context.args:
        await update.message.reply_text("/all <email>")
        return
    email = context.args[0]
    await update.message.reply_text("🔍 Мультипоиск... 20-30 сек")
    sn, ps, pn, br = await asyncio.gather(
        snusbase_search(email), psbdmp_email(email),
        proxynova_search(email), breachdb_search(email)
    )
    res = {}
    if sn: res["snusbase"] = sn
    if ps: res["psbdmp"] = ps
    if pn: res["proxynova"] = pn
    if br: res["breachdb"] = br
    if not res:
        await update.message.reply_text("❌ Ничего не найдено")
    else:
        await update.message.reply_text(format_output(res), parse_mode="HTML")

# ==================== ЗАПУСК ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("vk", cmd_vk))
    app.add_handler(CommandHandler("looka", cmd_looka))
    app.add_handler(CommandHandler("murix", cmd_murix))
    app.add_handler(CommandHandler("snusbase", cmd_snusbase))
    app.add_handler(CommandHandler("numverify", cmd_numverify))
    app.add_handler(CommandHandler("smsc", cmd_smsc))
    app.add_handler(CommandHandler("veriphone", cmd_veriphone))
    app.add_handler(CommandHandler("ip", cmd_ip))
    app.add_handler(CommandHandler("email", cmd_email))
    app.add_handler(CommandHandler("domain", cmd_domain))
    app.add_handler(CommandHandler("proxynova", cmd_proxynova))
    app.add_handler(CommandHandler("hudsonuser", cmd_hudsonuser))
    app.add_handler(CommandHandler("breach", cmd_breach))
    app.add_handler(CommandHandler("phone", cmd_phone))
    app.add_handler(CommandHandler("all", cmd_all))

    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")
    if WEBHOOK_URL:
        app.run_webhook(listen="0.0.0.0", port=PORT, url_path=BOT_TOKEN,
                        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    else:
        logger.info("Polling mode")
        app.run_polling()

if __name__ == "__main__":
    main()
