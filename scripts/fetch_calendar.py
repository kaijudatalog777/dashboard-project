# fetch_calendar.py
# Google Calendarから今日・明日の予定を取得する
# 環境変数: なし（token.jsonを使用）

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_FILE = Path(__file__).parent.parent / "token.json"
CLIENT_SECRET = Path(__file__).parent.parent / "client_secret.json"

FETCH_DAYS = 2  # 今日と明日


def fetch_events() -> list[dict]:
    """Google Calendarから直近の予定を取得して返す。"""
    if not TOKEN_FILE.exists():
        print("WARN: token.json が存在しません。auth_calendar.py を実行してください。")
        return []

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # トークンの更新
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
        except Exception as e:
            print(f"WARN: トークンの更新に失敗しました: {e}")
            return []

    try:
        service = build("calendar", "v3", credentials=creds)
    except Exception as e:
        print(f"WARN: Google Calendar APIの初期化に失敗しました: {e}")
        return []

    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    range_end = today_start + timedelta(days=FETCH_DAYS)

    try:
        result = service.events().list(
            calendarId="primary",
            timeMin=today_start.isoformat(),
            timeMax=range_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
    except Exception as e:
        print(f"WARN: Google Calendarの取得に失敗しました: {e}")
        return []

    events = []
    for item in result.get("items", []):
        title = item.get("summary", "（タイトルなし）")
        start = item["start"].get("dateTime") or item["start"].get("date", "")
        end = item["end"].get("dateTime") or item["end"].get("date", "")

        # 日時フォーマット
        try:
            if "T" in start:
                dt = datetime.fromisoformat(start)
                start_str = dt.strftime("%m/%d %H:%M")
                dt_end = datetime.fromisoformat(end)
                end_str = dt_end.strftime("%H:%M")
                time_str = f"{start_str}〜{end_str}"
            else:
                time_str = f"{start}（終日）"
        except Exception:
            time_str = start

        events.append({
            "title": title,
            "start": start,
            "time": time_str,
            "location": item.get("location", ""),
        })

    return events


if __name__ == "__main__":
    events = fetch_events()
    print(f"取得件数: {len(events)}")
    for e in events:
        loc = f" @{e['location']}" if e.get("location") else ""
        print(f"  {e['time']} {e['title']}{loc}")
