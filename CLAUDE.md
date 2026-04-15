# パーソナルダッシュボード プロジェクト

## 概要
毎朝6時にGitHub Actionsで自動実行するダッシュボード生成システム。
各情報ソースを収集→Gemini APIで要約→GitHub PagesにHTML出力する。

## 技術スタック
- Python 3.11
- Gemini Flash API（google-generativeai ライブラリ）
- Notion API（notion-client ライブラリ）
- GitHub API（PyGithub ライブラリ）
- feedparser（RSS取得）
- GitHub Actions（自動化）
- GitHub Pages（ホスティング）

## 実行方法
```
python scripts/build_dashboard.py
```

## コーディング規約
- 全スクリプトはutf-8、コメントは日本語OK
- エラーは握りつぶさずprint+sys.exitで明示
- .envはpython-dotenvで読み込む
- Geminiへのプロンプトは日本語で、出力も日本語

## 環境変数（.envから読む）
- GEMINI_API_KEY    : Google AI Studioで取得
- NOTION_API_KEY   : Notion Integration Tokenで取得
- GITHUB_TOKEN     : GitHub Personal Access Tokenで取得

## ディレクトリ構成
```
dashboard-project/
├── CLAUDE.md
├── .env                    # Git管理外
├── .gitignore
├── requirements.txt
├── scripts/
│   ├── fetch_notion.py
│   ├── fetch_github.py
│   ├── fetch_obsidian.py
│   ├── fetch_rss.py
│   ├── summarize.py
│   └── build_dashboard.py
├── dashboard/
│   └── index.html
└── .github/workflows/
    └── daily.yml
```
