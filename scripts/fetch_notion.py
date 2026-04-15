# fetch_notion.py
# Notion APIからTODOリストを取得する
# 環境変数: NOTION_API_KEY, NOTION_DATABASE_ID

import os
import sys
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()


def fetch_todos() -> list[dict]:
    """NotionデータベースからTODOアイテムを取得して返す。"""
    api_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not api_key:
        print("ERROR: NOTION_API_KEY が設定されていません")
        sys.exit(1)
    if not database_id:
        print("ERROR: NOTION_DATABASE_ID が設定されていません")
        sys.exit(1)

    client = Client(auth=api_key)

    try:
        response = client.databases.query(
            database_id=database_id,
            filter={
                "property": "ステータス",
                "status": {
                    "does_not_equal": "完了"
                }
            },
            sorts=[
                {
                    "property": "期限",
                    "direction": "ascending"
                }
            ],
        )
    except Exception as e:
        print(f"ERROR: Notion APIの取得に失敗しました: {e}")
        sys.exit(1)

    todos = []
    for page in response.get("results", []):
        props = page.get("properties", {})

        # タイトル取得（"Memo"）
        title_prop = props.get("Memo", {})
        title_parts = title_prop.get("title", [])
        title = "".join(part.get("plain_text", "") for part in title_parts)

        # ステータス取得
        status_prop = props.get("ステータス", {})
        status = status_prop.get("status", {}).get("name", "未着手")

        # 期限取得
        due_prop = props.get("期限", {})
        due = due_prop.get("date", {})
        due_date = due.get("start", "") if due else ""

        # 緊急度取得
        urgency_prop = props.get("緊急度", {})
        urgency_list = urgency_prop.get("multi_select", [])
        urgency = "、".join([u.get("name", "") for u in urgency_list])

        # プロジェクト取得
        project_prop = props.get("プロジェクト", {})
        project_list = project_prop.get("multi_select", [])
        project = "、".join([p.get("name", "") for p in project_list])

        # タグ取得
        tag_prop = props.get("タグ", {})
        tag_list = tag_prop.get("multi_select", [])
        tags = "、".join([t.get("name", "") for t in tag_list])

        if title:
            todos.append({
                "title": title,
                "status": status,
                "due": due_date,
                "urgency": urgency,
                "project": project,
                "tags": tags,
            })

    return todos


if __name__ == "__main__":
    todos = fetch_todos()
    print(f"取得件数: {len(todos)}")
    for t in todos:
        print(f"  [{t['status']}] {t['title']} (期限: {t['due'] or 'なし'}) 緊急度: {t['urgency'] or 'なし'} PJ: {t['project'] or 'なし'}")
