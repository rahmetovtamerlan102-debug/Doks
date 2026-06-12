import asyncio
import aiohttp
import json
import logging
import os
import re
from flask import Flask, jsonify
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==================== Flask app for health check ====================
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return jsonify({"status": "ok", "message": "OSINT bot is running"}), 200

# ==================== CONFIG ====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN", "0af157510af157510af15751aa0a89e69600af10af157516a0bc15996e74fe2b440998c")
NUMVERIFY_KEY = os.getenv("NUMVERIFY_KEY", "c84bb45a28c15b8c66911354c091106c")
VERIPHONE_KEY = os.getenv("VERIPHONE_KEY", "D997B34B302B4A06B3AB815312852E51")
OFDATA_KEY = os.getenv("OFDATA_KEY", "KBnpz1CHKNngFXxK")
IPGEOLOCATION_KEY = os.getenv("IPGEOLOCATION_KEY", "73d99145d2e948779263360bfeb67ecc")
IP2LOCATION_KEY = os.getenv("IP2LOCATION_KEY", "965108E0429BB3E9329066D8D015564C")
SMSC_API_KEY1 = os.getenv("SMSC_API_KEY1", "9fcd3e6622f96a780f0908ce414bb16360d3779d8253f484f319e02cc5c25065")
SMSC_API_KEY2 = os.getenv("SMSC_API_KEY2", "dbbc251dda62fb51321132d79b070d00cad48acec4c660f7f0b313eb09056e9b")
SMSC_API_KEY3 = os.getenv("SMSC_API_KEY3", "58878ed65228db88eddfda4983bce5d19d425ddf81472857b3f59f11aec34f127862a1cc7d4581")

API_TIMEOUT = 15
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== Helper functions ====================
async def fetch_json(session, url, params=None, headers=None, method='GET'):
    try:
        async with session.request(method, url, params=params, headers=headers, timeout=API_TIMEOUT) as resp:
            if resp.status == 200:
                return await resp.json(content_type=None)
            return {"error": f"HTTP {resp.status}"}
    except Exception as e:
        return {"error": str(e)}

# ==================== Phone lookup ====================
async def numverify_lookup(session, phone):
    url = "http://apilayer.net/api/validate"
    params = {"access_key": NUMVERIFY_KEY, "number": phone, "format": 1}
    data = await fetch_json(session, url, params)
    if data and "valid" in data:
        return (f"📞 NumVerify:\n"
                f"Valid: {data.get('valid')}\n"
                f"Country: {data.get('country_name')} ({data.get('country_code')})\n"
                f"Carrier: {data.get('carrier')}\n"
                f"Line type: {data.get('line_type')}")
    return "📞 NumVerify: No data"

async def veriphone_lookup(session, phone):
    url = "https://veriphone.com/api/verify"
    params = {"api_key": VERIPHONE_KEY, "phone": phone, "format": "json"}
    data = await fetch_json(session, url, params)
    if data and "phone_valid" in data:
        return (f"📱 VeriPhone:\nValid: {data.get('phone_valid')}\nCountry: {data.get('country')}\nCarrier: {data.get('carrier')}")
    return "📱 VeriPhone: No data"

async def ofdata_lookup(session, phone):
    return "📂 OFDATA: API requires additional info (not implemented in public version)"

async def smsc_lookup(session, phone):
    return "📨 SMSC: API not documented for lookup"

# ==================== Email leak lookup ====================
async def psbdmp_email(session, email):
    url = f"https://psbdmp.ws/api/search/email/{email}"
    data = await fetch_json(session, url)
    if isinstance(data, list) and data:
        leaks = data[:5]
        lines = [f"🔍 {l.get('title', 'No title')} - {l.get('date', 'unknown')}" for l in leaks]
        return "📧 PSBDMP leaks:\n" + "\n".join(lines)
    return "📧 PSBDMP: no leaks found"

async def proxynova_email(session, email):
    url = "https://api.proxynova.com/comb"
    params = {"query": email, "start": 0, "limit": 20}
    data = await fetch_json(session, url, params)
    if data and "recordsTotal" in data and data["recordsTotal"] > 0:
        total = data["recordsTotal"]
        first = data.get("records", [])[:3]
        lines = [f"🔐 {r.get('username', '')}:{r.get('password', '')}" for r in first if r.get('password')]
        return f"📧 ProxyNova: {total} records found.\n" + "\n".join(lines[:3]) if lines else "Records exist but no passwords shown."
    return "📧 ProxyNova: nothing found"

async def breachdb_email(session, email):
    return "🌊 BreachDB: API not provided, web scraping needed"

# ==================== IP geolocation ====================
async def ipgeolocation(session, ip):
    url = f"https://api.ipgeolocation.io/ipgeo?apiKey={IPGEOLOCATION_KEY}&ip={ip}"
    data = await fetch_json(session, url)
    if data and "ip" in data:
        return (f"🌐 ipgeolocation.io:\nIP: {data.get('ip')}\nCountry: {data.get('country_name')} ({data.get('country_code2')})\nRegion: {data.get('state_prov')}\nCity: {data.get('city')}\nISP: {data.get('isp')}")
    return "🌐 ipgeolocation: error"

async def ip2location(session, ip):
    url = f"https://api.ip2location.io/?key={IP2LOCATION_KEY}&ip={ip}"
    data = await fetch_json(session, url)
    if data and "country_name" in data:
        return (f"📍 ip2location:\nCountry: {data.get('country_name')}\nRegion: {data.get('region_name')}\nCity: {data.get('city_name')}\nISP: {data.get('isp')}")
    return "📍 ip2location: error"

# ==================== Username / VK lookup ====================
async def cavalier_username(session, username):
    url = f"https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-username?username={username}"
    data = await fetch_json(session, url)
    if data and "found" in data:
        return f"👤 Cavalier: found {data.get('count', 0)} records"
    return "👤 Cavalier: not found"

async def vk_by_username(session, username):
    url = "https://api.vk.com/method/users.get"
    params = {
        "access_token": VK_ACCESS_TOKEN,
        "v": "5.131",
        "user_ids": username,
        "fields": "first_name,last_name,status,sex,country"
    }
    data = await fetch_json(session, url, params)
    if data and "response" in data and data["response"]:
        u = data["response"][0]
        return (f"VK (@{username}):\nID: {u.get('id')}\nName: {u.get('first_name')} {u.get('last_name')}\nStatus: {u.get('status', 'none')}\nGender: {u.get('sex')}\nCountry: {u.get('country', {}).get('title', 'unknown')}")
    return "VK: user not found"

async def vk_by_id(session, user_id):
    url = "https://api.vk.com/method/users.get"
    params = {
        "access_token": VK_ACCESS_TOKEN,
        "v": "5.131",
        "user_ids": user_id,
        "fields": "first_name,last_name,status,sex,country"
    }
    data = await fetch_json(session, url, params)
    if data and "response" in data and data["response"]:
        u = data["response"][0]
        return (f"VK ID {user_id}:\nName: {u.get('first_name')} {u.get('last_name')}\nStatus: {u.get('status', 'none')}\nGender: {u.get('sex')}\nCountry: {u.get('country', {}).get('title', 'unknown')}")
    looka = f"https://looka.one/vk_user/id{user_id}"
    murix = f"http://api.murix.ru/eye?v=5.131&user_ids={user_id}"
    return f"VK (official): not found\nAlternatives:\n- Looka: {looka}\n- Murix: {murix}"

# ==================== Command handlers ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 OSINT Bot with 20+ APIs.\n\n"
        "Commands:\n"
        "/phone <number> – phone lookup\n"
        "/email <address> – email leaks\n"
        "/ip <address> – IP geolocation\n"
        "/username <nick> – username search (VK, Cavalier)\n"
        "/vk <id or nick> – VK info\n"
        "/leak <text> – general leak search\n"
        "/help – this help"
    )

async def phone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /phone 79261234567")
        return
    phone = context.args[0].replace("+", "").replace(" ", "")
    async with aiohttp.ClientSession() as session:
        tasks = [numverify_lookup(session, phone), veriphone_lookup(session, phone), ofdata_lookup(session, phone), smsc_lookup(session, phone)]
        results = await asyncio.gather(*tasks)
    reply = "📞 PHONE RESULTS:\n\n" + "\n\n".join(results)
    await update.message.reply_text(reply[:4000])

async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /email user@example.com")
        return
    email = context.args[0].lower()
    async with aiohttp.ClientSession() as session:
        tasks = [psbdmp_email(session, email), proxynova_email(session, email), breachdb_email(session, email)]
        results = await asyncio.gather(*tasks)
    reply = "📧 EMAIL LEAKS:\n\n" + "\n\n".join(results)
    await update.message.reply_text(reply[:4000])

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /ip 8.8.8.8")
        return
    ip = context.args[0]
    async with aiohttp.ClientSession() as session:
        tasks = [ipgeolocation(session, ip), ip2location(session, ip)]
        results = await asyncio.gather(*tasks)
    reply = "🌍 IP GEOLOCATION:\n\n" + "\n\n".join(results)
    await update.message.reply_text(reply[:4000])

async def username_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /username some_nick")
        return
    username = context.args[0]
    async with aiohttp.ClientSession() as session:
        cav = await cavalier_username(session, username)
        vk = await vk_by_username(session, username)
    reply = f"👤 USERNAME SEARCH: {username}\n\n{cav}\n\n{vk}"
    await update.message.reply_text(reply[:4000])

async def vk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /vk 1 or /vk durov")
        return
    uid = context.args[0]
    async with aiohttp.ClientSession() as session:
        result = await vk_by_id(session, uid)
    await update.message.reply_text(result[:4000])

async def leak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /leak query")
        return
    query = " ".join(context.args)
    async with aiohttp.ClientSession() as session:
        ps = await psbdmp_general(session, query)
        pn = await proxynova_general(session, query)
    reply = f"🔍 LEAK SEARCH: {query}\n\n{ps}\n\n{pn}"
    await update.message.reply_text(reply[:4000])

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def psbdmp_general(session, query):
    url = f"https://psbdmp.ws/api/search/{query}"
    data = await fetch_json(session, url)
    if isinstance(data, list) and data:
        lines = [d.get('title', '')[:100] for d in data[:5]]
        return "🔍 PSBDMP:\n" + "\n".join(lines)
    return "PSBDMP: no results"

async def proxynova_general(session, query):
    url = "https://api.proxynova.com/comb"
    params = {"query": query, "start": 0, "limit": 20}
    data = await fetch_json(session, url, params)
    if data and data.get("recordsTotal", 0) > 0:
        total = data["recordsTotal"]
        return f"🔐 ProxyNova: {total} records found"
    return "ProxyNova: no results"

# ==================== Run bot ====================
def run_bot():
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CommandHandler("phone", phone_command))
    bot_app.add_handler(CommandHandler("email", email_command))
    bot_app.add_handler(CommandHandler("ip", ip_command))
    bot_app.add_handler(CommandHandler("username", username_command))
    bot_app.add_handler(CommandHandler("vk", vk_command))
    bot_app.add_handler(CommandHandler("leak", leak_command))
    bot_app.run_polling()

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
    else:
        threading.Thread(target=run_bot).start()
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
