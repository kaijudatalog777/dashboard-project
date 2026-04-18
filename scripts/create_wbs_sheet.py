# create_wbs_sheet.py
# WBSデータをGoogle Sheetsに書き込む（Excelと同等のガントチャート付き）
# 環境変数: GOOGLE_SHEET_ID（既存シートID、なければ新規作成）

import os
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

import gspread
from gspread.utils import rowcol_to_a1
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
_BASE = Path(__file__).parent.parent
TOKEN_FILE = _BASE / "token.json" if (_BASE / "token.json").exists() else Path("token.json")

SHEET_TITLE = "WBSダッシュボード"
GANTT_DAYS = 180          # ガントチャート表示日数
GANTT_START_COL = 19      # S列（1始まり）
HEADER_ROW = 4
DATA_START_ROW = 5

# 列定義（1始まり）
COL = {
    "id": 1, "wbs_no": 2, "l1": 3, "l2": 4, "level": 5,
    "h1": 6, "h2": 7,
    "p_start": 8,   # H: 予定開始
    "p_end": 9,     # I: 予定終了
    "a_start": 10,  # J: 実績開始
    "a_end": 11,    # K: 実績終了
    "p_days": 12, "a_days": 13, "overrun": 14,
    "status": 15, "progress": 16, "deliverable": 17, "notes": 18,
}

STATUS_MAP = {"DONE": "完了", "IN_PROGRESS": "進行中", "TODO": "未着手"}


# ── 認証 ──────────────────────────────────────────────────────────────────

def _get_creds() -> Credentials:
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
    return creds


def _get_gspread(creds) -> gspread.Client:
    return gspread.authorize(creds)


def _get_sheets_service(creds):
    return build("sheets", "v4", credentials=creds)


# ── WBS階層ツリー構築 ──────────────────────────────────────────────────────

def _build_wbs_rows(tasks: list[dict]) -> list[dict]:
    """フラットなタスク配列をWBS番号・階層付きの行リストに変換する。"""
    task_map = {t["id"]: t for t in tasks}
    children_map: dict[str, list[str]] = {}
    roots: list[str] = []

    for t in tasks:
        pid = t.get("parentId")
        if pid:
            children_map.setdefault(pid, []).append(t["id"])
        else:
            roots.append(t["id"])

    def sort_key(tid):
        return task_map.get(tid, {}).get("order", 0) or 0

    roots.sort(key=sort_key)
    for pid in children_map:
        children_map[pid].sort(key=sort_key)

    result = []

    def traverse(tid: str, wbs_no: str, level: int, l1_name: str, l1_no: str):
        t = task_map.get(tid)
        if not t:
            return

        p_start = (t.get("startDate") or "")[:10]
        p_end = (t.get("endDate") or "")[:10]
        a_start = (t.get("actualStartDate") or "")[:10]
        a_end = (t.get("actualEndDate") or "")[:10]

        # 予定工数・実績工数（日数換算）
        p_days = ""
        if p_start and p_end:
            try:
                d = (date.fromisoformat(p_end) - date.fromisoformat(p_start)).days + 1
                p_days = d
            except Exception:
                pass

        a_days = ""
        if a_start and a_end:
            try:
                d = (date.fromisoformat(a_end) - date.fromisoformat(a_start)).days + 1
                a_days = d
            except Exception:
                pass

        overrun = ""
        if p_days and a_days and p_days > 0:
            pct = round((a_days - p_days) / p_days * 100, 1)
            overrun = f"{'+' if pct >= 0 else ''}{pct}%"

        result.append({
            "id": tid,
            "wbs_no": wbs_no,
            "l1": l1_no,
            "l2": wbs_no if level >= 2 else "",
            "level": level,
            "h1": l1_name,
            "h2": t["title"] if level >= 2 else "",
            "p_start": p_start,
            "p_end": p_end,
            "a_start": a_start,
            "a_end": a_end,
            "p_days": p_days,
            "a_days": a_days,
            "overrun": overrun,
            "status": STATUS_MAP.get(t.get("status", ""), t.get("status", "")),
            "progress": f"{t.get('progress', 0)}%",
            "deliverable": t.get("deliverable", "") or "",
            "notes": t.get("description", "") or "",
            "title": t["title"],
        })

        for j, cid in enumerate(children_map.get(tid, []), start=1):
            traverse(cid, f"{wbs_no}.{j}", level + 1, l1_name, l1_no)

    for i, rid in enumerate(roots, start=1):
        rt = task_map.get(rid)
        if rt:
            traverse(rid, str(i), 1, rt["title"], str(i))

    return result


# ── シート書き込み ─────────────────────────────────────────────────────────

def _col_letter(col_1based: int) -> str:
    return rowcol_to_a1(1, col_1based)[:-1]


def _write_wbs_sheet(
    spreadsheet: gspread.Spreadsheet,
    service,
    proj: dict,
):
    """1プロジェクト分のWBS + ガントチャートシートを作成・更新する。"""

    sheet_name = proj["title"][:28]
    try:
        ws = spreadsheet.worksheet(sheet_name)
        ws.clear()
        # 既存の条件付き書式を削除
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet.id,
            body={"requests": [{"deleteConditionalFormatRule": {
                "sheetId": ws.id, "index": 0
            }}]}
        ).execute()
    except Exception:
        try:
            ws = spreadsheet.add_worksheet(sheet_name, rows=500, cols=GANTT_START_COL + GANTT_DAYS + 5)
        except Exception:
            ws = spreadsheet.worksheet(sheet_name)
            ws.clear()

    tasks = proj.get("tasks", [])
    if not tasks:
        ws.update(values=[["タスクなし"]], range_name="A1")
        return

    rows = _build_wbs_rows(tasks)
    n = len(rows)
    today = date.today()

    # --- Row 1: プロジェクト名・表示開始日 ---
    gantt_start_date = today - timedelta(days=14)
    start_col_letter = _col_letter(COL["p_start"])  # H
    row1 = [""] * (GANTT_START_COL + 1)
    row1[1] = proj["title"]
    row1[COL["p_start"] - 1] = "表示開始日:"
    row1[COL["p_end"] - 1] = gantt_start_date.isoformat()

    # --- Row 3: 日付ヘッダー ---
    # S3 = 表示開始日（I1セル参照）、以降 +1
    date_header_row = [""] * (GANTT_START_COL - 1)
    date_header_row[COL["p_end"] - 1] = gantt_start_date.isoformat()  # I1として使用
    for i in range(GANTT_DAYS):
        d = gantt_start_date + timedelta(days=i)
        date_header_row.append(d.isoformat())

    # --- Row 4: 列ヘッダー ---
    col_headers = [
        "ID", "WBS No", "WBS_L1", "WBS_L2", "レベル",
        "階層1", "階層2",
        "予定開始", "予定終了", "実績開始", "実績終了",
        "予定工数(日)", "実績工数(日)", "超過率",
        "ステータス", "進捗", "成果物", "備考",
    ]
    # ガントヘッダー（曜日）
    for i in range(GANTT_DAYS):
        d = gantt_start_date + timedelta(days=i)
        col_headers.append(d.strftime("%m/%d"))

    # --- Row 5+: タスクデータ ---
    task_rows = []
    for row in rows:
        r = [
            row["id"], row["wbs_no"], row["l1"], row["l2"], row["level"],
            row["h1"], row["h2"],
            row["p_start"], row["p_end"], row["a_start"], row["a_end"],
            row["p_days"], row["a_days"], row["overrun"],
            row["status"], row["progress"], row["deliverable"], row["notes"],
        ] + [""] * GANTT_DAYS
        task_rows.append(r)

    # 一括書き込み
    all_data = [row1, [""] * len(col_headers), date_header_row, col_headers] + task_rows
    ws.update(values=all_data, range_name="A1")

    print(f"  [{sheet_name}] {n}タスク書き込み完了")

    # --- 書式設定 ---
    sheet_id = ws.id
    total_cols = GANTT_START_COL + GANTT_DAYS

    requests = []

    # ヘッダー行（Row4）の背景色
    requests.append({"repeatCell": {
        "range": {"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 4,
                  "startColumnIndex": 0, "endColumnIndex": COL["notes"]},
        "cell": {"userEnteredFormat": {
            "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "horizontalAlignment": "CENTER",
        }},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
    }})

    # プロジェクト名（Row1 B列）を太字に
    requests.append({"repeatCell": {
        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                  "startColumnIndex": 1, "endColumnIndex": 2},
        "cell": {"userEnteredFormat": {
            "textFormat": {"bold": True, "fontSize": 12},
        }},
        "fields": "userEnteredFormat(textFormat)",
    }})

    # ID列を非表示
    requests.append({"updateDimensionProperties": {
        "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                  "startIndex": 0, "endIndex": 1},
        "properties": {"hiddenByUser": True},
        "fields": "hiddenByUser",
    }})

    # ガントチャートヘッダー日付列の幅を小さく
    requests.append({"updateDimensionProperties": {
        "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                  "startIndex": GANTT_START_COL - 1, "endIndex": GANTT_START_COL + GANTT_DAYS},
        "properties": {"pixelSize": 28},
        "fields": "pixelSize",
    }})

    # タスク列の幅調整
    col_widths = [
        (1, 70),   # WBS No
        (5, 180),  # 階層1
        (6, 180),  # 階層2
        (7, 90),   # 予定開始
        (8, 90),   # 予定終了
        (9, 90),   # 実績開始
        (10, 90),  # 実績終了
        (14, 70),  # ステータス
        (15, 60),  # 進捗
    ]
    for col_0idx, width in col_widths:
        requests.append({"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                      "startIndex": col_0idx, "endIndex": col_0idx + 1},
            "properties": {"pixelSize": width},
            "fields": "pixelSize",
        }})

    # 先頭4行・先頭7列を固定
    requests.append({"updateSheetProperties": {
        "properties": {
            "sheetId": sheet_id,
            "gridProperties": {"frozenRowCount": 4, "frozenColumnCount": 7},
        },
        "fields": "gridProperties(frozenRowCount,frozenColumnCount)",
    }})

    # L1タスク行（level=1）を太字・薄背景
    for i, row in enumerate(rows):
        if row["level"] == 1:
            row_0 = DATA_START_ROW - 1 + i
            requests.append({"repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row_0, "endRowIndex": row_0 + 1,
                          "startColumnIndex": 0, "endColumnIndex": COL["notes"]},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.93, "green": 0.93, "blue": 0.97},
                    "textFormat": {"bold": True},
                }},
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }})

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet.id,
        body={"requests": requests}
    ).execute()

    # --- 条件付き書式（ガントチャート）---
    _apply_gantt_cf(service, spreadsheet.id, sheet_id, n)

    print(f"  [{sheet_name}] 書式設定完了")


def _apply_gantt_cf(service, spreadsheet_id: str, sheet_id: int, num_tasks: int):
    """ガントチャートの条件付き書式を適用する。"""
    g0 = GANTT_START_COL - 1   # 0-indexed開始列
    g_end = g0 + GANTT_DAYS
    d0 = DATA_START_ROW - 1    # 0-indexed データ開始行
    d_end = d0 + num_tasks

    gc_col = _col_letter(GANTT_START_COL)  # "S"
    H = _col_letter(COL["p_start"])        # "H" 予定開始
    I = _col_letter(COL["p_end"])          # "I" 予定終了
    J = _col_letter(COL["a_start"])        # "J" 実績開始
    K = _col_letter(COL["a_end"])          # "K" 実績終了
    r = DATA_START_ROW                     # 5

    data_range = {"sheetId": sheet_id, "startRowIndex": d0, "endRowIndex": d_end,
                  "startColumnIndex": g0, "endColumnIndex": g_end}
    head_range = {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 4,
                  "startColumnIndex": g0, "endColumnIndex": g_end}

    def cf_rule(formula: str, color: dict, cf_range: dict, index: int):
        return {"addConditionalFormatRule": {
            "rule": {
                "ranges": [cf_range],
                "booleanRule": {
                    "condition": {"type": "CUSTOM_FORMULA",
                                  "values": [{"userEnteredValue": formula}]},
                    "format": {"backgroundColor": color},
                }
            },
            "index": index,
        }}

    gray   = {"red": 0.85, "green": 0.85, "blue": 0.85}
    blue   = {"red": 0.40, "green": 0.65, "blue": 1.00}
    orange = {"red": 1.00, "green": 0.60, "blue": 0.20}
    yellow = {"red": 1.00, "green": 0.95, "blue": 0.40}
    lt_red = {"red": 1.00, "green": 0.88, "blue": 0.88}
    lt_blu = {"red": 0.88, "green": 0.93, "blue": 1.00}

    requests = [
        # データ行: 1. 予定バー（グレー）
        cf_rule(f"=AND(INT({gc_col}$3)>=INT(${H}{r}),INT({gc_col}$3)<=INT(${I}{r}),${H}{r}<>\"\")",
                gray, data_range, 0),
        # データ行: 2. 実績（予定内・青）
        cf_rule(f"=AND(INT({gc_col}$3)>=INT(${J}{r}),INT({gc_col}$3)<=INT(${K}{r}),OR(${I}{r}=\"\",INT({gc_col}$3)<=INT(${I}{r})),${J}{r}<>\"\")",
                blue, data_range, 1),
        # データ行: 3. 実績（超過・オレンジ）
        cf_rule(f"=AND(INT({gc_col}$3)>=INT(${J}{r}),INT({gc_col}$3)<=INT(${K}{r}),INT({gc_col}$3)>INT(${I}{r}),${J}{r}<>\"\",${I}{r}<>\"\")",
                orange, data_range, 2),
        # データ行: 4. 今日（黄色）
        cf_rule(f"=INT({gc_col}$3)=INT(TODAY())", yellow, data_range, 3),
        # ヘッダー行: 土曜（薄青）
        cf_rule(f"=WEEKDAY({gc_col}$3,2)=6", lt_blu, head_range, 4),
        # ヘッダー行: 日曜（薄赤）
        cf_rule(f"=WEEKDAY({gc_col}$3,2)=7", lt_red, head_range, 5),
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests}
    ).execute()


def _write_summary_sheet(
    spreadsheet: gspread.Spreadsheet,
    service,
    projects_data: list[dict],
):
    """サマリーシートを書き込む。"""
    try:
        ws = spreadsheet.worksheet("サマリー")
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet("サマリー", rows=100, cols=10)

    today = date.today()
    headers = ["プロジェクト", "タスク数", "完了数", "完了率", "期限切れ", "更新日"]
    rows = [headers]

    for proj in projects_data:
        tasks = proj.get("tasks", [])
        total = len(tasks)
        done = sum(1 for t in tasks if t.get("status") == "DONE")
        pct = round(done / total * 100, 1) if total else 0
        overdue = sum(
            1 for t in tasks
            if t.get("status") != "DONE"
            and t.get("endDate")
            and (t["endDate"] or "")[:10] < today.isoformat()
        )
        rows.append([
            proj["title"], total, done, f"{pct}%",
            overdue if overdue else "なし",
            today.isoformat(),
        ])

    ws.update(values=rows, range_name="A1")

    sheet_id = ws.id
    requests = [
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": 6},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }},
    ]

    # 期限切れ行を赤くする
    for i, proj in enumerate(projects_data, start=1):
        tasks = proj.get("tasks", [])
        overdue = sum(
            1 for t in tasks
            if t.get("status") != "DONE"
            and t.get("endDate")
            and (t["endDate"] or "")[:10] < today.isoformat()
        )
        if overdue > 0:
            requests.append({"repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": i, "endRowIndex": i + 1,
                          "startColumnIndex": 4, "endColumnIndex": 5},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.8},
                }},
                "fields": "userEnteredFormat(backgroundColor)",
            }})

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet.id,
        body={"requests": requests}
    ).execute()

    print(f"  サマリーシート更新: {len(projects_data)}プロジェクト")


# ── メイン ────────────────────────────────────────────────────────────────

def create_or_update_sheet(projects_data: list[dict]) -> str:
    """WBSシートを作成・更新してURLを返す。"""
    creds = _get_creds()
    gc = _get_gspread(creds)
    service = _get_sheets_service(creds)

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    if sheet_id:
        spreadsheet = gc.open_by_key(sheet_id)
        print(f"既存スプレッドシートを更新: {spreadsheet.url}")
    else:
        spreadsheet = gc.create(SHEET_TITLE)
        spreadsheet.share(None, perm_type="anyone", role="reader")
        new_id = spreadsheet.id
        print(f"新しいスプレッドシートを作成: {spreadsheet.url}")
        print(f"→ .env に追加: GOOGLE_SHEET_ID={new_id}")

    _write_summary_sheet(spreadsheet, service, projects_data)

    for proj in projects_data:
        if not proj.get("tasks"):
            continue
        _write_wbs_sheet(spreadsheet, service, proj)

    return spreadsheet.url


if __name__ == "__main__":
    import sys
    import requests as req
    sys.stdout.reconfigure(encoding="utf-8")

    url = os.getenv("SUPABASE_URL", "https://gzwiyylvthttvockugtf.supabase.co")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    r = req.get(f"{url}/rest/v1/projects?select=id,title,data", headers=headers, timeout=10)
    projects_raw = r.json()

    projects_data = [
        {"title": p["title"], "tasks": p.get("data") or []}
        for p in projects_raw
    ]

    print(f"プロジェクト数: {len(projects_data)}")
    sheet_url = create_or_update_sheet(projects_data)
    print(f"\n完了: {sheet_url}")
