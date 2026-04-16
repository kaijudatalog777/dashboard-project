# パーソナルダッシュボード 基本設計書

**文書バージョン:** 1.2  
**作成日:** 2026-04-12  
**更新日:** 2026-04-15  
**対象読者:** 非エンジニアの開発者本人

> **v1.1 変更点:** ダッシュボードの出力先をNotionに変更（メインプラン）。GitHub Pages案・ハイブリッド案をサブプランとして保持。  
> **v1.2 変更点:** 開発作業ログ・トラブルシューティング・次回タスクを追加。ハイブリッド案（案3）を当面の方針として採用。

---

## 目次

1. [プロジェクト概要](#1-プロジェクト概要)
2. [要件定義](#2-要件定義)
3. [システム基本設計](#3-システム基本設計)
4. [ファイル構成と役割](#4-ファイル構成と役割)
5. [データ設計](#5-データ設計)
6. [開発フェーズ計画](#6-開発フェーズ計画)
7. [環境構築手順](#7-環境構築手順)
8. [APIキー取得手順](#8-apiキー取得手順)
9. [ローカル開発・テスト手順](#9-ローカル開発テスト手順)
10. [GitHub公開・自動化手順](#10-github公開自動化手順)
11. [テスト計画](#11-テスト計画)
12. [運用・メンテナンス](#12-運用メンテナンス)
13. [用語集](#13-用語集)

---

## 1. プロジェクト概要

### 1-1. このシステムで何を実現するか

**毎朝6時に、1日のスタートに必要な情報をまとめたウェブページを自動生成する。**

人が何もしなくても、以下の情報が自動で1ページに集約される：

- 今日やるべきTODO・タスク管理（Notionから）
- 自分のコード作業履歴（GitHubから）
- 最近書いたメモ・ノート（Obsidianから ※Claude Codeと直接連携）
- 今日のニュース（RSSから）

各情報はGemini AI（Googleの生成AI）が日本語で要約してくれるため、忙しい朝でも素早く把握できる。

### 1-4. NotionとObsidianの役割分担

このシステムでは2つのツールを目的に応じて使い分ける。

| ツール | 役割 | 得意なこと |
|---|---|---|
| **Notion** | タスク・TODO管理のメインハブ | 締め切り・優先度・ステータス管理 |
| **Obsidian** | メモ・ノートのメインハブ | 自由な記述・Claude Codeと直接連携 |

#### Notionの活用イメージ

```
Notion（タスク管理）
├── TODO：今日やること・期限・優先度
├── プロジェクト管理：進行中の案件一覧
└── 習慣トラッカー：毎日のルーティン確認
         ↓ API経由で自動取得
    ダッシュボードに「今日のタスク」として表示
```

**具体的なシーン:**
- 朝、ダッシュボードを開くと「今日期限のTODOが3件」と表示される
- 優先度の高いタスクが上に並び、何から手をつけるか一目でわかる
- 進行中・未着手・期限切れをステータスで色分けして把握できる

#### Obsidianの活用イメージ

```
Obsidian（ノート管理）
├── 日報：今日やったこと・気づき
├── 学習メモ：勉強した内容・参考リンク
├── 議事録：会議の記録
├── アイデアノート：思いついたこと
└── 読書メモ：本・記事の要約
         ↓ ローカルファイルを直接読み込み（APIキー不要）
    ダッシュボードに「直近の思考・活動」として表示
```

**具体的なシーン:**
- 昨日書いた学習メモがAIに要約されて朝のダッシュボードに出る
- 「最近どんなことを考えていたか」が自動でまとめられる
- **Claude Codeが直接Obsidianのノートを読み書きできる**ため、AIとの対話内容をそのままノートに保存することも可能

#### 2ツールの連携イメージ

```
【朝のダッシュボード確認】
Notion → 「今日のTODO: 企画書提出・MTG準備・コードレビュー」
Obsidian → 「昨日の気づき: 新機能のアイデアをメモ済み」
           ↓
    1日の計画が5分で把握できる

【夜のふりかえり】
Obsidianに日報を書く
           ↓
    翌朝のダッシュボードに自動で要約が出る
```

### 1-2. 完成イメージ

```
┌─────────────────────────────────────────┐
│    パーソナルダッシュボード              │
│    生成日時: 2026年04月12日 06:00 JST   │
├─────────────────────────────────────────┤
│ TODO（Notion）                          │
│ ┌ AI要約: 今日は締め切りが3件あり... ┐  │
│ └──────────────────────────────────┘  │
│ [表] ステータス | タスク | 期限          │
├─────────────────────────────────────────┤
│ GitHub 直近コミット                     │
│ ┌ AI要約: 先週はAIチャットbot機能を... ┐│
│ └──────────────────────────────────┘  │
│ [表] 日時 | リポジトリ | コミット内容   │
├─────────────────────────────────────────┤
│ Obsidian 直近ノート                     │
│ ┌ AI要約: 学習ノートと読書メモが... ┐  │
│ └──────────────────────────────────┘  │
│ [一覧] ファイル名と更新日               │
├─────────────────────────────────────────┤
│ 今日のニュース                          │
│ ┌ AI要約: IT分野では...経済では... ┐   │
│ └──────────────────────────────────┘  │
│ [カテゴリ別リンク一覧]                  │
└─────────────────────────────────────────┘
```

### 1-3. 技術スタック（使う技術）

| 技術 | 役割 | 難易度 |
|---|---|---|
| **Python 3.11** | プログラム本体の言語 | 低（書かなくてよい） |
| **Gemini Flash API** | AI要約エンジン | 低（キー取得のみ） |
| **Notion API** | TODOデータ取得 ＋ ダッシュボード出力先 | 中（設定が必要） |
| **GitHub API** | コミット履歴取得 | 中（設定が必要） |
| **feedparser** | RSSニュース取得 | 低（URLを書くだけ） |
| **GitHub Actions** | 毎朝の自動実行 | 低（設定済み） |
| **GitHub Pages** | ウェブ公開（サブプランB・C用） | 低（設定のみ） |

---

## 2. 要件定義

### 2-1. 機能要件（必ずやること）

| # | 要件 | 優先度 |
|---|---|---|
| F-01 | 毎朝6時（JST）に自動でダッシュボードを生成する | 必須 |
| F-02 | NotionをTODO・タスク管理のメインハブとして未完了タスクを取得する | 必須 |
| F-03 | GitHubから直近7日分の自分のコミット履歴を取得する | 必須 |
| F-04 | ObsidianをメモのメインハブとしてVaultから直近7日以内に更新したノートを取得する（Claude Codeと直接連携・APIキー不要） | 必須 |
| F-05 | 設定したRSSフィードから最新記事を取得する | 必須 |
| F-06 | 収集した各データをGemini AIが日本語で要約する | 必須 |
| F-07 | 収集・要約したデータをNotionダッシュボードページに毎朝書き込む（メインプラン） | 必須 |
| F-08 | GitHub Actionsから手動で即時実行できる | 必須 |
| F-09 | 一部のデータ取得が失敗しても残りのデータは表示する | 必須 |
| F-10 | ObsidianのノートからタスクをNotionに自動作成する | フェーズ4 |
| F-11 | Claude Codeへの指示でNotionタスクのステータスを更新できる | フェーズ4 |
| F-12 | 完了タスクの記録をObsidianに自動書き戻しできる | フェーズ4 |
| F-13 | ダッシュボードに今週の完了タスク数・進行中タスク数を表示する | フェーズ4 |

### 2-2. 非機能要件（品質・制約）

| # | 要件 | 詳細 |
|---|---|---|
| N-01 | **セキュリティ** | APIキーはコードに直接書かず、環境変数で管理する |
| N-02 | **可用性** | 一部APIが落ちていてもダッシュボードは生成される |
| N-03 | **コスト** | Gemini APIの無料枠内で運用できる規模にする |
| N-04 | **保守性** | RSSフィードの追加・変更が設定1箇所で完結する |
| N-05 | **文字コード** | 全ファイルUTF-8（日本語が文字化けしない） |

### 2-3. 対象外（やらないこと）

- リアルタイム更新（毎朝1回のバッチ処理のみ）
- スマートフォン専用アプリの作成
- ユーザー認証・ログイン機能
- ObsidianデータのGitHub Actions上での取得（ローカルマシン専用・ローカル実行時のみ有効）
- NotionをObsidianの代替として使うこと（役割は明確に分離する）

### 2-4. ダッシュボード出力プラン（メイン＋サブ）

> イメージと異なる場合はサブプランに切り替えられる。

#### メインプラン A：Notionダッシュボード（採用中）

```
GitHub Actions
    ↓ 毎朝6時
Notion APIで「ダッシュボード」ページを更新
    ↓
Notionアプリ・ブラウザで確認
```

**メリット:** スマホアプリで快適・TODOを直接チェックできる・非公開  
**デメリット:** Notion APIへの書き込み設定がやや複雑

#### サブプラン B：ハイブリッド

```
GitHub Actions
    ├→ Notion APIでTODOセクションのみ更新
    └→ GitHub PagesにHTMLも出力
```

**メリット:** 両方使える・障害時のバックアップになる  
**デメリット:** 管理が2か所になる

#### サブプラン C：GitHub Pages（当初案）

```
GitHub Actions
    ↓ 毎朝6時
dashboard/index.htmlを生成
    ↓
GitHub Pagesで公開（URL共有可能）
```

**メリット:** シンプル・設定が簡単・URLで共有できる  
**デメリット:** Public公開・Notionアプリより使い勝手が落ちる

---

## 3. システム基本設計

### 3-1. 処理フロー

```
[毎朝6時 or 手動トリガー]
         │
         ▼
┌─────────────────┐
│ GitHub Actions  │  クラウド上の仮想マシンが起動
│  (ubuntu)       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  build_dashboard.py（メイン処理）                   │
│                                                     │
│  ① fetch_notion.py    → Notion API    → todos[]     │
│  ② fetch_github.py    → GitHub API   → commits[]   │
│  ③ fetch_obsidian.py  → ローカルファイル→ notes[]   │
│  ④ fetch_rss.py       → RSSフィード  → articles[]  │
│                                                     │
│  ⑤ summarize.py       → Gemini API   → 各要約文    │
│                                                     │
│  ⑥ _render_html()     → index.html 生成            │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  git push       │  dashboard/index.html をコミット
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GitHub Pages    │  ウェブで公開・閲覧可能に
└─────────────────┘
```

> **注意:** Obsidianのデータはローカルのファイルを読むため、GitHub Actions上では取得できません。
> ローカル実行時のみ有効です（GitHub Actions上では「データなし」と表示されます）。

### 3-2. エラー処理の方針

```
各fetch関数が失敗した場合
    └→ _safe_fetch() がエラーをキャッチ
         └→ WARNログを出力して空リスト[] を返す
              └→ 残りの処理は続行（ダッシュボードは生成される）
```

一部が失敗しても **ダッシュボード全体は生成される** 設計になっています。

### 3-3. 自動実行スケジュール

```yaml
cron: "0 21 * * *"   # UTC 21:00 = JST 翌06:00
```

GitHub ActionsはUTC（協定世界時）で動くため、JST（日本時間）より9時間ずれます。

---

## 4. ファイル構成と役割

```
Dashboard-project/
├── CLAUDE.md              # Claude Code用の指示書（編集不要）
├── DESIGN.md              # この設計書
├── .env                   # APIキー（Git管理外・絶対に公開しない）
├── .gitignore             # Gitに含めないファイルの設定
├── requirements.txt       # Pythonライブラリ一覧
│
├── scripts/               # Pythonスクリプト群
│   ├── build_dashboard.py # ★メイン。全体を統括して実行
│   ├── fetch_notion.py    # NotionからTODOを取得
│   ├── fetch_github.py    # GitHubからコミット履歴を取得
│   ├── fetch_obsidian.py  # Obsidianのノートを取得
│   ├── fetch_rss.py       # RSSニュースを取得（URLはここに書く）
│   └── summarize.py       # Gemini APIで各データを要約
│
├── dashboard/
│   └── index.html         # ★生成物。GitHub Pagesで公開されるページ
│
└── .github/workflows/
    └── daily.yml          # GitHub Actionsの自動実行設定
```

### 各ファイルの編集頻度

| ファイル | 編集タイミング |
|---|---|
| `fetch_rss.py` | RSSフィードを追加・変更したいとき |
| `build_dashboard.py` | デザインや表示内容を変えたいとき |
| `fetch_notion.py` | NotionのプロパティID/名前が変わったとき |
| `fetch_github.py` | 取得日数（FETCH_DAYS）を変えたいとき |
| `daily.yml` | 実行時刻を変えたいとき |
| `.env` | APIキーを更新するとき |

---

## 5. データ設計

各スクリプトが返すデータの形（Pythonのリスト）を定義します。

### 5-1. Notion TODO データ

```python
todos = [
    {
        "title": "企画書を提出する",   # タスク名
        "status": "In Progress",       # ステータス（Done以外）
        "due": "2026-04-15",           # 期限（なければ空文字）
    },
    ...
]
```

**Notionデータベースの必須プロパティ名：**

| プロパティ名 | 型 | 説明 |
|---|---|---|
| `Name` | タイトル | タスク名 |
| `Status` | ステータス | 進捗状態（"Done"以外を取得） |
| `Due` | 日付 | 期限 |
| `Priority` | セレクト等 | 優先度（降順でソート） |

### 5-2. GitHubコミット データ

```python
commits = [
    {
        "repo": "my-project",                    # リポジトリ名
        "message": "feat: ログイン機能を追加",   # コミットメッセージ1行目
        "date": "2026-04-11 20:30",              # 日時（JST）
        "url": "https://github.com/...",         # コミットURL
    },
    ...
]
```

### 5-3. Obsidianノート データ

```python
notes = [
    {
        "title": "2026-04-11 読書メモ",     # ファイル名（拡張子なし）
        "content": "# 読書メモ\n...",        # 内容（先頭2000文字）
        "modified": "2026-04-11 22:15",      # 最終更新日時
    },
    ...
]
```

### 5-4. RSSフィード データ

```python
articles = [
    {
        "label": "AI/IT",                        # カテゴリ名
        "title": "生成AIが○○分野に進出",         # 記事タイトル
        "summary": "記事の概要テキスト...",       # 記事概要（300文字以内）
        "link": "https://...",                   # 元記事URL
        "published": "2026-04-12 06:00",         # 公開日時
    },
    ...
]
```

---

## 6. 開発フェーズ計画

全体を4つのフェーズに分けて進めます。**現在、コードは全て作成済みです。** 残る作業は「設定」と「公開」です。

```
フェーズ1: 環境構築      ← 今ここ
フェーズ2: ローカルテスト
フェーズ3: GitHub公開・自動化
フェーズ4: カスタマイズ・改善
```

### フェーズ1: 環境構築（目安: 1〜2時間）

| # | タスク | 詳細 |
|---|---|---|
| 1-1 | Python 3.11 インストール確認 | `python --version` で確認 |
| 1-2 | 仮想環境の作成・有効化 | `python -m venv .venv` |
| 1-3 | ライブラリのインストール | `pip install -r requirements.txt` |
| 1-4 | Gemini APIキー取得 | Google AI Studioで発行 |
| 1-5 | .envファイル作成 | APIキーを記入 |

**完了基準:** `.env` に `GEMINI_API_KEY` が設定されている

### フェーズ2: ローカルテスト（目安: 1〜3時間）

| # | タスク | 詳細 |
|---|---|---|
| 2-1 | Gemini APIのみでテスト実行 | `python scripts/summarize.py` |
| 2-2 | RSSテスト実行 | `python scripts/fetch_rss.py` |
| 2-3 | Notion APIキー取得・設定 | .envに追記 |
| 2-4 | NotionテストDD | `python scripts/fetch_notion.py` |
| 2-5 | GitHub APIキー取得・設定 | .envに追記 |
| 2-6 | GitHubテスト実行 | `python scripts/fetch_github.py` |
| 2-7 | 全体テスト実行 | `python scripts/build_dashboard.py` |
| 2-8 | 生成HTMLをブラウザで確認 | `dashboard/index.html` を開く |

**完了基準:** `dashboard/index.html` が正常に開け、各セクションにデータが表示される

### フェーズ3: GitHub公開・自動化（目安: 1時間）

| # | タスク | 詳細 |
|---|---|---|
| 3-1 | GitHubリポジトリ作成 | Public設定で作成 |
| 3-2 | コードをGitHubにアップロード | git push |
| 3-3 | GitHub Secretsを設定 | APIキーをGitHubに登録 |
| 3-4 | GitHub Pagesを有効化 | /dashboardフォルダを公開 |
| 3-5 | GitHub Actionsを手動実行 | 正常に動くか確認 |
| 3-6 | 公開URLを確認 | ブラウザでアクセス |

**完了基準:** `https://ユーザー名.github.io/リポジトリ名/` でダッシュボードが表示される

### フェーズ4: カスタマイズ・改善（任意・随時）

| # | タスク | 詳細 |
|---|---|---|
| 4-1 | RSSフィードの追加・変更 | `fetch_rss.py` のURLリストを編集 |
| 4-2 | デザインの調整 | `build_dashboard.py` のCSSを編集 |
| 4-3 | Obsidian→Notionタスク自動作成 | F-10: ノートからタスク抽出スクリプトを追加 |
| 4-4 | Notionタスクのステータス管理 | F-11: Claude Code指示でステータス更新 |
| 4-5 | 完了タスクのObsidian書き戻し | F-12: タスク完了記録をノートに自動保存 |
| 4-6 | ダッシュボードに進捗サマリー追加 | F-13: 完了数・進行中タスク数を表示 |
| 4-7 | 天気予報の追加 | 無料APIで実現可能 |

---

## 7. 環境構築手順

### 7-1. Pythonのインストール確認

コマンドプロンプト（Windowsキー + R → `cmd` と入力）を開いて実行：

```bash
python --version
```

`Python 3.11.x` と表示されればOK。表示されない場合は以下からインストール：
- ダウンロード先: https://www.python.org/downloads/
- **必ず「Add Python to PATH」にチェックを入れてインストール**

### 7-2. プロジェクトフォルダに移動

```bash
cd C:\Users\shige\Desktop\Projects\Dashboard-project
```

### 7-3. Python仮想環境の作成

```bash
python -m venv .venv
```

> 仮想環境とは：このプロジェクト専用のPython実行環境。他のプロジェクトと干渉しない。

### 7-4. 仮想環境の有効化

```bash
.venv\Scripts\activate
```

プロンプトの先頭に `(.venv)` が付いたら成功。

> **毎回作業開始時にこのコマンドを実行してください。**  
> ウィンドウを閉じると無効化されます。

### 7-5. ライブラリのインストール

```bash
pip install -r requirements.txt
```

以下のライブラリがインストールされます：
- `google-generativeai` - Gemini AI
- `notion-client` - Notion API
- `PyGithub` - GitHub API
- `feedparser` - RSSフィード
- `python-dotenv` - .envファイル読み込み

### 7-6. .envファイルの作成

プロジェクトフォルダ直下に `.env` という名前のファイルを作成します。

**メモ帳で作成する場合:**
1. メモ帳を開く
2. 以下を貼り付け（APIキーは取得後に記入）
3. 「名前を付けて保存」→ ファイル名を `.env`、種類を「すべてのファイル」にして保存

```
GEMINI_API_KEY=ここに貼る
NOTION_API_KEY=ここに貼る
NOTION_DATABASE_ID=ここに貼る
GITHUB_TOKEN=ここに貼る
GITHUB_USERNAME=あなたのGitHubユーザー名
OBSIDIAN_VAULT_PATH=C:\Users\shige\Documents\ObsidianVault
```

---

## 8. APIキー取得手順

### 8-1. Gemini APIキー（最優先・必須）

1. https://aistudio.google.com/ を開く
2. Googleアカウントでログイン
3. 左メニュー「Get API key」をクリック
4. 「APIキーを作成」→ キーをコピー
5. `.env` の `GEMINI_API_KEY=` の後に貼り付け

> **無料枠について:** 個人利用であれば無料枠で十分です。1日1回の実行なら費用はかかりません。

### 8-2. Notion APIキー + データベースID

**ステップA: インテグレーションの作成**

1. https://www.notion.so/my-integrations を開く
2. 「新しいインテグレーション」をクリック
3. 名前: `dashboard`（任意）、ワークスペースを選択→「送信」
4. 表示される「インターナルインテグレーショントークン」をコピー
5. `.env` の `NOTION_API_KEY=` の後に貼り付け

**ステップB: NotionデータベースIDの取得**

1. Notionでダッシュボードに表示したいTODOデータベースを開く
2. ブラウザのURL（アドレスバー）を確認
   ```
   https://www.notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...
                          ↑ この32文字がデータベースID
   ```
3. この32文字を `.env` の `NOTION_DATABASE_ID=` の後に貼り付け

**ステップC: インテグレーションをデータベースに接続**

1. NotionのTODOデータベースページを開く
2. 右上の「...」（3点メニュー）をクリック
3. 「接続を追加」→ 作成した `dashboard` を選択
4. 「確認」

**ステップD: Notionデータベースのプロパティ確認**

`fetch_notion.py` は以下のプロパティ名を想定しています。  
Notionのデータベースのプロパティ名がこれと異なる場合は変更が必要です。

| 期待するプロパティ名 | 説明 |
|---|---|
| `Name` | タスク名（タイトル型） |
| `Status` | 進捗（ステータス型）※"Done"以外を取得 |
| `Due` | 期限（日付型） |
| `Priority` | 優先度（ソートに使用） |

### 8-3. GitHub Personal Access Token

1. https://github.com にログイン
2. 右上のアイコン → 「Settings」
3. 左メニューを一番下までスクロール → 「Developer settings」
4. 「Personal access tokens」→「Tokens (classic)」
5. 「Generate new token (classic)」
6. Note: `dashboard`（任意）
7. Expiration: 「No expiration」または任意の期間
8. Scopes: **`repo` にチェック**（これだけでOK）
9. 「Generate token」→ 表示されたトークンをコピー（**一度しか表示されない**）
10. `.env` の `GITHUB_TOKEN=` の後に貼り付け

---

## 9. ローカル開発・テスト手順

### 9-1. 個別スクリプトのテスト（推奨順）

問題が起きたときに原因を特定しやすくするため、個別に動作確認します。

**① Gemini APIのテスト**

```bash
python scripts/summarize.py
```

期待する出力:
```
Good morning.
```

**② RSSフィードのテスト（APIキー不要）**

```bash
python scripts/fetch_rss.py
```

期待する出力:
```
取得記事数: 25
  [AI/IT] 2026-04-12 05:00 〇〇の最新動向...
  [経済] ...
```

**③ Notionのテスト**

```bash
python scripts/fetch_notion.py
```

期待する出力:
```
取得件数: 5
  [In Progress] 企画書を提出する (期限: 2026-04-15)
  ...
```

**④ GitHubのテスト**

```bash
python scripts/fetch_github.py
```

期待する出力:
```
取得コミット数: 12
  [2026-04-11 20:30] my-project: feat: 新機能追加
  ...
```

**⑤ 全体テスト**

```bash
python scripts/build_dashboard.py
```

期待する出力:
```
=== ダッシュボード生成開始: 2026年04月12日 09:00 JST ===
Notion TODOを取得中...
GitHubコミットを取得中...
Obsidianノートを取得中...
RSSフィードを取得中...
Geminiで要約中...
index.html を生成中: ...dashboard\index.html
=== 生成完了 ===
```

### 9-2. 生成HTMLの確認

```bash
start dashboard/index.html
```

または、エクスプローラーで `dashboard/index.html` をダブルクリック。

### 9-3. よくあるエラーと対処法

| エラーメッセージ | 原因 | 対処 |
|---|---|---|
| `ModuleNotFoundError: No module named 'xxx'` | ライブラリ未インストール | `pip install -r requirements.txt` |
| `ERROR: GEMINI_API_KEY が設定されていません` | .envファイルがない or キーが空 | .envファイルの内容を確認 |
| `ERROR: NOTION_API_KEY が設定されていません` | .envにNOTION_API_KEYがない | .envに追記 |
| `ERROR: Notion APIの取得に失敗しました` | インテグレーション未接続 | 8-2のステップCを実施 |
| `WARN: [AI/IT] フィード取得に失敗` | RSSサイトが一時的に落ちている | しばらく待って再実行 |
| `(.venv)` が表示されない | 仮想環境が有効化されていない | `.venv\Scripts\activate` を実行 |

---

## 10. GitHub公開・自動化手順

### 10-1. Gitの初期設定（初回のみ）

コマンドプロンプトで実行（名前とメールはGitHubのものに合わせる）：

```bash
git config --global user.name "あなたの名前"
git config --global user.email "GitHubのメールアドレス"
```

### 10-2. GitHubリポジトリの作成

1. https://github.com にログイン
2. 右上「+」→「New repository」
3. Repository name: `dashboard-project`
4. **「Public」を選択**（GitHub PagesはPublicリポジトリが必要）
5. 「Initialize this repository」は**チェックしない**
6. 「Create repository」

### 10-3. コードをGitHubにアップロード

```bash
cd C:\Users\shige\Desktop\Projects\Dashboard-project
git init
git add CLAUDE.md DESIGN.md .gitignore requirements.txt
git add scripts/ dashboard/ .github/
git commit -m "first commit: パーソナルダッシュボード初期版"
git branch -M main
git remote add origin https://github.com/あなたのユーザー名/dashboard-project.git
git push -u origin main
```

> **注意:** `.env` はアップロードしません（`.gitignore` で除外済み）

### 10-4. GitHub Secretsの設定

GitHubはクラウドで動くため、手元の `.env` ファイルが読めません。
代わりに「Secrets（秘密の設定値）」としてGitHub上に登録します。

1. GitHubのリポジトリページを開く
2. 「Settings」タブ → 左メニュー「Secrets and variables」→「Actions」
3. 「New repository secret」で以下を1つずつ追加：

| Secret名 | 設定する値 |
|---|---|
| `GEMINI_API_KEY` | GeminiのAPIキー |
| `NOTION_API_KEY` | NotionのAPIキー |
| `NOTION_DATABASE_ID` | NotionのデータベースID |
| `GITHUB_TOKEN` | GitHubのPersonal Access Token |
| `GITHUB_USERNAME` | あなたのGitHubユーザー名 |

### 10-5. GitHub Pagesの設定

1. リポジトリの「Settings」タブ
2. 左メニューの「Pages」をクリック
3. Source: **「Deploy from a branch」**
4. Branch: `main`、フォルダ: **`/dashboard`**
5. 「Save」

数分後、以下のURLでダッシュボードが公開されます：
```
https://あなたのユーザー名.github.io/dashboard-project/
```

### 10-6. GitHub Actionsの手動テスト実行

1. リポジトリの「Actions」タブ
2. 左メニュー「Daily Dashboard Build」をクリック
3. 「Run workflow」→「Run workflow」
4. 実行が完了（緑のチェックマーク）したことを確認
5. 公開URLにアクセスして表示を確認

---

## 11. テスト計画

### 11-1. テストの種類と目的

| テスト種別 | 目的 | 実施タイミング |
|---|---|---|
| **単体テスト** | 各スクリプトが単独で動くか確認 | フェーズ2 |
| **結合テスト** | 全体を繋いで動くか確認 | フェーズ2完了後 |
| **受け入れテスト** | GitHub Actions + Pagesで正しく公開されるか確認 | フェーズ3完了後 |

### 11-2. テストチェックリスト

**単体テスト（フェーズ2）**

- [ ] `python scripts/summarize.py` が日本語の出力を返す
- [ ] `python scripts/fetch_rss.py` が記事を1件以上取得する
- [ ] `python scripts/fetch_notion.py` がTODOを取得する（またはエラー内容が明確）
- [ ] `python scripts/fetch_github.py` がコミットを取得する

**結合テスト（フェーズ2）**

- [ ] `python scripts/build_dashboard.py` がエラーなく完了する
- [ ] `dashboard/index.html` が生成される
- [ ] ブラウザで開いてTODOセクションが表示される
- [ ] ブラウザで開いてニュースセクションが表示される
- [ ] AI要約が日本語で表示される

**受け入れテスト（フェーズ3）**

- [ ] GitHub Actionsの手動実行が成功（緑のチェック）する
- [ ] 公開URL（github.io）でダッシュボードが表示される
- [ ] 翌朝6時以降に自動で更新されていることを確認

### 11-3. データなしのテスト

一部のAPIキーを設定せずに実行した場合でも、ダッシュボードが生成されることを確認します。

```bash
# .envのNOTION_API_KEYを一時的にコメントアウト（行頭に#を追加）
# NOTION_API_KEY=xxx
python scripts/build_dashboard.py
```

期待する動作:
```
WARN: Notion TODO の取得をスキップしました
```
→ その他のセクションは正常に表示される

---

## 12. 運用・メンテナンス

### 12-1. 日常的な操作

| したいこと | 操作 |
|---|---|
| 今すぐダッシュボードを更新したい | GitHub Actions → 手動実行（10-6参照） |
| ローカルで確認したい | `python scripts/build_dashboard.py` → `start dashboard/index.html` |

### 12-2. よくあるカスタマイズ

**RSSフィードを追加・変更する**

`scripts/fetch_rss.py` を開き、`RSS_SOURCES` リストを編集：

```python
RSS_SOURCES = [
    {"label": "AI/IT",  "url": "https://..."},   # ← URLとラベルを変更
    {"label": "経済",   "url": "https://..."},
    # ↓ 新しいフィードを追加
    {"label": "スポーツ", "url": "https://..."},
]
```

**取得日数を変更する**

- GitHubコミット: `scripts/fetch_github.py` の `FETCH_DAYS = 7` を変更
- Obsidianノート: `scripts/fetch_obsidian.py` の `FETCH_DAYS = 7` を変更

**自動実行の時刻を変更する**

`.github/workflows/daily.yml` の `cron:` を変更：

```yaml
# 変換表: JST = UTC + 9時間 → JSTの時刻から9を引いてUTCに変換
- cron: "0 21 * * *"   # UTC 21:00 = JST 06:00（現在の設定）
- cron: "0 22 * * *"   # UTC 22:00 = JST 07:00
- cron: "0 23 * * *"   # UTC 23:00 = JST 08:00
```

### 12-3. APIキーの更新

APIキーの有効期限が切れた場合：

1. 新しいキーを取得（各サービスのサイトで）
2. ローカル: `.env` ファイルを更新
3. クラウド: GitHub Secretsを更新（Settings → Secrets → 該当キーをクリック → Update）

### 12-4. コードを変更してGitHubに反映する方法

ファイルを編集した後：

```bash
cd C:\Users\shige\Desktop\Projects\Dashboard-project
.venv\Scripts\activate
git add scripts/fetch_rss.py          # 変更したファイルを指定
git commit -m "RSSにスポーツを追加"   # 変更内容を一言で
git push
```

---

## 13. 用語集

| 用語 | 意味 |
|---|---|
| **API** | 外部サービス（Notion、GitHubなど）とやり取りする窓口。APIキーはその入館証。 |
| **APIキー** | APIを使う権限を示す長い文字列。パスワードのように扱う（公開しない）。 |
| **Git** | ファイルの変更履歴を管理するツール。 |
| **GitHub** | Gitのリポジトリをクラウドで管理・公開できるサービス。 |
| **GitHub Actions** | GitHubが提供する自動実行機能。スケジュール実行や条件付き実行ができる。 |
| **GitHub Pages** | GitHubのリポジトリの内容をウェブサイトとして公開できる機能（無料）。 |
| **Gemini API** | GoogleのAI（Gemini）をプログラムから呼び出すAPI。 |
| **RSS** | ウェブサイトの新着情報を自動で配信する仕組み。 |
| **仮想環境（venv）** | Pythonのライブラリをプロジェクトごとに独立して管理する仕組み。 |
| **.env** | 環境変数（APIキーなど）を書いたファイル。Gitには含めない。 |
| **環境変数** | プログラムに渡す設定値。コードに直接書かずに外から渡すことでセキュリティを保つ。 |
| **cron** | 定期実行スケジュールを表す書き方。`0 21 * * *` = 毎日21:00など。 |
| **UTC / JST** | UTC＝協定世界時、JST＝日本時間（UTC+9時間）。 |
| **Obsidian Vault** | Obsidianアプリでノートが保存されているフォルダ。 |
| **Remote Control** | 自宅PCで動いているClaude Codeに、外出先のスマホ・ブラウザから接続して開発作業を継続できる機能。自宅PCのターミナルで `/remote-control` を実行するとQRコードまたはURLが発行され、同じAnthropicアカウントでログインしたスマホアプリ（claude.ai）から接続できる。ファイル内容の確認や編集結果の表示はスマホアプリの方が全て見えるため、外出先での作業はスマホアプリでの接続が推奨。自宅PCは起動したまま・Claude Codeが動いている状態を維持する必要がある。 |

---

*このドキュメントは開発の進行に合わせて随時更新してください。*

---

## 14. 開発作業ログ・トラブルシューティング

### 14-1. フェーズ1〜2 作業ログ（2026-04-12〜2026-04-15）

#### Gemini API関連

| 問題 | 原因 | 解決策 |
|---|---|---|
| `google.generativeai` が動作しない | ライブラリが廃止された | `google-genai` に変更（requirements.txtも更新済み） |
| モデル `gemini-1.5-flash` が見つからない | 旧モデル名 | `gemini-flash-latest` に変更 |
| クォータエラー（limit: 0） | Google Cloudプロジェクトに請求先アカウント未設定 | Google Cloudで請求先アカウントをリンク（無料枠内で課金なし） |
| APIキーをチャットに貼り付けてしまった | 誤操作 | 即座に無効化して新しいキーを発行すること |

#### Notion API関連

| 問題 | 原因 | 解決策 |
|---|---|---|
| `'DatabasesEndpoint' object has no attribute 'query'` | notion-client 3.0.0はquery非対応 | `notion-client==2.2.1` に固定（requirements.txtも更新済み） |
| 新しいNotionデータベースに接続できない | Notionの新形式（inline+data_sources）がAPI非対応 | 従来形式のデータベースを使用する |
| データベースID末尾に `?v=...` が混入 | URLをそのままコピーした | `?v=` 以降を除いた32文字のみを使用する |
| データベースIDが「ページ」と判定される | 親ページのIDをコピーしていた | データベースを「↗」で単体ページとして開いてからURLをコピー |
| `Could not find property with name: Status` | Notionのプロパティ名が設計と異なる | 実際のプロパティ名に合わせてコードを修正 |

#### 実際のNotionデータベース プロパティ名（案C対応済み）

| プロパティ名 | 型 | コード上の対応 |
|---|---|---|
| `Memo` | タイトル | タスク名 |
| `ステータス` | status | 進捗（未着手・進行中・完了・保留） |
| `期限` | date | 締め切り |
| `緊急度` | multi_select | 高・中・低 |
| `プロジェクト` | multi_select | 所属プロジェクト |
| `タグ` | multi_select | 分類タグ |
| `出所` | multi_select | タスクの発生源 |
| `完了日` | date | 実際の完了日 |
| `メモ` | rich_text | 補足説明 |
| `Done` | checkbox | 完了フラグ |

#### GitHub API関連

| 問題 | 原因 | 解決策 |
|---|---|---|
| 404エラー | GitHubユーザー名のタイポ（`aijudatalog777`） | 正しいユーザー名 `kaijudatalog777` に修正 |

#### 方針変更

| 変更内容 | 変更前 | 変更後 | 理由 |
|---|---|---|---|
| ダッシュボード出力先 | GitHub Pagesのみ | **ハイブリッド（HTML＋Notion）** | スマホ対応・プライバシー・利便性 |
| Geminiライブラリ | google-generativeai | **google-genai** | ライブラリ廃止 |
| Geminiモデル | gemini-1.5-flash | **gemini-flash-latest** | モデル廃止 |
| notion-clientバージョン | 最新（3.0.0） | **2.2.1固定** | 3.0.0はquery非対応 |

---

## 15. 次回タスク（フェーズ3〜）

### ✅ フェーズ3 GitHub公開・自動化（2026-04-15 完了）

| # | タスク | 状態 |
|---|---|---|
| 3-1 | GitHubリポジトリ作成 | 完了 |
| 3-2 | コードをGitHubにpush | 完了 |
| 3-3 | GitHub Secretsの設定 | 完了（GITHUB_TOKEN→MY_GITHUB_TOKEN、GITHUB_USERNAME→MY_GITHUB_USERNAME） |
| 3-4 | GitHub Pagesの有効化 | 完了（/docsフォルダ使用・/dashboardは不可だったため変更） |
| 3-5 | GitHub Actionsの手動実行 | 完了（Success・48秒） |
| 3-6 | 公開URL確認 | 完了 https://kaijudatalog777.github.io/dashboard-project/ |

**2026-04-15 追加変更:**
- RSSソース変更: 子育て・旧労務URLを削除、ビジネス（東洋経済）・産業化学（日刊工業新聞）・科学エネルギー（サイエンスポータル）を追加
- 出力先を `dashboard/` から `docs/` に変更（GitHub Pages仕様に合わせる）
- `GITHUB_TOKEN` → `MY_GITHUB_TOKEN`、`GITHUB_USERNAME` → `MY_GITHUB_USERNAME` に変更（GitHubの予約語制限のため）

### ✅ Notionダッシュボード実装（2026-04-16 完了）

| # | タスク | 状態 |
|---|---|---|
| N-1 | Notionダッシュボードページ作成 | 完了（ページID: 343955a112ce803089bfea8d32761f1c） |
| N-2 | `write_notion_dashboard.py` 作成 | 完了 |
| N-3 | `build_dashboard.py` にNotion書き込み追加 | 完了 |
| N-4 | Notionページにインテグレーション接続 | 完了（ワークスペース側で新規作成） |
| N-5 | ハイブリッド動作確認 | 完了（HTML＋Notion両方書き込み確認済み） |
| N-6 | GitHub Secretsに `NOTION_DASHBOARD_PAGE_ID` 追加 | 完了 |

**2026-04-16 実装内容:**
- `write_notion_dashboard.py` 新規作成（Notionページへの書き込み処理）
- `build_dashboard.py` にNotion書き込み処理を追加（HTML生成と並行して実行）
- Gemini API 503エラー時の自動リトライ機能追加（最大3回・10秒間隔）
- データベースビュー（DB_TODO）を削除しないよう修正（`child_database` ブロックは保持）
- `daily.yml` に `NOTION_DASHBOARD_PAGE_ID` 環境変数を追加
- GitHub Actionsで動作確認済み（Success・2分31秒）

**Notionダッシュボードの現在の構成:**
```
DB_TODO（リンクドビュー・手動設置・位置固定）
生成日時
TODO AI要約
区切り線
GitHub コミット AI要約 + リスト
区切り線
Obsidian ノート AI要約 + リスト
区切り線
今日のニュース AI要約 + カテゴリ別リスト
```

**仕様上の制約:**
- DB_TODOは常にページ先頭になる（Notion APIの仕様・ブロック挿入位置の制限）
- Obsidianデータは GitHub Actions 上では取得不可（ローカル実行時のみ）

---

### 🔄 次: フェーズ4 タスクライフサイクル管理

| # | タスク | 詳細 | 状態 |
|---|---|---|---|
| **4-1** | **ObsidianノートからNotionタスク自動作成** | **ノートを書いたら「タスク化して」と指示 → Claude Codeが抽出・登録** | **次回実装予定** |
| 4-2 | Notionタスクのステータス管理 | Claude Code指示でステータス更新 | 未着手 |
| 4-3 | 完了タスクのObsidian書き戻し | タスク完了記録をノートに保存 | 未着手 |

### トラブルシューティング追記（2026-04-15〜16）

| 問題 | 原因 | 解決策 |
|---|---|---|
| GitHub Secretsに `GITHUB_USERNAME` が登録できない | `GITHUB_` で始まる名前はGitHubの予約語 | `MY_GITHUB_USERNAME` に変更 |
| GitHub Pagesで `/dashboard` フォルダが選択できない | GitHub Pagesは `/(root)` か `/docs` のみ対応 | 出力先を `docs/` に変更 |
| git pushが拒否される | GitHub Actionsが先にpushしていた | `git pull --rebase` してからpush |
| Notionページに「接続を追加」が表示されない | ページがプライベート設定のため | ワークスペース側で新規ページを作成 |
| API Error 500 | Anthropic/ClaudeのAPIサーバーの一時障害 | しばらく待って再実行（こちら側の問題なし） |
| Gemini API 503エラーが頻発 | APIサーバーの混雑（朝の時間帯に多い） | 自動リトライ機能を実装（最大3回） |
| ダッシュボード更新でDB_TODOが消える | `_clear_page` が全ブロック削除していた | `child_database` タイプは削除しないよう修正 |
| DB_TODOが常にページ先頭になる | Notion APIはブロックの追記のみ対応（挿入位置指定不可） | 仕様として受け入れ。AI要約はDB_TODOの下に表示 |
