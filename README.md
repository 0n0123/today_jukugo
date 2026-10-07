# 今日の熟語

毎日ひとつ、日本語の熟語を意味と用例から学ぶ静的Webページです。

日付に応じて熟語を選び、GitHub Actionsがページを生成してGitHub Pagesへ公開します。候補を使い切るまでは同じ熟語を繰り返しません。

熟語は2〜4文字の漢字から成る名詞・形容詞・サ変動詞です。定義と用例は同じ語義のデータを使い、対象の熟語を含む用例がある語だけを候補にします。サ変動詞は「する」を付けた形で表示します。

## データ

辞書データには[日本語 WordNet 1.1](https://bond-lab.github.io/wnja/jpn/index.html)を使用しています。公開ページには出典へのリンクを表示し、軽量化したデータベースとともに[ライセンス](data/LICENSE.txt)を同梱しています。

元データの`wnjpn.db`はサイズが大きいためリポジトリには含めません。軽量データベース`data/idioms.sqlite3`を再作成する場合は、配布元から原本を取得してから抽出します。

```sh
curl -L https://github.com/bond-lab/wnja/releases/download/v1.1/wnjpn.db.gz | gunzip > wnjpn.db
python3 -m pip install -r requirements.txt
python3 scripts/prepare_dictionary.py
```

生成した`data/idioms.sqlite3`はリポジトリに含めます。原本の`wnjpn.db`は`.gitignore`で除外されています。
読みは`pykakasi`でかなに変換して保存します。語義によって読みが異なる場合があるため、必要に応じて生成したデータを確認してください。

## ローカル実行

Python 3.9以降を使います。ページは次のコマンドで生成できます。

```sh
python3 scripts/generate_site.py
```

特定の日付を指定して再現する場合:

```sh
python3 scripts/generate_site.py --date 2026-10-07
```

ページは`public/index.html`に出力されます。ページ生成には外部Pythonパッケージは必要ありません。`pykakasi`は辞書データの作成時だけ使います。

## GitHub Pages

GitHubリポジトリの **Settings > Pages > Build and deployment > Source** を **GitHub Actions** に設定します。`.github/workflows/pages.yml`が毎日日本時間0時ごろにページを生成して公開します。初回公開や動作確認にはActions画面から **Build and deploy daily idiom** を手動実行できます。GitHubのスケジュール実行には遅延が生じる場合があります。

## ライセンス

日本語 WordNetの著作権表示とライセンス条件は[data/LICENSE.txt](data/LICENSE.txt)を参照してください。日本語 WordNetの利用条件に従い、公開ページに出典リンクを掲載しています。
