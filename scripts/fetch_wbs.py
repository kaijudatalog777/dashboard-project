# fetch_wbs.py
# Supabase（WBS Generator）からWBSタスクデータを取得する
# 環境変数: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

import os
import requests
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gzwiyylvthttvockugtf.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }


def fetch_wbs_summary() -> dict:
    """WBSの進捗サマリーを返す。

    戻り値:
    {
        "projects": [{"id": ..., "title": ..., "tasks": [...]}],
        "total_tasks": int,
        "done_tasks": int,
        "overdue_tasks": [{"title": ..., "end_date": ..., "project": ...}],
        "today_tasks": [{"title": ..., "end_date": ..., "project": ...}],
        "category_progress": [{"name": ..., "total": int, "done": int, "pct": float}],
    }
    """
    if not SUPABASE_KEY:
        print("WARN: SUPABASE_SERVICE_ROLE_KEY が設定されていません")
        return _empty_summary()

    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/projects?select=id,title,data",
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        print(f"WARN: Supabaseへの接続に失敗しました: {e}")
        return _empty_summary()

    projects_raw = r.json()
    today = date.today()

    projects = []
    total_tasks = 0
    done_tasks = 0
    overdue_tasks = []
    today_tasks = []
    category_progress = []

    for proj in projects_raw:
        title = proj.get("title", "")
        tasks = proj.get("data") or []

        # 完了以外のタスクのみ集計（サブタスク含む全タスク）
        all_tasks = [t for t in tasks if isinstance(t, dict)]
        root_tasks = [t for t in all_tasks if not t.get("parentId")]

        proj_total = len(all_tasks)
        proj_done = sum(1 for t in all_tasks if t.get("status") == "DONE")

        total_tasks += proj_total
        done_tasks += proj_done

        # 期限切れ・今日期限タスク（未完了のみ）
        for t in all_tasks:
            if t.get("status") == "DONE":
                continue
            end_date_str = t.get("endDate", "")
            if not end_date_str:
                continue
            try:
                end_date = date.fromisoformat(end_date_str)
            except ValueError:
                continue

            task_info = {
                "title": t.get("title", ""),
                "end_date": end_date_str,
                "project": title,
            }
            if end_date < today:
                overdue_tasks.append(task_info)
            elif end_date == today:
                today_tasks.append(task_info)

        # 大分類別進捗（ルートタスクのみ）
        for rt in root_tasks:
            rt_id = rt.get("id")
            children = [t for t in all_tasks if t.get("parentId") == rt_id]
            if children:
                c_done = sum(1 for c in children if c.get("status") == "DONE")
                pct = round(c_done / len(children) * 100, 1)
                category_progress.append({
                    "name": rt.get("title", ""),
                    "project": title,
                    "total": len(children),
                    "done": c_done,
                    "pct": pct,
                })
            else:
                is_done = 1 if rt.get("status") == "DONE" else 0
                category_progress.append({
                    "name": rt.get("title", ""),
                    "project": title,
                    "total": 1,
                    "done": is_done,
                    "pct": 100.0 if is_done else 0.0,
                })

        projects.append({"id": proj.get("id"), "title": title, "task_count": proj_total})

    # 期限切れを日付順でソート
    overdue_tasks.sort(key=lambda x: x["end_date"])

    return {
        "projects": projects,
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "overdue_tasks": overdue_tasks,
        "today_tasks": today_tasks,
        "category_progress": category_progress,
    }


def _empty_summary() -> dict:
    return {
        "projects": [],
        "total_tasks": 0,
        "done_tasks": 0,
        "overdue_tasks": [],
        "today_tasks": [],
        "category_progress": [],
    }


if __name__ == "__main__":
    import json, sys
    sys.stdout.reconfigure(encoding="utf-8")
    summary = fetch_wbs_summary()
    total = summary["total_tasks"]
    done = summary["done_tasks"]
    pct = round(done / total * 100, 1) if total else 0
    print(f"総タスク: {total}  完了: {done}  完了率: {pct}%")
    print(f"期限切れ: {len(summary['overdue_tasks'])}件  今日期限: {len(summary['today_tasks'])}件")
    print("\n--- 大分類別進捗 ---")
    for c in summary["category_progress"][:10]:
        print(f"  [{c['project']}] {c['name']}  {c['pct']}% ({c['done']}/{c['total']})")
