# obsidian_to_notion.py
# ObsidianのノートからタスクをGeminiで抽出してNotionに登録する
# 使い方:
#   python scripts/obsidian_to_notion.py           # 直近7日のノートから抽出
#   python scripts/obsidian_to_notion.py --days 3  # 直近3日のノートから抽出
#   python scripts/obsidian_to_notion.py --file "ノート名"  # 特定ノートから抽出

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from notion_client import Client
from google import genai

load_dotenv()

FETCH_DAYS_DEFAULT = 7
MAX_CHARS_PER_FILE = 3000


def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY が設定されていません")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def _get_notion_client():
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        print("ERROR: NOTION_API_KEY が設定されていません")
        sys.exit(1)
    return Client(auth=api_key)


def _get_database_id():
    db_id = os.getenv("NOTION_DATABASE_ID")
    if not db_id:
        print("ERROR: NOTION_DATABASE_ID が設定されていません")
        sys.exit(1)
    return db_id


def load_notes(days: int = FETCH_DAYS_DEFAULT, filename: str = None) -> list[dict]:
    """Obsidianノートを読み込む。"""
    vault_path_str = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path_str:
        print("ERROR: OBSIDIAN_VAULT_PATH が設定されていません")
        sys.exit(1)

    vault_path = Path(vault_path_str)
    if not vault_path.is_dir():
        print(f"ERROR: Vaultパスが存在しません: {vault_path}")
        sys.exit(1)

    notes = []

    if filename:
        # 特定ファイルを検索
        matches = list(vault_path.rglob(f"*{filename}*.md"))
        if not matches:
            print(f"ERROR: '{filename}' に一致するノートが見つかりません")
            sys.exit(1)
        targets = matches[:3]
    else:
        # 直近N日のファイル
        cutoff = datetime.now().timestamp() - days * 86400
        targets = [
            f for f in vault_path.rglob("*.md")
            if f.stat().st_mtime >= cutoff
        ]
        targets.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    for md_file in targets:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            trimmed = content[:MAX_CHARS_PER_FILE]
            if len(content) > MAX_CHARS_PER_FILE:
                trimmed += "\n（以下省略）"
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            notes.append({
                "title": md_file.stem,
                "content": trimmed,
                "modified": mtime,
            })
        except Exception as e:
            print(f"WARN: {md_file.name} の読み込みに失敗: {e}")

    return notes


def extract_tasks(notes: list[dict]) -> list[dict]:
    """GeminiでノートからタスクをJSON形式で抽出する。"""
    if not notes:
        print("対象ノートが見つかりませんでした。")
        return []

    client = _get_gemini_client()

    parts = []
    for n in notes:
        parts.append(f"### {n['title']}（{n['modified']}）\n{n['content']}")

    prompt = (
        "以下のObsidianノートの内容を読んで、アクションアイテム（やること・タスク）を抽出してください。\n"
        "具体的な行動が必要なものだけを抽出し、以下のJSON形式で返してください。\n"
        "メモや情報の記録はタスクに含めないでください。\n\n"
        "出力形式（JSONのみ、説明文は不要）:\n"
        '[\n'
        '  {"title": "タスク名", "memo": "補足（任意）", "urgency": "高/中/低"},\n'
        '  ...\n'
        ']\n\n'
        "タスクが見つからない場合は空の配列 [] を返してください。\n\n"
        "=== ノート内容 ===\n\n"
        + "\n\n".join(parts)
    )

    import time
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt,
            )
            text = response.text.strip()
            # JSONブロックの抽出
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            tasks = json.loads(text)
            return tasks
        except json.JSONDecodeError:
            print(f"WARN: JSON解析に失敗しました。再試行 ({attempt+1}/3)...")
            time.sleep(5)
            continue
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                print(f"WARN: Gemini混雑中。10秒後にリトライ ({attempt+1}/3)...")
                time.sleep(10)
                continue
            print(f"ERROR: Gemini API呼び出しに失敗: {e}")
            sys.exit(1)

    print("ERROR: タスク抽出に失敗しました")
    return []


def create_notion_tasks(tasks: list[dict]) -> int:
    """抽出したタスクをNotionデータベースに登録する。"""
    client = _get_notion_client()
    database_id = _get_database_id()
    created = 0

    for task in tasks:
        title = task.get("title", "").strip()
        memo = task.get("memo", "").strip()
        urgency = task.get("urgency", "低")

        if not title:
            continue

        try:
            props = {
                "Memo": {
                    "title": [{"text": {"content": title}}]
                },
                "ステータス": {
                    "status": {"name": "未着手"}
                },
                "出所": {
                    "multi_select": [{"name": "Obsidian"}]
                },
                "緊急度": {
                    "multi_select": [{"name": urgency}]
                },
            }
            if memo:
                props["メモ"] = {
                    "rich_text": [{"text": {"content": memo}}]
                }

            client.pages.create(
                parent={"database_id": database_id},
                properties=props,
            )
            created += 1
            print(f"  [OK] 登録: {title}")
        except Exception as e:
            print(f"  [NG] 登録失敗: {title} -> {e}")

    return created


def main():
    parser = argparse.ArgumentParser(description="ObsidianノートからNotionタスクを作成")
    parser.add_argument("--days", type=int, default=FETCH_DAYS_DEFAULT, help="取得日数（デフォルト7日）")
    parser.add_argument("--file", type=str, default=None, help="特定ノートのファイル名（部分一致）")
    parser.add_argument("--dry-run", action="store_true", help="Notionへの登録をせず抽出結果のみ表示")
    args = parser.parse_args()

    # ノート読み込み
    print(f"Obsidianノートを読み込み中...")
    notes = load_notes(days=args.days, filename=args.file)
    if not notes:
        print("対象ノートが見つかりませんでした。")
        return

    print(f"対象ノート: {len(notes)}件")
    for n in notes:
        print(f"  - {n['title']}（{n['modified']}）")

    # タスク抽出
    print("\nGeminiでタスクを抽出中...")
    tasks = extract_tasks(notes)

    if not tasks:
        print("タスクは見つかりませんでした。")
        return

    # 抽出結果を表示
    print(f"\n=== 抽出されたタスク（{len(tasks)}件）===")
    for i, t in enumerate(tasks, 1):
        urgency = t.get("urgency", "低")
        memo = f" ※{t['memo']}" if t.get("memo") else ""
        print(f"  {i}. [{urgency}] {t['title']}{memo}")

    if args.dry_run:
        print("\n（dry-runモード: Notionへの登録はスキップ）")
        return

    # Notionに登録
    print(f"\nNotionに登録中...")
    created = create_notion_tasks(tasks)
    print(f"\n完了: {created}/{len(tasks)}件を登録しました")


if __name__ == "__main__":
    main()
