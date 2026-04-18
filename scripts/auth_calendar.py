# auth_calendar.py
# Google Calendar APIの初回認証（1回だけ実行する）
# ブラウザが開くのでGoogleアカウントでログインして許可してください

from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CLIENT_SECRET = Path(__file__).parent.parent / "client_secret.json"
TOKEN_FILE = Path(__file__).parent.parent / "token.json"

flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
creds = flow.run_local_server(port=0)

TOKEN_FILE.write_text(creds.to_json())
print(f"認証完了！トークンを保存しました: {TOKEN_FILE}")
