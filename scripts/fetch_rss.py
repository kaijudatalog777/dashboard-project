# fetch_rss.py
# 複数のRSSフィードを取得・パースする

import sys
import feedparser
from datetime import datetime

# RSSソース一覧
RSS_SOURCES = [
    {"label": "AI/IT",    "url": "https://xtech.nikkei.com/rss/xtech-it.rdf"},
    {"label": "経済",     "url": "https://www3.nhk.or.jp/rss/news/cat6.xml"},
    {"label": "労務",     "url": "https://www.mhlw.go.jp/stf/news.rdf"},
    {"label": "ビジネス", "url": "https://toyokeizai.net/list/feed/rss"},
    {"label": "健康",     "url": "https://www3.nhk.or.jp/rss/news/cat7.xml"},
]

# 1ソースあたりの最大取得件数
MAX_ITEMS_PER_SOURCE = 5


def fetch_all_feeds() -> list[dict]:
    """
    全RSSソースを取得し、記事リストを返す。
    各記事は { label, title, summary, link, published } を持つ。
    """
    articles = []

    for source in RSS_SOURCES:
        label = source["label"]
        url = source["url"]

        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"WARN: [{label}] フィード取得に失敗: {e}")
            continue

        if feed.bozo and feed.bozo_exception:
            print(f"WARN: [{label}] パースエラー: {feed.bozo_exception}")

        entries = feed.entries[:MAX_ITEMS_PER_SOURCE]
        for entry in entries:
            title = entry.get("title", "（タイトルなし）")
            summary = entry.get("summary", entry.get("description", ""))
            # タグを除去して平文化（簡易版）
            summary = _strip_tags(summary)
            link = entry.get("link", "")
            published = _parse_published(entry)

            articles.append({
                "label": label,
                "title": title,
                "summary": summary[:300],  # 長すぎる要約を切り詰め
                "link": link,
                "published": published,
            })

    return articles


def _strip_tags(text: str) -> str:
    """HTMLタグを簡易除去する。"""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_published(entry) -> str:
    """エントリの公開日を文字列で返す。取得できなければ空文字。"""
    # feedparser は published_parsed (time.struct_time) を提供する場合がある
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6])
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    return entry.get("published", "")


if __name__ == "__main__":
    articles = fetch_all_feeds()
    print(f"取得記事数: {len(articles)}")
    for a in articles:
        print(f"  [{a['label']}] {a['published']} {a['title']}")
