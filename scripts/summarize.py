# summarize.py
# Gemini APIを使ってデータを日本語で要約する
# 環境変数: GEMINI_API_KEY

import os
import sys
from google import genai
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_client():
    """Geminiクライアントのシングルトン取得。"""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: GEMINI_API_KEY が設定されていません")
            sys.exit(1)
        _client = genai.Client(api_key=api_key)
    return _client


def summarize_todos(todos: list[dict]) -> str:
    """TODOリストを要約する。"""
    if not todos:
        return "本日のTODOはありません。"

    lines = []
    for t in todos:
        due = f"（期限: {t['due']}）" if t.get("due") else ""
        lines.append(f"- [{t['status']}] {t['title']}{due}")

    prompt = (
        "以下は今日のTODOリストです。優先度の高いものや期限が近いものを中心に、"
        "100字程度で日本語で簡潔に要約してください。\n\n"
        + "\n".join(lines)
    )
    return _generate(prompt)


def summarize_commits(commits: list[dict]) -> str:
    """GitHubコミット履歴を要約する。"""
    if not commits:
        return "直近のコミットはありません。"

    lines = [f"- [{c['date']}] {c['repo']}: {c['message']}" for c in commits[:20]]
    prompt = (
        "以下は直近のGitHubコミット履歴です。どのようなプロジェクトでどんな作業をしたか、"
        "100字程度で日本語で簡潔に要約してください。\n\n"
        + "\n".join(lines)
    )
    return _generate(prompt)


def summarize_notes(notes: list[dict]) -> str:
    """Obsidianノートを要約する。"""
    if not notes:
        return "直近の更新ノートはありません。"

    parts = []
    for n in notes[:5]:
        parts.append(f"### {n['title']}（{n['modified']}）\n{n['content'][:500]}")

    prompt = (
        "以下は直近更新されたObsidianノートの抜粋です。主なテーマや気づきを"
        "100字程度で日本語で簡潔に要約してください。\n\n"
        + "\n\n".join(parts)
    )
    return _generate(prompt)


def summarize_rss(articles: list[dict]) -> str:
    """RSSフィード記事を要約する。"""
    if not articles:
        return "本日のニュースは取得できませんでした。"

    # カテゴリ別にまとめる
    by_label: dict[str, list[str]] = {}
    for a in articles:
        label = a["label"]
        by_label.setdefault(label, [])
        by_label[label].append(f"- {a['title']}")

    sections = []
    for label, titles in by_label.items():
        sections.append(f"【{label}】\n" + "\n".join(titles))

    prompt = (
        "以下は今日のニュースヘッドラインです。カテゴリごとに重要なトピックを"
        "200字程度で日本語で簡潔にまとめてください。\n\n"
        + "\n\n".join(sections)
    )
    return _generate(prompt)


def _generate(prompt: str) -> str:
    """Geminiにプロンプトを送り、テキストを返す。"""
    client = _get_client()
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"ERROR: Gemini API呼び出しに失敗しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 動作確認用
    result = _generate("「おはようございます」を英語に翻訳してください。")
    print(result)
