# write_notion_dashboard.py
# ダッシュボードの内容をNotionページに書き込む
# 環境変数: NOTION_API_KEY, NOTION_DASHBOARD_PAGE_ID

import os
import sys
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()


def _get_client() -> Client:
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        print("ERROR: NOTION_API_KEY が設定されていません")
        sys.exit(1)
    return Client(auth=api_key)


def _get_page_id() -> str:
    page_id = os.getenv("NOTION_DASHBOARD_PAGE_ID")
    if not page_id:
        print("ERROR: NOTION_DASHBOARD_PAGE_ID が設定されていません")
        sys.exit(1)
    return page_id


def _clear_page(client: Client, page_id: str):
    """ページの既存ブロックのうち、データベースビュー以外を全削除する（ページネーション対応）。"""
    try:
        cursor = None
        while True:
            kwargs = {"block_id": page_id}
            if cursor:
                kwargs["start_cursor"] = cursor
            response = client.blocks.children.list(**kwargs)
            for block in response.get("results", []):
                if block.get("type") in ("child_database", "child_page"):
                    continue
                client.blocks.delete(block_id=block["id"])
            if response.get("has_more"):
                cursor = response.get("next_cursor")
            else:
                break
    except Exception as e:
        print(f"WARN: ページのクリアに失敗しました: {e}")


def _heading2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


def _heading3(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


def _table(headers: list[str], rows: list[list[str]]) -> dict:
    def _cell(text: str) -> list:
        return [{"type": "text", "text": {"content": text}}]

    children = [{"type": "table_row", "table_row": {"cells": [_cell(h) for h in headers]}}]
    for row in rows:
        children.append({"type": "table_row", "table_row": {"cells": [_cell(c) for c in row]}})

    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": len(headers),
            "has_column_header": True,
            "has_row_header": False,
            "children": children,
        }
    }


def _callout(text: str, emoji: str = "💡") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"type": "emoji", "emoji": emoji}
        }
    }


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


def _bullet(text: str, url: str = "") -> dict:
    if url:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": text, "link": {"url": url}}}]
            }
        }
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def write_dashboard(
    date_str: str,
    todos: list[dict],
    todo_summary: str,
    commits: list[dict],
    commit_summary: str,
    notes: list[dict],
    note_summary: str,
    articles: list[dict],
    rss_summary: str,
    events: list[dict] = [],
    wbs_summary: dict = None,
):
    """ダッシュボード内容をNotionページに書き込む。"""
    client = _get_client()
    page_id = _get_page_id()

    print(f"Notionダッシュボードページをクリア中...")
    _clear_page(client, page_id)

    blocks = []

    # ヘッダー
    blocks.append(_paragraph(f"生成日時: {date_str}"))
    blocks.append(_divider())

    # カレンダーセクション
    blocks.append(_heading2("📅 今日・明日の予定"))
    if events:
        for e in events:
            loc = f" @{e['location']}" if e.get("location") else ""
            blocks.append(_bullet(f"{e['time']} {e['title']}{loc}"))
    else:
        blocks.append(_paragraph("予定はありません"))
    blocks.append(_divider())

    # WBSセクション
    if wbs_summary and wbs_summary.get("total_tasks", 0) > 0:
        total = wbs_summary["total_tasks"]
        done = wbs_summary["done_tasks"]
        pct = round(done / total * 100, 1) if total else 0
        overdue = wbs_summary.get("overdue_tasks", [])
        today_t = wbs_summary.get("today_tasks", [])
        projects = wbs_summary.get("projects", [])
        category = wbs_summary.get("category_progress", [])

        blocks.append(_heading2("📊 WBS進捗サマリー"))

        # 全体KPI
        blocks.append(_callout(
            f"総タスク: {total}　完了率: {pct}%　期限切れ: {len(overdue)}件　今日期限: {len(today_t)}件",
            "📊"
        ))

        # プロジェクト一覧テーブル
        table_rows = []
        for proj in projects:
            proj_name = proj["title"]
            proj_total = proj["task_count"]
            proj_overdue = [t for t in overdue if t["project"] == proj_name]
            proj_cats = [c for c in category if c["project"] == proj_name]
            proj_done_count = sum(c["done"] for c in proj_cats)
            proj_pct = round(proj_done_count / proj_total * 100, 1) if proj_total else 0
            overdue_str = f"{len(proj_overdue)}件" if proj_overdue else "なし"
            table_rows.append([proj_name, str(proj_total), f"{proj_pct}%", overdue_str])

        blocks.append(_table(
            ["プロジェクト", "タスク数", "完了率", "期限切れ"],
            table_rows
        ))

        # 期限切れタスク一覧
        if overdue:
            blocks.append(_paragraph(""))
            blocks.append(_heading3("⚠️ 期限切れタスク"))
            for t in overdue[:15]:
                blocks.append(_bullet(f"{t['title']}（{t['end_date']}）― {t['project']}"))
            if len(overdue) > 15:
                blocks.append(_bullet(f"他 {len(overdue) - 15} 件..."))

        # 今日期限
        if today_t:
            blocks.append(_heading3("📌 今日期限のタスク"))
            for t in today_t:
                blocks.append(_bullet(f"{t['title']}（{t['end_date']}）― {t['project']}"))

        blocks.append(_divider())

    # TODOセクション（AI要約のみ・データベースビューは手動で設置）
    blocks.append(_heading2("📋 TODO（Notion）"))
    blocks.append(_callout(todo_summary, "📋"))
    blocks.append(_divider())

    # GitHubセクション
    blocks.append(_heading2("🔧 GitHub 直近コミット"))
    blocks.append(_callout(commit_summary, "🔧"))
    for c in commits[:10]:
        blocks.append(_bullet(f"[{c['date']}] {c['repo']}: {c['message']}", c['url']))
    if not commits:
        blocks.append(_paragraph("直近のコミットはありません"))
    blocks.append(_divider())

    # Obsidianセクション
    blocks.append(_heading2("📝 Obsidian 直近ノート"))
    blocks.append(_callout(note_summary, "📝"))
    for n in notes[:5]:
        blocks.append(_bullet(f"{n['title']} ({n['modified']})"))
    if not notes:
        blocks.append(_paragraph("データなし"))
    blocks.append(_divider())

    # RSSセクション
    blocks.append(_heading2("📰 今日のニュース"))
    blocks.append(_callout(rss_summary, "📰"))

    by_label: dict[str, list] = {}
    for a in articles:
        by_label.setdefault(a["label"], []).append(a)

    for label, items in by_label.items():
        blocks.append(_paragraph(f"【{label}】"))
        for a in items:
            pub = f" ({a.get('published', '')})" if a.get("published") else ""
            blocks.append(_bullet(f"{a['title']}{pub}", a.get("link", "")))

    if not articles:
        blocks.append(_paragraph("データなし"))

    # Notionに書き込む（100ブロック制限のため分割）
    try:
        for i in range(0, len(blocks), 95):
            chunk = blocks[i:i+95]
            client.blocks.children.append(block_id=page_id, children=chunk)
        print("Notionダッシュボードページの更新完了")
    except Exception as e:
        print(f"ERROR: Notionへの書き込みに失敗しました: {e}")
        sys.exit(1)
