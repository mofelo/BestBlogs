import feedparser
import requests
from telegram import Bot
from telegram.constants import ParseMode
import xml.etree.ElementTree as ET
import json
import os
import time

# ==================== 配置区 ====================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# 关键：使用原作者永远有效的 OPML（等您以后想自己维护再改）
OPML_URL = 'https://raw.githubusercontent.com/ginobefun/BestBlogs/main/BestBlogs_RSS_ALL.opml'

STATE_FILE = 'rss_state.json'   # 用来记住每个 RSS 已经推到哪一条
# ===============================================

bot = Bot(token=TELEGRAM_TOKEN)

def parse_opml(url):
    r = requests.get(url)
    root = ET.fromstring(r.content)
    feeds = [item.get('xmlUrl') for item in root.findall('.//outline') if item.get('xmlUrl')]
    return feeds

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def send(entry):
    title = entry.get('title', '无标题')
    link = entry.link
    summary = (entry.get('summary') or '')[:250] + '...' if entry.get('summary') else ''
    msg = f"<b>{title}</b>\n{summary}\n\n<a href='{link}'>阅读原文</a>"
    bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode=ParseMode.HTML,
                     disable_web_page_preview=True)

def main():
    feeds = parse_opml(OPML_URL)
    state = load_state()
    pushed = 0

    # 第一次建议只跑前 8~10 个源，避免刷屏
    for url in feeds[:10]:
        last_id = state.get(url, '')
        feed = feedparser.parse(url)
        if not feed.entries:
            continue

        new_entries = [e for e in feed.entries if e.get('id', e.link) != last_id]
        for entry in reversed(new_entries[-5:]):   # 每个源最多发最新的 5 条
            send(entry)
            pushed += 1

        if feed.entries:
            state[url] = feed.entries[0].get('id', feed.entries[0].link)
        time.sleep(1.5)   # 防止触发 Telegram 频率限制

    save_state(state)
    print(f"本次检查完成，共推送 {pushed} 条新文章")

if __name__ == '__main__':
    main()
