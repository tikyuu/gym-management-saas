# API設計書

## 共通パス

業務APIの共通パスは`/api/v1`とする。

## ヘルスチェック

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/health` | ALBがECSタスクの正常性を確認する | 不要 |

正常時はHTTPステータス`200`と、次のJSONを返す。

```json
{
  "status": "ok"
}
```

## ログイン利用者情報の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/me` | ログイン中の利用者のアプリ内情報を取得する | Cognitoアクセストークン |

レスポンスには、画面種別の判断に使用する`user_type`を含める。

| 値 | 意味 |
| --- | --- |
| `member` | 会員 |
| `staff` | ジム事業者側のスタッフ |
| `system_admin` | SaaS運営管理者 |

`user_type`が`staff`の場合は、`roles`にスタッフの役割と対象店舗を配列で含める。

| `role`の値 | 対象店舗 |
| --- | --- |
| `organization_admin` | 指定しない。事業者全体が対象 |
| `store_admin` | `store_id`で指定する |
| `trainer` | `store_id`で指定する |

`/me`はログイン直後の画面遷移と操作権限の判断に必要な最小限の情報だけを返す。電話番号、生年月日、契約情報などのプロフィール詳細は、用途別のAPIで取得する。

### 正常時のレスポンス

会員の場合:

```json
{
  "user_type": "member",
  "display_name": "山田 太郎"
}
```

スタッフの場合:

```json
{
  "user_type": "staff",
  "display_name": "山田 花子",
  "roles": [
    {
      "role": "trainer",
      "store_id": "store_001"
    }
  ]
}
```

SaaS運営管理者の場合:

```json
{
  "user_type": "system_admin",
  "display_name": "運営管理者"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 | クライアント側の扱い |
| --- | --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 | ログイン画面へ戻す |
| `403 Forbidden` | Cognitoでは認証済みだが、アプリケーション側で利用停止 | 利用できない旨を表示する |
