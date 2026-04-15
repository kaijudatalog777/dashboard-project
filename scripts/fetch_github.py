# fetch_github.py
# GitHub APIから直近のコミット履歴を取得する
# 環境変数: GITHUB_TOKEN, GITHUB_USERNAME

import os
import sys
from datetime import datetime, timedelta, timezone
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

# 取得対象の日数
FETCH_DAYS = 7


def fetch_recent_commits() -> list[dict]:
    """過去FETCH_DAYS日分のコミットを全リポジトリから取得して返す。"""
    token = os.getenv("GITHUB_TOKEN")
    username = os.getenv("GITHUB_USERNAME")

    if not token:
        print("ERROR: GITHUB_TOKEN が設定されていません")
        sys.exit(1)
    if not username:
        print("ERROR: GITHUB_USERNAME が設定されていません")
        sys.exit(1)

    auth = Auth.Token(token)
    g = Github(auth=auth)

    since = datetime.now(timezone.utc) - timedelta(days=FETCH_DAYS)
    commits = []

    try:
        user = g.get_user(username)
        repos = user.get_repos(type="owner", sort="pushed")
    except Exception as e:
        print(f"ERROR: GitHub APIの接続に失敗しました: {e}")
        sys.exit(1)

    for repo in repos:
        # 更新日がFETCH_DAYS以内のリポジトリのみ対象
        if repo.pushed_at and repo.pushed_at < since:
            continue
        try:
            repo_commits = repo.get_commits(since=since, author=username)
            for c in repo_commits:
                commits.append({
                    "repo": repo.name,
                    "message": c.commit.message.splitlines()[0],  # 1行目のみ
                    "date": c.commit.author.date.strftime("%Y-%m-%d %H:%M"),
                    "url": c.html_url,
                })
        except Exception:
            # コミット取得失敗は無視して続行
            continue

    # 日付降順でソート
    commits.sort(key=lambda x: x["date"], reverse=True)
    return commits


if __name__ == "__main__":
    commits = fetch_recent_commits()
    print(f"取得コミット数: {len(commits)}")
    for c in commits[:10]:
        print(f"  [{c['date']}] {c['repo']}: {c['message']}")
