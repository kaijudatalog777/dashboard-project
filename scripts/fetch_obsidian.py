# fetch_obsidian.py
# ObsidianのVaultからMarkdownファイルを読み込む
# 環境変数: OBSIDIAN_VAULT_PATH（Vaultのルートディレクトリパス）

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# 取得対象の日数（最終更新日基準）
FETCH_DAYS = 7
# 1ファイルあたりの最大文字数（要約トークン節約のため）
MAX_CHARS_PER_FILE = 2000


def fetch_recent_notes() -> list[dict]:
    """
    過去FETCH_DAYS日以内に更新されたMarkdownノートを返す。
    各ノートは { title, content, modified } を持つ。
    """
    vault_path_str = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path_str:
        print("ERROR: OBSIDIAN_VAULT_PATH が設定されていません")
        sys.exit(1)

    vault_path = Path(vault_path_str)
    if not vault_path.is_dir():
        print(f"ERROR: Vaultパスが存在しません: {vault_path}")
        sys.exit(1)

    cutoff = datetime.now().timestamp() - FETCH_DAYS * 86400
    notes = []

    for md_file in vault_path.rglob("*.md"):
        try:
            mtime = md_file.stat().st_mtime
        except OSError:
            continue

        if mtime < cutoff:
            continue

        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"WARN: {md_file} の読み込みに失敗: {e}")
            continue

        # 長すぎる場合は冒頭のみ
        trimmed = content[:MAX_CHARS_PER_FILE]
        if len(content) > MAX_CHARS_PER_FILE:
            trimmed += "\n（以下省略）"

        notes.append({
            "title": md_file.stem,
            "content": trimmed,
            "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
        })

    # 更新日降順でソート
    notes.sort(key=lambda x: x["modified"], reverse=True)
    return notes


if __name__ == "__main__":
    notes = fetch_recent_notes()
    print(f"取得ノート数: {len(notes)}")
    for n in notes[:5]:
        print(f"  [{n['modified']}] {n['title']}")
        print(f"    {n['content'][:100].replace(chr(10), ' ')}...")
