# build_dashboard.py
# メイン実行ファイル。各データを収集→Geminiで要約→index.html生成。
# 実行: python scripts/build_dashboard.py

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

# スクリプトのディレクトリをパスに追加（同階層モジュールのimport用）
sys.path.insert(0, str(Path(__file__).parent))

from fetch_notion import fetch_todos
from fetch_github import fetch_recent_commits
from fetch_obsidian import fetch_recent_notes
from fetch_rss import fetch_all_feeds
from summarize import summarize_todos, summarize_commits, summarize_notes, summarize_rss
from write_notion_dashboard import write_dashboard

load_dotenv()

# 出力先
OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "index.html"

JST = timezone(timedelta(hours=9))


def build():
    now = datetime.now(JST)
    date_str = now.strftime("%Y年%m月%d日 %H:%M JST")
    print(f"=== ダッシュボード生成開始: {date_str} ===")

    # --- データ収集 ---
    print("Notion TODOを取得中...")
    todos = _safe_fetch(fetch_todos, "Notion TODO", [])

    print("GitHubコミットを取得中...")
    commits = _safe_fetch(fetch_recent_commits, "GitHubコミット", [])

    print("Obsidianノートを取得中...")
    notes = _safe_fetch(fetch_recent_notes, "Obsidianノート", [])

    print("RSSフィードを取得中...")
    articles = _safe_fetch(fetch_all_feeds, "RSSフィード", [])

    # --- Gemini要約 ---
    print("Geminiで要約中...")
    todo_summary = summarize_todos(todos)
    commit_summary = summarize_commits(commits)
    note_summary = summarize_notes(notes)
    rss_summary = summarize_rss(articles)

    # --- Notionダッシュボード書き込み ---
    print("Notionダッシュボードに書き込み中...")
    try:
        write_dashboard(
            date_str=date_str,
            todos=todos,
            todo_summary=todo_summary,
            commits=commits,
            commit_summary=commit_summary,
            notes=notes,
            note_summary=note_summary,
            articles=articles,
            rss_summary=rss_summary,
        )
    except SystemExit:
        print("WARN: Notionダッシュボードへの書き込みをスキップしました")
    except Exception as e:
        print(f"WARN: Notionダッシュボードへの書き込み中にエラー: {e}")

    # --- HTML生成 ---
    print(f"index.html を生成中: {OUTPUT_PATH}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    html = _render_html(
        date_str=date_str,
        todos=todos,
        todo_summary=todo_summary,
        commits=commits,
        commit_summary=commit_summary,
        notes=notes,
        note_summary=note_summary,
        articles=articles,
        rss_summary=rss_summary,
    )
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print("=== 生成完了 ===")


def _safe_fetch(fn, label: str, default):
    """取得失敗時はデフォルト値を返してビルドを継続する。"""
    try:
        return fn()
    except SystemExit:
        print(f"WARN: {label} の取得をスキップしました")
        return default
    except Exception as e:
        print(f"WARN: {label} の取得中に予期しないエラー: {e}")
        return default


def _render_html(
    date_str, todos, todo_summary,
    commits, commit_summary,
    notes, note_summary,
    articles, rss_summary,
) -> str:
    """ダッシュボードのHTMLを生成して返す。"""

    def _esc(s: str) -> str:
        """HTMLエスケープ。"""
        return (s.replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;")
                  .replace('"', "&quot;"))

    # --- Notion TODOセクション ---
    todo_rows = ""
    for t in todos:
        due = _esc(t.get("due") or "—")
        todo_rows += f"""
        <tr>
          <td>{_esc(t['status'])}</td>
          <td>{_esc(t['title'])}</td>
          <td>{due}</td>
        </tr>"""

    # --- GitHubコミットセクション ---
    commit_rows = ""
    for c in commits[:10]:
        commit_rows += f"""
        <tr>
          <td>{_esc(c['date'])}</td>
          <td>{_esc(c['repo'])}</td>
          <td><a href="{_esc(c['url'])}" target="_blank">{_esc(c['message'])}</a></td>
        </tr>"""

    # --- Obsidianノートセクション ---
    note_items = ""
    for n in notes[:5]:
        note_items += f"""
        <li><strong>{_esc(n['title'])}</strong> <small>({_esc(n['modified'])})</small></li>"""

    # --- RSSセクション（カテゴリ別） ---
    by_label: dict[str, list] = {}
    for a in articles:
        by_label.setdefault(a["label"], []).append(a)

    rss_sections = ""
    for label, items in by_label.items():
        rss_sections += f"<h4>{_esc(label)}</h4><ul>"
        for a in items:
            link = _esc(a["link"])
            title = _esc(a["title"])
            pub = _esc(a.get("published", ""))
            rss_sections += f'<li><a href="{link}" target="_blank">{title}</a> <small>{pub}</small></li>'
        rss_sections += "</ul>"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>パーソナルダッシュボード</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; margin: 0; padding: 20px; }}
    h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 8px; }}
    h2 {{ color: #2980b9; margin-top: 32px; }}
    h3 {{ color: #555; }}
    .summary-box {{
      background: #eaf4fb; border-left: 4px solid #3498db;
      padding: 12px 16px; border-radius: 4px; margin-bottom: 16px;
      white-space: pre-wrap;
    }}
    table {{ border-collapse: collapse; width: 100%; background: #fff; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
    th {{ background: #3498db; color: #fff; padding: 10px 12px; text-align: left; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
    tr:last-child td {{ border-bottom: none; }}
    ul {{ background: #fff; border-radius: 6px; padding: 12px 24px; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
    li {{ margin: 6px 0; }}
    a {{ color: #2980b9; }}
    .generated {{ color: #aaa; font-size: 0.85em; margin-top: 40px; }}
  </style>
</head>
<body>
  <h1>パーソナルダッシュボード</h1>
  <p>生成日時: <strong>{_esc(date_str)}</strong></p>

  <!-- TODO セクション -->
  <h2>TODO（Notion）</h2>
  <div class="summary-box">{_esc(todo_summary)}</div>
  <table>
    <thead><tr><th>ステータス</th><th>タスク</th><th>期限</th></tr></thead>
    <tbody>{todo_rows if todo_rows else '<tr><td colspan="3">データなし</td></tr>'}</tbody>
  </table>

  <!-- GitHubコミット セクション -->
  <h2>GitHub 直近コミット</h2>
  <div class="summary-box">{_esc(commit_summary)}</div>
  <table>
    <thead><tr><th>日時</th><th>リポジトリ</th><th>コミット</th></tr></thead>
    <tbody>{commit_rows if commit_rows else '<tr><td colspan="3">データなし</td></tr>'}</tbody>
  </table>

  <!-- Obsidianノート セクション -->
  <h2>Obsidian 直近ノート</h2>
  <div class="summary-box">{_esc(note_summary)}</div>
  <ul>{note_items if note_items else '<li>データなし</li>'}</ul>

  <!-- RSSニュース セクション -->
  <h2>今日のニュース</h2>
  <div class="summary-box">{_esc(rss_summary)}</div>
  {rss_sections if rss_sections else '<p>データなし</p>'}

  <p class="generated">このページは自動生成されています。</p>
</body>
</html>
"""


if __name__ == "__main__":
    build()
