# mantela-prober
東京広域電話網の Mantela 到達性を監視するためのリポジトリです。

このリポジトリでは、次の Mantela ドキュメントに含まれる providers 配列を 1 時間ごとに監視します。

- https://unstable.kusaremkn.com/.well-known/mantela.json

## 動作

- providers 配列内の各 provider エントリを個別に監視します。
- mantela URL が空の provider は、Mantela を使っていないものとして監視対象外にします。
- mantela URL が不正、到達不能、または有効な JSON を返さない場合は不通とみなします。
- 現在不通の provider 一覧は unreachable.json に保存します。
- 以前 unreachable.json に記録されておらず、新たに不通になった provider だけを Discord Webhook に通知します。
- 復旧した provider は unreachable.json から削除します。

## GitHub Actions

ワークフローは [.github/workflows/mantela-prober.yml](.github/workflows/mantela-prober.yml) にあります。実行タイミングは次のとおりです。

- 1 時間ごとの定期実行
- workflow_dispatch による手動実行

ワークフローは実行結果に応じて unreachable.json を更新し、その差分をリポジトリへ push します。これにより、次回実行時に新規不通だけを判定できます。

## 必要な Secret

リポジトリの Secret に次を設定してください。

- DISCORD_WEBHOOK_URL: 新規不通の通知先となる Discord Incoming Webhook URL

## ローカル実行

ローカルで確認する場合は次を実行します。

```bash
python scripts/check_mantela_providers.py
```

必要に応じて、以下の環境変数を指定できます。

- MANTELA_SOURCE_URL
- UNREACHABLE_FILE
- DISCORD_WEBHOOK_URL
- REQUEST_TIMEOUT_SECONDS
