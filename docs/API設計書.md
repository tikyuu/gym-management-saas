# API設計書

## 共通パス

業務APIの共通パスは`/api/v1`とする。

追加APIのリクエスト・レスポンスと認可条件も、この設計書に記載する。事業者IDは原則として認証済みの所属情報から決め、管理者向けAPIのリクエストから任意の事業者IDを信頼しない。

## API一覧

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/health` | ECSタスクの正常性を確認する | 不要 |
| `GET` | `/api/v1/me` | ログイン利用者の種別と操作権限を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/members/me` | 会員自身のプロフィールを取得する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/members/me` | 会員自身のプロフィールを更新する | Cognitoアクセストークン |
| `GET` | `/api/v1/stores` | 会員が予約できる店舗候補を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/stores/{store_id}/menus` | 選択店舗で予約できるメニュー候補を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/stores/{store_id}/availability` | 選択した店舗・メニューの予約可能時間を取得する | Cognitoアクセストークン |
| `POST` | `/api/v1/reservations` | 会員の予約を作成する | Cognitoアクセストークン |
| `GET` | `/api/v1/members/me/reservations` | 会員自身の予約一覧を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/members/me/reservations/{reservation_id}` | 会員自身の予約詳細を取得する | Cognitoアクセストークン |
| `POST` | `/api/v1/reservations/{reservation_id}/cancel` | 会員自身の予約をキャンセルする | Cognitoアクセストークン |
| `GET` | `/api/v1/members/me/contracts` | 会員自身の契約内容と利用状況を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/staff` | 管理者が権限範囲内のスタッフ一覧を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/staff/{staff_id}` | 管理者が権限範囲内のスタッフ詳細を取得する | Cognitoアクセストークン |
| `POST` | `/api/v1/staff` | 管理者が権限範囲内のスタッフを招待する | Cognitoアクセストークン |
| `POST` | `/api/v1/staff/{staff_id}/deactivate` | 管理者が権限範囲内のスタッフを利用停止にする | Cognitoアクセストークン |
| `POST` | `/api/v1/staff/{staff_id}/organization-admin-role` | 事業者管理者が事業者管理者役割を付与する | Cognitoアクセストークン |
| `POST` | `/api/v1/staff/{staff_id}/store-memberships` | 管理者が権限範囲内の店舗所属を追加する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/staff/{staff_id}/store-memberships/{membership_id}/roles` | 管理者が権限範囲内の店舗内役割を変更する | Cognitoアクセストークン |
| `POST` | `/api/v1/staff/{staff_id}/store-memberships/{membership_id}/deactivate` | 管理者が権限範囲内の店舗所属を終了する | Cognitoアクセストークン |
| `POST` | `/api/v1/staff/me/activate` | 招待されたスタッフが初回ログイン後に利用を開始する | Cognitoアクセストークン |
| `GET` | `/api/v1/staff/me/reservations` | スタッフが権限範囲内の予約一覧を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/staff/me/reservations/{reservation_id}` | スタッフが権限範囲内の予約詳細を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/staff/me/work-shifts` | スタッフ自身の勤務予定を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/work-shifts` | 管理者が権限範囲内の勤務予定を取得する | Cognitoアクセストークン |
| `POST` | `/api/v1/work-shifts` | 管理者・本人が権限範囲内の勤務予定を登録する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/work-shifts/{shift_id}` | 管理者・本人が勤務予定の日時を変更する | Cognitoアクセストークン |
| `POST` | `/api/v1/work-shifts/{shift_id}/cancel` | 管理者・本人が勤務予定を取消する | Cognitoアクセストークン |
| `POST` | `/api/v1/work-shifts/{shift_id}/unavailable-periods` | スタッフが勤務予定内の予約不可時間を登録する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/work-shifts/{shift_id}/unavailable-periods/{unavailable_period_id}` | スタッフが予約不可時間を変更する | Cognitoアクセストークン |
| `DELETE` | `/api/v1/work-shifts/{shift_id}/unavailable-periods/{unavailable_period_id}` | スタッフが予約不可時間を削除する | Cognitoアクセストークン |
| `POST` | `/api/v1/reservations/{reservation_id}/reassign-trainer` | 管理者が予約の担当トレーナーを変更する | Cognitoアクセストークン |
| `POST` | `/api/v1/staff/me/reservations/{reservation_id}/complete` | スタッフが予約を来店完了にする | Cognitoアクセストークン |
| `POST` | `/api/v1/staff/me/reservations/{reservation_id}/no-show` | スタッフが予約を無断欠席にする | Cognitoアクセストークン |
| `GET` | `/api/v1/staff/me` | スタッフ自身のプロフィールと操作範囲を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/system-admin/me` | SaaS運営管理者自身の情報を取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/system-admin/organizations` | 登録済み事業者を検索する | Cognitoアクセストークン |
| `POST` | `/api/v1/system-admin/organizations` | 契約済み事業者を登録する | Cognitoアクセストークン |
| `GET` | `/api/v1/system-admin/organizations/{organization_id}` | 事業者の設定と状態を取得する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/system-admin/organizations/{organization_id}/status` | 事業者の利用状態を変更する | Cognitoアクセストークン |
| `POST` | `/api/v1/system-admin/organizations/{organization_id}/initial-admin` | 最初の事業者管理者を招待する | Cognitoアクセストークン |
| `POST` | `/api/v1/system-admin/organizations/{organization_id}/recover-admin` | 本人確認後に事業者管理者の利用を復旧する | Cognitoアクセストークン |
| `GET` | `/api/v1/management/stores` | 管理対象店舗を取得する | Cognitoアクセストークン |
| `POST` | `/api/v1/management/stores` | 店舗を登録する | Cognitoアクセストークン |
| `GET` | `/api/v1/management/stores/{store_id}` | 店舗の設定を取得する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/management/stores/{store_id}` | 店舗の基本設定を更新する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/management/stores/{store_id}/status` | 店舗の状態を変更する | Cognitoアクセストークン |
| `PUT` | `/api/v1/management/stores/{store_id}/regular-hours` | 通常営業時間をまとめて設定する | Cognitoアクセストークン |
| `PUT` | `/api/v1/management/stores/{store_id}/special-days/{date}` | 特定日の営業設定を保存する | Cognitoアクセストークン |
| `DELETE` | `/api/v1/management/stores/{store_id}/special-days/{date}` | 特定日の設定を解除する | Cognitoアクセストークン |
| `GET` | `/api/v1/management/menus` | 管理対象メニューを取得する | Cognitoアクセストークン |
| `POST` | `/api/v1/management/menus` | メニューを登録する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/management/menus/{menu_id}` | メニューの内容・状態を変更する | Cognitoアクセストークン |
| `PUT` | `/api/v1/management/stores/{store_id}/menus/{menu_id}` | 店舗のメニュー提供状態を設定する | Cognitoアクセストークン |
| `PUT` | `/api/v1/management/staff/{staff_id}/store-memberships/{membership_id}/menus/{menu_id}` | トレーナーの担当メニューを設定する | Cognitoアクセストークン |
| `GET` | `/api/v1/plans` | 会員が申し込めるプランを取得する | Cognitoアクセストークン |
| `GET` | `/api/v1/management/plans` | 管理対象プランを取得する | Cognitoアクセストークン |
| `POST` | `/api/v1/management/plans` | プランを登録する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/management/plans/{plan_id}` | プランの条件・状態を変更する | Cognitoアクセストークン |
| `PUT` | `/api/v1/management/plans/{plan_id}/stores/{store_id}` | プランの利用可能店舗を設定する | Cognitoアクセストークン |
| `PUT` | `/api/v1/management/plans/{plan_id}/menus/{menu_id}` | プランの利用可能メニューを設定する | Cognitoアクセストークン |
| `POST` | `/api/v1/members/me/contracts` | 会員がプランへ申し込む | Cognitoアクセストークン |
| `GET` | `/api/v1/management/contracts` | 管理対象の契約申込み・契約を検索する | Cognitoアクセストークン |
| `GET` | `/api/v1/management/contracts/{contract_id}` | 契約の内容・状態・履歴を取得する | Cognitoアクセストークン |
| `POST` | `/api/v1/management/contracts/{contract_id}/approve` | 申込みを承認する | Cognitoアクセストークン |
| `POST` | `/api/v1/management/contracts/{contract_id}/reject` | 申込みを理由付きで拒否する | Cognitoアクセストークン |
| `POST` | `/api/v1/management/contracts/{contract_id}/pause` | 契約を一時停止する | Cognitoアクセストークン |
| `POST` | `/api/v1/management/contracts/{contract_id}/resume` | 契約を再開する | Cognitoアクセストークン |
| `POST` | `/api/v1/management/contracts/{contract_id}/terminate` | 契約を終了する | Cognitoアクセストークン |
| `POST` | `/api/v1/management/contracts/{contract_id}/adjustments` | 契約期限・利用回数を理由付きで調整する | Cognitoアクセストークン |
| `POST` | `/api/v1/members/me/registration` | メール確認済み会員のプロフィールを作成する | Cognitoアクセストークン |
| `GET` | `/api/v1/management/members` | 管理対象会員を検索する | Cognitoアクセストークン |
| `GET` | `/api/v1/management/members/{member_id}` | 管理対象会員の詳細を取得する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/management/members/{member_id}` | 理由付きで会員プロフィールを訂正する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/management/members/{member_id}/status` | 会員の利用停止・再開を行う | Cognitoアクセストークン |
| `POST` | `/api/v1/members/me/withdraw` | 会員が事業者から退会する | Cognitoアクセストークン |
| `POST` | `/api/v1/members/me/rejoin` | 退会した会員が再入会する | Cognitoアクセストークン |
| `POST` | `/api/v1/members/me/account-deletion` | 会員がサービスアカウント削除を申請する | Cognitoアクセストークン |
| `POST` | `/api/v1/staff/{staff_id}/reactivate` | 事業者管理者がスタッフを再雇用する | Cognitoアクセストークン |
| `DELETE` | `/api/v1/staff/{staff_id}/organization-admin-role` | 事業者管理者役割を解除する | Cognitoアクセストークン |
| `POST` | `/api/v1/work-shifts/bulk` | 権限範囲内の勤務予定を一括登録する | Cognitoアクセストークン |
| `POST` | `/api/v1/staff/me/reservations/{reservation_id}/cancel` | スタッフが店舗都合で予約を取消す | Cognitoアクセストークン |
| `POST` | `/api/v1/management/reservations/{reservation_id}/correct-status` | 管理者が誤った予約状態を訂正する | Cognitoアクセストークン |
| `GET` | `/api/v1/system-admin/reservations` | SaaS運営管理者が調査対象予約を確認する | Cognitoアクセストークン |

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
| `403 Forbidden` | ログインアカウント自体が無効化・削除申請中 | 利用できない旨を表示する |

会員が`suspended`または`withdrawn`であっても、`/me`と本人の過去の契約・予約の取得は許可する。新しい申込みと予約は業務APIで拒否する。

## 会員プロフィール

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/members/me` | ログイン中の会員自身のプロフィールを取得する | Cognitoアクセストークン |
| `PATCH` | `/api/v1/members/me` | ログイン中の会員自身のプロフィールを更新する | Cognitoアクセストークン |

会員ホームからプロフィール画面を開いたときに、`GET`を呼び出す。`PATCH`では会員自身が編集できる項目だけを更新する。

### 取得・更新成功時のレスポンス

`GET`と、成功した`PATCH`は同じ形式で返す。

```json
{
  "id": "member_001",
  "member_number": "M000001",
  "status": "active",
  "name": "山田 太郎",
  "name_kana": "ヤマダ タロウ",
  "phone_number": "09012345678",
  "birth_date": "1995-04-01",
  "organization": {
    "id": "org_001",
    "name": "サンプルジム"
  }
}
```

### 更新リクエスト

```json
{
  "name": "山田 太郎",
  "name_kana": "ヤマダ タロウ",
  "phone_number": "09012345678",
  "birth_date": "1995-04-01"
}
```

生年月日は会員自身が任意で更新できる。所属事業者は会員自身では変更できない。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 会員以外が呼び出した、またはログインアカウントが無効化されている |
| `422 Unprocessable Content` | 氏名、フリガナまたは電話番号の形式が不正 |

## スタッフプロフィール

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/staff/me` | ログイン中のスタッフ自身のプロフィールと操作範囲を取得する | Cognitoアクセストークン |

スタッフ用画面を開くときに呼び出す。スタッフの氏名、所属事業者、役割および操作できる店舗を返す。

```json
{
  "id": "staff_001",
  "name": "山田 花子",
  "organization": {
    "id": "org_001",
    "name": "サンプルジム"
  },
  "roles": [
    {
      "role": "trainer",
      "store": {
        "id": "store_001",
        "name": "渋谷店"
      }
    }
  ]
}
```

スタッフ自身によるプロフィール更新はPhase 1の対象外とする。氏名、所属事業者、役割および店舗所属は、事業者管理者が管理する情報であるためとする。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | スタッフが招待中または利用停止中 |
| `404 Not Found` | 認証済みだが、対応するスタッフプロフィールが見つからない |

## 管理者向けスタッフ一覧の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/staff` | ログイン中の管理者が、権限範囲内のスタッフ一覧を取得する | Cognitoアクセストークン |

勤務予定の登録画面などで、対象スタッフを選択するときに呼び出す。店舗管理者は担当店舗に有効所属するスタッフ、事業者管理者は事業者内のスタッフを取得できる。トレーナーは呼び出せない。

| クエリパラメータ | 必須 | 意味 |
| --- | --- | --- |
| `store_id` | いいえ | 対象店舗。指定すると、その店舗に有効所属するスタッフだけを返す |
| `status` | いいえ | `active`、`invited`または`inactive`。指定しない場合は`active` |

```json
{
  "items": [
    {
      "id": "staff_001",
      "name": "佐藤 花子",
      "status": "active",
      "stores": [
        {
          "id": "store_001",
          "name": "渋谷店",
          "roles": ["trainer"]
        }
      ]
    }
  ]
}
```

勤務予定の登録候補として使用する場合は、`status=active`かつ選択店舗に有効所属するスタッフだけを選択できる。メールアドレス、電話番号、Cognitoの識別子など、一覧表示に不要な情報は返さない。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 店舗管理者・事業者管理者ではない、または有効な役割・店舗所属がない |
| `404 Not Found` | 指定した店舗が存在しない、または担当範囲外 |
| `422 Unprocessable Content` | `status`の値が不正 |

## 管理者向けスタッフ詳細の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/staff/{staff_id}` | ログイン中の管理者が、権限範囲内のスタッフ詳細を取得する | Cognitoアクセストークン |

スタッフ一覧から1人を選択したときに呼び出す。事業者管理者は事業者内のスタッフの全所属・役割を取得できる。店舗管理者は担当店舗に所属するスタッフだけを取得でき、返す所属・役割も担当店舗分に限定する。トレーナーは呼び出せない。

```json
{
  "id": "staff_001",
  "name": "佐藤 花子",
  "status": "active",
  "stores": [
    {
      "id": "store_001",
      "name": "渋谷店",
      "membership_status": "active",
      "roles": ["trainer"]
    }
  ]
}
```

スタッフのメールアドレス、電話番号、Cognitoの識別子および他店舗の情報は返さない。`invited`、`active`および`inactive`のスタッフを取得できる。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 店舗管理者・事業者管理者ではない、または有効な役割・店舗所属がない |
| `404 Not Found` | 指定したスタッフが存在しない、または担当範囲外 |

## スタッフの店舗所属追加

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/staff/{staff_id}/store-memberships` | 管理者が権限範囲内の店舗所属と役割を追加する | Cognitoアクセストークン |

事業者管理者は同一事業者のスタッフを追加所属させられる。店舗管理者は担当店舗のトレーナーを追加所属させられるが、管理者役割を持つスタッフの所属や`store_admin`の付与は扱えない。対象スタッフは`invited`または`active`に限る。トレーナーは呼び出せない。

### リクエスト

```json
{
  "store_id": "store_002",
  "roles": ["trainer"]
}
```

`roles`には`trainer`または`store_admin`を1件以上指定する。`organization_admin`は店舗に紐づかないため、このAPIでは指定できない。FastAPIは店舗所属と役割付与を同じトランザクションで作成する。

### 成功時のレスポンス

HTTPステータス`201 Created`で、追加した店舗所属を返す。

```json
{
  "id": "staff_store_membership_002",
  "store": {
    "id": "store_002",
    "name": "新宿店"
  },
  "status": "active",
  "roles": ["trainer"]
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 事業者管理者でも担当店舗の店舗管理者でもない、または役割・店舗が操作範囲外 |
| `404 Not Found` | 指定したスタッフまたは店舗が存在しない、または同一事業者に属さない |
| `409 Conflict` | 対象スタッフが`inactive`、または指定店舗へすでに有効所属している |
| `422 Unprocessable Content` | `roles`が空、重複、または指定できない役割を含む |

## スタッフの店舗内役割変更

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PATCH` | `/api/v1/staff/{staff_id}/store-memberships/{membership_id}/roles` | 管理者が権限範囲内の店舗内役割を変更する | Cognitoアクセストークン |

事業者管理者は同一事業者の店舗内役割を変更できる。店舗管理者は担当店舗のトレーナー役割だけを変更でき、管理者役割の付与・解除はできない。対象スタッフと`membership_id`の店舗所属が一致し、所属状態が`active`であることを確認する。トレーナーは呼び出せない。

### リクエスト

```json
{
  "roles": ["trainer", "store_admin"]
}
```

`roles`には、変更後に有効としたい`trainer`または`store_admin`を1件以上指定する。`organization_admin`は店舗に紐づかないため、このAPIでは指定できない。

FastAPIは、リクエストにない現在の有効役割を`inactive`へ変更して`revoked_at`を記録する。新たに指定された役割は作成または再び`active`にする。役割の変更履歴を残すため、既存の役割行を物理削除しない。

### 成功時のレスポンス

HTTPステータス`200 OK`で、変更後に有効な役割を返す。

```json
{
  "membership_id": "staff_store_membership_001",
  "roles": ["trainer", "store_admin"]
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 事業者管理者でも担当店舗の店舗管理者でもない、または管理者役割が操作対象に含まれる |
| `404 Not Found` | 指定したスタッフまたは店舗所属が存在しない、または一致しない |
| `409 Conflict` | 対象スタッフまたは店舗所属が`inactive` |
| `422 Unprocessable Content` | `roles`が空、重複、または指定できない役割を含む |

## スタッフの店舗所属終了

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/staff/{staff_id}/store-memberships/{membership_id}/deactivate` | 管理者が権限範囲内の店舗所属を終了する | Cognitoアクセストークン |

異動や特定店舗からの退職時に呼び出す。スタッフ全体のログインは維持し、対象店舗への所属だけを終了する。事業者管理者は同一事業者の所属を終了できる。店舗管理者は担当店舗のトレーナーの所属だけを終了でき、店舗管理者役割を持つスタッフは対象外とする。

対象店舗所属に紐づく将来の`scheduled`勤務予定を取消し、対象店舗で担当する将来の`confirmed`予約を別トレーナーへ変更またはキャンセルしてから実行する。未対応の勤務予定または予約が残る場合、FastAPIは所属終了を実行しない。

所属状態を`inactive`へ変更して`ended_at`を記録する。同じ店舗所属に紐づく有効な`trainer`・`store_admin`役割も`inactive`へ変更して`revoked_at`を記録する。所属・役割の過去履歴は物理削除しない。

### 成功時のレスポンス

HTTPステータス`200 OK`で、終了後の所属状態を返す。すでに`inactive`の所属へ再実行しても、状態は変更せず成功として扱う。

```json
{
  "id": "staff_store_membership_001",
  "status": "inactive",
  "ended_at": "2026-10-01T12:00:00+09:00"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 事業者管理者でも担当店舗の店舗管理者でもない、または管理者役割が操作対象に含まれる |
| `404 Not Found` | 指定したスタッフまたは店舗所属が存在しない、または一致しない |
| `409 Conflict` | 将来の勤務予定または`confirmed`予約が残っている |

## 事業者管理者役割の付与

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/staff/{staff_id}/organization-admin-role` | ログイン中の事業者管理者が、同一事業者のスタッフへ事業者管理者役割を付与する | Cognitoアクセストークン |

事業者管理者だけが呼び出せる。対象スタッフは同一事業者に所属する`invited`または`active`のスタッフに限定する。店舗管理者とトレーナーは呼び出せない。リクエスト本文は受け取らない。

`organization_admin`は店舗に紐づかない役割であるため、店舗所属を作成・変更しない。すでに有効な`organization_admin`を持つスタッフへ再実行しても、状態は変更せず成功として扱う。

### 成功時のレスポンス

HTTPステータス`201 Created`で、付与した役割を返す。すでに有効な役割を持つ場合は`200 OK`で同じ内容を返す。

```json
{
  "staff_id": "staff_001",
  "role": "organization_admin",
  "status": "active"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 事業者管理者ではない、または有効な役割がない |
| `404 Not Found` | 指定したスタッフが存在しない、または同一事業者に属さない |
| `409 Conflict` | 対象スタッフが`inactive` |

## スタッフの利用停止

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/staff/{staff_id}/deactivate` | 管理者が権限範囲内のスタッフを利用停止にする | Cognitoアクセストークン |

退職や利用停止時に呼び出す。事業者管理者は同一事業者のスタッフを停止できる。店舗管理者は、担当店舗のみに所属し管理者役割を持たないトレーナーを停止できる。複数店舗に所属するトレーナーについて店舗管理者が終了できるのは自身の担当店舗の所属だけであり、スタッフ全体は停止できない。リクエスト本文は受け取らない。対象スタッフを物理削除せず、`inactive`へ変更して過去の勤務・予約・操作履歴を保持する。

利用停止前に、対象スタッフの将来の`scheduled`勤務予定を取消し、将来の`confirmed`予約を別スタッフへ変更またはキャンセルする。これらが残る場合、FastAPIは利用停止を実行しない。事業者内に`active`な`organization_admin`を最低1人残す。

条件を満たす場合、FastAPIはCognitoのスタッフ用User Poolで対象ユーザーを無効化し、`staff.status`、有効な店舗所属と役割を`inactive`へ変更する。所属終了日時と役割解除日時も記録する。Cognito側の無効化に失敗した場合は、データベースの状態を変更しない。Cognito無効化後のDB更新失敗には再試行または補償処理が必要であり、処理結果を監査・アラート対象にする。

### 成功時のレスポンス

HTTPステータス`200 OK`で、利用停止後の状態を返す。すでに`inactive`のスタッフへ再実行しても、状態は変更せず成功として扱う。

```json
{
  "id": "staff_001",
  "status": "inactive"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 事業者管理者でも対象トレーナーの担当店舗管理者でもない、または停止対象が操作範囲外 |
| `404 Not Found` | 指定したスタッフが存在しない、または同一事業者に属さない |
| `409 Conflict` | 将来の勤務予定または`confirmed`予約が残っている、または最後の有効な事業者管理者である |
| `503 Service Unavailable` | Cognitoのユーザー無効化に失敗した |

## 予約担当トレーナーの変更

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/reservations/{reservation_id}/reassign-trainer` | ログイン中の管理者が、将来の予約の担当トレーナーを変更する | Cognitoアクセストークン |

スタッフの退職や勤務予定変更などにより、将来の予約を別トレーナーへ引き継ぐときに呼び出す。店舗管理者は担当店舗、事業者管理者は事業者内の予約を変更できる。トレーナーは呼び出せない。

### リクエスト

```json
{
  "staff_id": "staff_002"
}
```

予約の店舗・メニュー・開始終了時刻は変更せず、担当トレーナーだけを変更する。対象は開始時刻より前の`confirmed`予約だけとする。

FastAPIは、新しい担当者が予約店舗へ有効所属し、対象メニューを担当可能であり、予約時間を完全に含む勤務予定を持つことを確認する。さらに、予約不可時間および他の`confirmed`予約と重ならないことを、トランザクション内で再確認する。

### 成功時のレスポンス

HTTPステータス`200 OK`で、変更後の担当トレーナーを返す。

```json
{
  "id": "reservation_001",
  "trainer": {
    "id": "staff_002",
    "name": "鈴木 一郎"
  }
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 店舗管理者・事業者管理者ではない、または対象予約が権限範囲外 |
| `404 Not Found` | 指定した予約または新しい担当スタッフが存在しない、または利用対象外 |
| `409 Conflict` | 予約が`confirmed`ではない、開始時刻以降、または新しい担当者の勤務予定・予約不可時間・既存予約と重複する |

## スタッフの招待

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/staff` | 管理者が権限範囲内のスタッフを招待する | Cognitoアクセストークン |

事業者管理者は同一事業者のスタッフを招待できる。店舗管理者は担当店舗の`trainer`だけを招待でき、`store_admin`または`organization_admin`の付与や担当外店舗の指定はできない。トレーナーは呼び出せない。新しいスタッフは、招待時点では`invited`とする。

### リクエスト

```json
{
  "name": "佐藤 花子",
  "email": "sato@example.com",
  "roles": [
    {
      "role": "trainer",
      "store_id": "store_001"
    }
  ]
}
```

`roles`には1件以上を指定する。`trainer`と`store_admin`では`store_id`が必須、`organization_admin`では`store_id`を指定しない。同じスタッフへ複数の店舗・役割を指定できる。ただし店舗管理者が招待する場合は、自身の担当店舗の`trainer`1役割に限定する。FastAPIは店舗に紐づく役割から店舗所属を作成し、同じ店舗に複数の役割を指定した場合でも店舗所属は1件だけ作成する。

### 処理内容

FastAPIはCognitoのスタッフ用User Poolへ招待ユーザーを作成し、Cognitoが指定メールアドレスへ初回ログイン用の招待メールを送る。Cognitoが発行した`sub`を使って`user_accounts`、`staff`、店舗所属および役割を登録する。

Cognitoのユーザー作成後にデータベース登録が失敗した場合は、作成したCognitoユーザーを削除する補償処理を行う。補償処理にも失敗した場合はエラーログ・アラームの対象とし、運用で確認して解消する。

### 成功時のレスポンス

HTTPステータス`201 Created`で、招待したスタッフを返す。

```json
{
  "id": "staff_001",
  "name": "佐藤 花子",
  "status": "invited",
  "roles": [
    {
      "role": "trainer",
      "store_id": "store_001"
    }
  ]
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 事業者管理者でも担当店舗の店舗管理者でもない、または指定した役割・店舗が操作範囲外 |
| `404 Not Found` | 指定した店舗が存在しない、または同一事業者に属さない |
| `409 Conflict` | 同じメールアドレスのスタッフ用Cognitoユーザー、または有効な招待が存在する |
| `422 Unprocessable Content` | 氏名・メールアドレス・役割の形式が不正、または役割と`store_id`の組み合わせが不正 |
| `503 Service Unavailable` | Cognitoへの招待ユーザー作成またはメール送信に失敗した |

## 招待済みスタッフの利用開始

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/staff/me/activate` | 初回ログインを完了した招待済みスタッフが、自身の利用を開始する | Cognitoアクセストークン |

Cognitoの招待メールから初回ログインとパスワード設定を完了した直後に、Reactが1回だけ呼び出す。リクエスト本文は受け取らない。アクセストークン内のUser Pool IDと`sub`から、対象スタッフを特定する。

対象スタッフの状態が`invited`であることを確認し、`active`へ変更する。すでに`active`のスタッフが再実行しても、状態は変更せず成功として扱う。これにより、通信失敗後にReactが再送しても安全に処理できる。

### 成功時のレスポンス

HTTPステータス`200 OK`で、利用開始後の状態を返す。

```json
{
  "id": "staff_001",
  "status": "active"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | スタッフアカウントが`inactive`である |
| `404 Not Found` | アクセストークンに対応するスタッフプロフィールが存在しない |

## SaaS運営管理者プロフィール

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/system-admin/me` | ログイン中のSaaS運営管理者自身の情報を取得する | Cognitoアクセストークン |

SaaS運営画面を開くときに呼び出す。SaaS運営管理者は事業者・店舗に所属しないため、氏名だけを返す。

```json
{
  "id": "system_admin_001",
  "name": "運営管理者"
}
```

SaaS運営管理者自身のプロフィール更新はPhase 1の対象外とする。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | SaaS運営管理者アカウントが利用停止中 |
| `404 Not Found` | 認証済みだが、対応するSaaS運営管理者プロフィールが見つからない |

## 予約可能店舗の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/stores` | ログイン中の会員が予約できる店舗候補を取得する | Cognitoアクセストークン |

会員が予約画面を開いたときに呼び出す。所属事業者と店舗がともに`active`であり、会員の有効な契約プランで利用可能な店舗だけを返す。

```json
[
  {
    "id": "store_001",
    "name": "渋谷店",
    "address": "東京都渋谷区..."
  },
  {
    "id": "store_002",
    "name": "新宿店",
    "address": "東京都新宿区..."
  }
]
```

電話番号、営業時間および空き時間は含めない。店舗を選択した後に、それぞれの用途に対応するAPIから取得する。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 会員以外が呼び出した |

予約可能な店舗がない場合は、`200 OK`で空配列`[]`を返す。

## 予約可能メニューの取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/stores/{store_id}/menus` | 選択した店舗で予約できるメニュー候補を取得する | Cognitoアクセストークン |

会員が予約画面で店舗を選択した後に呼び出す。店舗、メニューおよび店舗でのメニュー提供設定がすべて`active`であり、会員の有効な契約プランで利用可能なメニューだけを返す。契約を持たない会員による都度払い予約および体験トレーニングは、Phase 1の対象外とする。

```json
[
  {
    "id": "menu_001",
    "name": "パーソナルトレーニング 60分",
    "description": "筋力向上を目的とした個別トレーニングです。",
    "duration_minutes": 60
  }
]
```

料金は含めない。料金はメニューではなく会員の契約プランで決まるためとする。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 会員以外が呼び出した |
| `404 Not Found` | 指定した店舗が存在しない、または会員が利用できない |

利用可能な店舗だが予約可能なメニューがない場合は、`200 OK`で空配列`[]`を返す。

## 予約可能時間の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/stores/{store_id}/availability` | 選択した店舗・メニュー・日付の予約可能時間を取得する | Cognitoアクセストークン |

会員が予約画面で店舗とメニューを選択し、予約日を指定した後に呼び出す。

| クエリパラメータ | 必須 | 意味 |
| --- | --- | --- |
| `menu_id` | はい | 選択したメニューのID |
| `date` | はい | 空きを確認する日付。`YYYY-MM-DD`形式 |
| `trainer_id` | いいえ | 指名するトレーナーのID。指定しない場合は指名なし予約 |

店舗営業時間、特定日設定、メニュー所要時間、予約開始間隔、トレーナー勤務予定、予約不可時間および既存予約をもとに算出する。指名なしの場合は、担当可能なトレーナーが1人以上空いている時間だけを返す。

```json
{
  "date": "2026-10-10",
  "slots": [
    {
      "starts_at": "2026-10-10T10:00:00+09:00",
      "ends_at": "2026-10-10T11:00:00+09:00"
    },
    {
      "starts_at": "2026-10-10T11:30:00+09:00",
      "ends_at": "2026-10-10T12:30:00+09:00"
    }
  ]
}
```

会員は返された候補から1つの時間帯を選ぶ。空き日時の表示後に別の予約が確定する可能性があるため、予約作成時に改めて予約可能か確認する。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 会員以外が呼び出した |
| `404 Not Found` | 店舗または指名トレーナーが存在しない、または会員が利用できない |

指定日の予約可能時間がない場合は、`200 OK`で`slots`を空配列`[]`として返す。

## 予約の作成

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/reservations` | ログイン中の会員の予約を作成する | Cognitoアクセストークン |

### リクエスト

```json
{
  "store_id": "store_001",
  "menu_id": "menu_001",
  "starts_at": "2026-10-10T10:00:00+09:00",
  "trainer_id": "staff_001"
}
```

`trainer_id`は指名予約の場合だけ指定する。指名なし予約では指定せず、予約作成時にFastAPIが担当可能なトレーナーを1人確保する。

会員ID、契約IDおよび終了時刻は、リクエストから受け取らずにFastAPIが決定する。会員の有効な契約、プランで利用可能な店舗・メニュー、店舗営業時間、トレーナー勤務予定、予約不可時間および既存予約を、作成直前のDBの状態で再確認する。

利用回数制プランでは、予約の作成と同じトランザクションで利用回数を1回分確保する。通い放題プランでは利用回数を確保しない。

### 成功時のレスポンス

HTTPステータス`201 Created`で、作成した予約を返す。

```json
{
  "id": "reservation_001",
  "status": "confirmed",
  "store": {
    "id": "store_001",
    "name": "渋谷店"
  },
  "menu": {
    "id": "menu_001",
    "name": "パーソナルトレーニング 60分"
  },
  "starts_at": "2026-10-10T10:00:00+09:00",
  "ends_at": "2026-10-10T11:00:00+09:00",
  "trainer": {
    "id": "staff_001",
    "name": "山田 花子"
  }
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 会員が利用停止中、または契約が利用できない |
| `404 Not Found` | 店舗、メニューまたは指名トレーナーが存在しない、または利用対象外 |
| `409 Conflict` | 空き枠が埋まった、利用回数が不足したなど、最新状態では予約を作成できない |
| `422 Unprocessable Content` | 日時形式など、リクエスト内容の形式が不正 |

## 会員予約一覧の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/members/me/reservations` | ログイン中の会員自身の予約一覧を取得する | Cognitoアクセストークン |

会員ホームから予約一覧画面を開いたときに呼び出す。画面内の「今後の予約」「過去の予約」タブに応じて`scope`を指定する。

| クエリパラメータ | 必須 | 意味 |
| --- | --- | --- |
| `scope` | いいえ | `upcoming`または`past`。省略時は`upcoming` |
| `limit` | いいえ | 1回に取得する件数。省略時は`20` |
| `cursor` | いいえ | 前回レスポンスの`next_cursor`。次のページを取得するときに指定する |

`upcoming`では、開始時刻が現在より後で`confirmed`の予約を返す。`past`では、開始済み、`completed`、`no_show`または`cancelled`の予約を返す。

```json
{
  "items": [
    {
      "id": "reservation_001",
      "status": "confirmed",
      "store_name": "渋谷店",
      "menu_name": "パーソナルトレーニング 60分",
      "starts_at": "2026-10-10T10:00:00+09:00",
      "ends_at": "2026-10-10T11:00:00+09:00",
      "trainer_name": "山田 花子"
    }
  ],
  "next_cursor": "次の位置を示す文字列"
}
```

最終ページでは`next_cursor`を`null`で返す。会員が他の会員の予約を取得することはできない。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 会員以外が呼び出した |
| `422 Unprocessable Content` | `scope`、`limit`または`cursor`の形式が不正 |

## 会員予約のキャンセル

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/reservations/{reservation_id}/cancel` | ログイン中の会員自身の予約をキャンセルする | Cognitoアクセストークン |

予約一覧画面で会員がキャンセルを確定したときに呼び出す。対象は、開始時刻より前の`confirmed`予約だけとする。

### リクエスト

キャンセル理由は任意とする。

```json
{
  "reason": "都合が悪くなったため"
}
```

理由を入力しない場合は、空のJSONオブジェクト`{}`を送る。

予約状態を`cancelled`へ変更し、状態変更履歴を記録する。無料キャンセル期限までなら、利用回数制プランで確保中の1回分を利用可能回数へ戻す。期限後かつ開始時刻より前なら、確保中の1回分を利用済みとして消費する。通い放題プランでは利用回数を操作しない。これらは1つのトランザクションで処理する。

### 成功時のレスポンス

HTTPステータス`200 OK`で、キャンセル結果を返す。

```json
{
  "id": "reservation_001",
  "status": "cancelled",
  "usage_result": "returned"
}
```

| `usage_result` | 意味 |
| --- | --- |
| `returned` | 無料キャンセル期限内のため、確保していた回数を利用可能回数へ戻した |
| `consumed` | 無料キャンセル期限後のため、確保していた回数を消費した |
| `not_applicable` | 通い放題プランのため、利用回数の対象外 |

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `404 Not Found` | 予約が存在しない、または本人の予約ではない |
| `409 Conflict` | すでにキャンセル済み、完了済み、無断欠席、または開始時刻を過ぎている |
| `422 Unprocessable Content` | 任意の`reason`の形式が不正 |

## 会員契約内容の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- |
| `GET` | `/api/v1/members/me/contracts` | ログイン中の会員自身の申込み・契約と利用状況を取得する | Cognitoアクセストークン |

会員ホームから契約・利用状況画面を開いたときに呼び出す。`scope=current`では`pending`、`scheduled`、`active`および`paused`の申込み・契約を返す。`scope=history`では`terminated`、`expired`、`rejected`など過去の申込み・契約を返す。省略時は`current`とする。

```json
{
  "items": [
    {
      "id": "contract_001",
      "status": "active",
      "plan_name": "月4回プラン",
      "price_yen": 30000,
      "starts_on": "2026-10-01",
      "ends_on": "2026-10-31",
      "usage": {
        "type": "count_based",
        "available_count": 3,
        "reserved_count": 1
      }
    }
  ]
}
```

料金、プラン名および契約期間は、契約時に保存したプラン条件を返す。後からプラン設定が変更されても、既存契約の表示内容は変更しない。

`usage.type`が`unlimited`の場合は、`available_count`と`reserved_count`を含めない。

```json
{
  "type": "unlimited"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 会員以外が呼び出した |

該当する契約がない場合は、`200 OK`で`items`を空配列`[]`として返す。`scope`が不正なら`422`を返す。

## スタッフ予約一覧の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/staff/me/reservations` | ログイン中のスタッフが、権限範囲内の予約一覧を取得する | Cognitoアクセストークン |

スタッフ用カレンダー画面を開くときに呼び出す。Reactは返された予約を、開始・終了時刻に基づいてカレンダーへ配置する。

| クエリパラメータ | 必須 | 意味 |
| --- | --- | --- |
| `from` | はい | 表示開始日。`YYYY-MM-DD`形式 |
| `to` | はい | 表示終了日。`YYYY-MM-DD`形式。`from`から最大31日間 |
| `store_id` | いいえ | 表示対象の店舗。指定しない場合は権限範囲内の全店舗 |
| `scope` | いいえ | トレーナーは`mine`（省略時）または`store`。管理者は権限範囲内の予約を取得する |

トレーナーの`scope=mine`には自分が担当する予約を返す。`scope=store`には自分が有効所属する店舗の他トレーナーの予約も返すが、他トレーナー担当分は予約日時・担当者・メニュー・状態だけを返し、会員情報や契約情報は含めない。店舗管理者には担当店舗の予約、事業者管理者には事業者内の全店舗の予約を返す。担当外の店舗や他事業者の予約は、`store_id`を指定しても返さない。

```json
{
  "items": [
    {
      "id": "reservation_001",
      "status": "confirmed",
      "starts_at": "2026-10-10T10:00:00+09:00",
      "ends_at": "2026-10-10T11:00:00+09:00",
      "store": {
        "id": "store_001",
        "name": "渋谷店"
      },
      "member": {
        "id": "member_001",
        "name": "山田 太郎"
      },
      "menu": {
        "id": "menu_001",
        "name": "パーソナルトレーニング 60分"
      }
    }
  ]
}
```

`confirmed`、`completed`、`no_show`および`cancelled`を返す。電話番号、生年月日、契約料金など、トレーナー業務に不要な会員情報は返さない。

他トレーナー担当分の一覧では`member`を省略し、`trainer`に担当者のID・氏名だけを含める。トレーナーが他トレーナー担当予約の詳細APIを呼んでも`404`とする。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | スタッフではない、または有効な役割・店舗所属がない |
| `404 Not Found` | 指定した店舗が存在しない、または担当範囲外 |
| `422 Unprocessable Content` | 日付形式・`scope`が不正、`from`が`to`より後、または期間が31日を超える |

## スタッフ予約詳細の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/staff/me/reservations/{reservation_id}` | ログイン中のスタッフが、権限範囲内の予約詳細を取得する | Cognitoアクセストークン |

スタッフ用カレンダーで予約を選択したときに呼び出す。トレーナーは自分が担当する予約だけを取得できる。店舗管理者は担当店舗の予約、事業者管理者は事業者内の全店舗の予約を取得できる。

```json
{
  "id": "reservation_001",
  "status": "confirmed",
  "starts_at": "2026-10-10T10:00:00+09:00",
  "ends_at": "2026-10-10T11:00:00+09:00",
  "store": {
    "id": "store_001",
    "name": "渋谷店"
  },
  "member": {
    "id": "member_001",
    "name": "山田 太郎"
  },
  "trainer": {
    "id": "staff_001",
    "name": "佐藤 花子"
  },
  "menu": {
    "id": "menu_001",
    "name": "パーソナルトレーニング 60分",
    "duration_minutes": 60
  }
}
```

電話番号、生年月日、契約料金および利用回数など、スタッフの予約対応に不要な会員・契約情報は返さない。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | スタッフではない、または有効な役割・店舗所属がない |
| `404 Not Found` | 予約が存在しない、または担当範囲外 |

## スタッフ勤務予定の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/staff/me/work-shifts` | ログイン中のスタッフ自身の勤務予定を取得する | Cognitoアクセストークン |

スタッフ用の勤務予定画面を開くときに呼び出す。自分自身の勤務予定だけを返すため、店舗管理者や事業者管理者であっても他スタッフの予定は返さない。

| クエリパラメータ | 必須 | 意味 |
| --- | --- | --- |
| `from` | はい | 表示開始日。`YYYY-MM-DD`形式 |
| `to` | はい | 表示終了日。`from`から最大31日間 |

```json
{
  "items": [
    {
      "id": "shift_001",
      "status": "scheduled",
      "starts_at": "2026-10-10T09:00:00+09:00",
      "ends_at": "2026-10-10T18:00:00+09:00",
      "store": {
        "id": "store_001",
        "name": "渋谷店"
      },
      "unavailable_periods": [
        {
          "id": "unavailable_period_001",
          "starts_at": "2026-10-10T12:00:00+09:00",
          "ends_at": "2026-10-10T13:00:00+09:00",
          "reason": "break"
        }
      ]
    }
  ]
}
```

`scheduled`と`cancelled`を返す。各勤務予定に、休憩・研修などの予約不可時間を`unavailable_periods`として含める。勤務予定が複数あっても、カレンダー表示に必要な情報を1回のリクエストで取得するためとする。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | スタッフではない、または有効なスタッフプロフィールがない |
| `422 Unprocessable Content` | 日付形式が不正、`from`が`to`より後、または期間が31日を超える |

## 管理者向け勤務予定の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/work-shifts` | ログイン中の管理者が、権限範囲内の勤務予定を取得する | Cognitoアクセストークン |

店舗管理者または事業者管理者が、スタッフの勤務予定を管理するカレンダーを開くときに呼び出す。トレーナーは呼び出せない。

| クエリパラメータ | 必須 | 意味 |
| --- | --- | --- |
| `from` | はい | 表示開始日。`YYYY-MM-DD`形式 |
| `to` | はい | 表示終了日。`from`から最大31日間 |
| `store_id` | いいえ | 表示対象の店舗 |
| `staff_id` | いいえ | 表示対象のスタッフ |

店舗管理者には担当店舗の勤務予定だけを返す。事業者管理者には事業者内の全店舗の勤務予定を返す。担当外の店舗や他事業者のスタッフを指定しても返さない。

```json
{
  "items": [
    {
      "id": "shift_001",
      "status": "scheduled",
      "starts_at": "2026-10-10T09:00:00+09:00",
      "ends_at": "2026-10-10T18:00:00+09:00",
      "store": {
        "id": "store_001",
        "name": "渋谷店"
      },
      "staff": {
        "id": "staff_001",
        "name": "佐藤 花子"
      },
      "unavailable_periods": [
        {
          "id": "unavailable_period_001",
          "starts_at": "2026-10-10T12:00:00+09:00",
          "ends_at": "2026-10-10T13:00:00+09:00",
          "reason": "break"
        }
      ]
    }
  ]
}
```

`scheduled`と`cancelled`を返す。各勤務予定に、休憩・研修などの予約不可時間を`unavailable_periods`として含める。スタッフの電話番号、メールアドレス、予約内容など、勤務予定の管理に不要な情報は返さない。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 店舗管理者・事業者管理者ではない、または有効な役割・店舗所属がない |
| `404 Not Found` | 指定した店舗またはスタッフが存在しない、または担当範囲外 |
| `422 Unprocessable Content` | 日付形式が不正、`from`が`to`より後、または期間が31日を超える |

## 勤務予定の登録

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/work-shifts` | 管理者または本人が権限範囲内の勤務予定を登録する | Cognitoアクセストークン |

店舗管理者または事業者管理者は権限範囲内のトレーナーの予定を登録できる。トレーナーは自身の有効な店舗所属について、自身の`staff_id`を指定した予定だけを登録できる。

### リクエスト

```json
{
  "staff_id": "staff_001",
  "store_id": "store_001",
  "starts_at": "2026-10-10T09:00:00+09:00",
  "ends_at": "2026-10-10T18:00:00+09:00"
}
```

`staff_id`は勤務するスタッフ、`store_id`は勤務する店舗を指定する。同じスタッフが複数店舗に所属できるため、両方を受け取り、FastAPIが有効な店舗所属を確認して勤務予定へ紐付ける。`status`は受け取らず、新規登録時は必ず`scheduled`とする。

管理者の権限範囲内であること、スタッフと店舗の所属が有効であること、開始が終了より前であることを確認する。同じスタッフの既存勤務予定との重複、または既存の`confirmed`予約と重なる時間帯は登録しない。

### 成功時のレスポンス

HTTPステータス`201 Created`で、登録した勤務予定を返す。

```json
{
  "id": "shift_001",
  "status": "scheduled",
  "staff_id": "staff_001",
  "store_id": "store_001",
  "starts_at": "2026-10-10T09:00:00+09:00",
  "ends_at": "2026-10-10T18:00:00+09:00"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 対象スタッフ・店舗が本人または管理者の権限範囲外 |
| `404 Not Found` | 指定したスタッフまたは店舗が存在しない |
| `409 Conflict` | 既存の勤務予定または`confirmed`予約と時間帯が重複する |
| `422 Unprocessable Content` | 日時形式が不正、開始が終了以降、または開始時刻が過去 |

## 勤務予定の変更

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PATCH` | `/api/v1/work-shifts/{shift_id}` | 管理者または本人が未来の勤務予定の日時を変更する | Cognitoアクセストークン |

店舗管理者または事業者管理者は権限範囲内の勤務予定を変更できる。トレーナーは自身の有効な店舗所属における自身の勤務予定だけを変更できる。対象は開始時刻より前の`scheduled`勤務予定だけとする。

### リクエスト

```json
{
  "starts_at": "2026-10-10T10:00:00+09:00",
  "ends_at": "2026-10-10T19:00:00+09:00"
}
```

開始・終了日時は常に対で指定する。`staff_id`と`store_id`は変更しない。勤務するスタッフまたは店舗を変更する場合は、既存予定を取消して新しい勤務予定を登録する。

管理者の権限範囲内であること、開始が終了より前であること、変更後の時間帯が同じスタッフの他勤務予定および既存の`confirmed`予約と重ならないことを確認する。

### 成功時のレスポンス

HTTPステータス`200 OK`で、変更後の勤務予定を返す。

```json
{
  "id": "shift_001",
  "status": "scheduled",
  "staff_id": "staff_001",
  "store_id": "store_001",
  "starts_at": "2026-10-10T10:00:00+09:00",
  "ends_at": "2026-10-10T19:00:00+09:00"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 対象勤務予定が本人または管理者の権限範囲外 |
| `404 Not Found` | 指定した勤務予定が存在しない |
| `409 Conflict` | 勤務予定が`scheduled`ではない、開始時刻以降、または変更後の時間帯が他勤務予定・`confirmed`予約と重複する |
| `422 Unprocessable Content` | 日時形式が不正、または開始が終了以降 |

## 勤務予定の取消

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/work-shifts/{shift_id}/cancel` | 管理者または本人が未来の勤務予定を取消する | Cognitoアクセストークン |

店舗管理者または事業者管理者は権限範囲内の勤務予定を取り消せる。トレーナーは自身の有効な店舗所属における自身の勤務予定だけを取り消せる。通常の取消ではリクエスト本文を受け取らない。

勤務予定を物理削除せず、`scheduled`から`cancelled`へ変更して取消日時を記録する。過去の勤務実績や管理操作の経緯を残すため、`DELETE`は使用しない。

対象は開始時刻より前の`scheduled`勤務予定だけとする。取消対象の時間帯に`confirmed`予約がある場合は、先に予約の担当者変更またはキャンセルを完了させる必要があるため、勤務予定を取り消さない。

### 成功時のレスポンス

HTTPステータス`200 OK`で、取消後の勤務予定を返す。

```json
{
  "id": "shift_001",
  "status": "cancelled",
  "cancelled_at": "2026-10-01T12:00:00+09:00"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 対象勤務予定が本人または管理者の権限範囲外 |
| `404 Not Found` | 指定した勤務予定が存在しない |
| `409 Conflict` | 勤務予定が`scheduled`ではない、開始時刻以降、または`confirmed`予約が残っている |

## 予約不可時間の登録

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/work-shifts/{shift_id}/unavailable-periods` | ログイン中のスタッフが、勤務予定内の休憩・研修などの予約不可時間を登録する | Cognitoアクセストークン |

トレーナーは自分自身の勤務予定だけに登録できる。店舗管理者は担当店舗、事業者管理者は事業者内の勤務予定に登録できる。

### リクエスト

```json
{
  "starts_at": "2026-10-10T12:00:00+09:00",
  "ends_at": "2026-10-10T13:00:00+09:00",
  "reason": "break"
}
```

`reason`は必須とし、`break`（休憩）または`other`（研修など）を指定する。予約可能時間の計算には使用しないが、スタッフ・管理者が予約不可の種類を確認するために保持する。

予約不可時間は、対象勤務予定の開始から終了までの範囲に収める。開始が終了より前であること、既存の予約不可時間および`confirmed`予約と重ならないことを確認する。過去の時間帯は登録しない。

### 成功時のレスポンス

HTTPステータス`201 Created`で、登録した予約不可時間を返す。

```json
{
  "id": "unavailable_period_001",
  "starts_at": "2026-10-10T12:00:00+09:00",
  "ends_at": "2026-10-10T13:00:00+09:00",
  "reason": "break"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 対象勤務予定が権限範囲外、または有効な役割・店舗所属がない |
| `404 Not Found` | 指定した勤務予定が存在しない |
| `409 Conflict` | 勤務予定が`scheduled`ではない、または既存の予約不可時間・`confirmed`予約と重複する |
| `422 Unprocessable Content` | 日時形式が不正、開始が終了以降、勤務予定の範囲外、または開始時刻が過去 |

## 予約不可時間の変更

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PATCH` | `/api/v1/work-shifts/{shift_id}/unavailable-periods/{unavailable_period_id}` | ログイン中のスタッフが、勤務予定内の予約不可時間を変更する | Cognitoアクセストークン |

トレーナーは自分自身の勤務予定だけを変更できる。店舗管理者は担当店舗、事業者管理者は事業者内の予約不可時間を変更できる。対象は開始時刻より前の予約不可時間だけとする。

### リクエスト

```json
{
  "starts_at": "2026-10-10T12:30:00+09:00",
  "ends_at": "2026-10-10T13:30:00+09:00",
  "reason": "break"
}
```

開始・終了日時は常に対で指定する。`reason`は`break`または`other`へ変更できる。変更後の時間帯が対象勤務予定の範囲内であり、既存の予約不可時間および`confirmed`予約と重ならないことを確認する。

### 成功時のレスポンス

HTTPステータス`200 OK`で、変更後の予約不可時間を返す。

```json
{
  "id": "unavailable_period_001",
  "starts_at": "2026-10-10T12:30:00+09:00",
  "ends_at": "2026-10-10T13:30:00+09:00",
  "reason": "break"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 対象勤務予定が権限範囲外、または有効な役割・店舗所属がない |
| `404 Not Found` | 指定した勤務予定または予約不可時間が存在しない |
| `409 Conflict` | 勤務予定が`scheduled`ではない、予約不可時間の開始時刻以降、または変更後の時間帯が他の予約不可時間・`confirmed`予約と重複する |
| `422 Unprocessable Content` | 日時形式が不正、開始が終了以降、または勤務予定の範囲外 |

## 予約不可時間の削除

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `DELETE` | `/api/v1/work-shifts/{shift_id}/unavailable-periods/{unavailable_period_id}` | ログイン中のスタッフが、勤務予定内の未来の予約不可時間を削除する | Cognitoアクセストークン |

トレーナーは自分自身の勤務予定だけを操作できる。店舗管理者は担当店舗、事業者管理者は事業者内の予約不可時間を削除できる。対象は開始時刻より前の予約不可時間だけとする。

予約不可時間には取消状態や履歴を保持する要件がないため、物理削除する。勤務予定とは異なり、`cancelled`へ状態変更するAPIは作成しない。

### 成功時のレスポンス

HTTPステータス`204 No Content`を返し、レスポンス本文は返さない。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 対象勤務予定が権限範囲外、または有効な役割・店舗所属がない |
| `404 Not Found` | 指定した勤務予定または予約不可時間が存在しない |
| `409 Conflict` | 勤務予定が`scheduled`ではない、または予約不可時間の開始時刻以降 |

## スタッフによる予約状態の変更

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/staff/me/reservations/{reservation_id}/complete` | 来店・利用完了を記録する | Cognitoアクセストークン |
| `POST` | `/api/v1/staff/me/reservations/{reservation_id}/no-show` | 無断欠席を記録する | Cognitoアクセストークン |

予約開始後の`confirmed`予約だけを対象にする。通常の来店完了・無断欠席ではリクエスト本文を受け取らない。

トレーナーは自分が担当する予約だけを変更できる。店舗管理者は担当店舗の予約、事業者管理者は事業者内の全店舗の予約を変更できる。

`complete`では予約状態を`completed`へ、`no-show`では`no_show`へ変更する。利用回数制プランでは、確保中の回数を利用済みにする。通い放題プランでは利用回数を操作しない。状態変更、利用回数処理および状態変更履歴の記録は、1つのトランザクションで処理する。

### 成功時のレスポンス

HTTPステータス`200 OK`で、変更後の予約状態を返す。

```json
{
  "id": "reservation_001",
  "status": "completed"
}
```

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | スタッフではない、または有効な役割がない |
| `404 Not Found` | 予約が存在しない、または担当範囲外 |
| `409 Conflict` | 予約が`confirmed`ではない、または開始時刻前 |

## 会員予約詳細の取得

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/members/me/reservations/{reservation_id}` | ログイン中の会員自身の予約詳細を取得する | Cognitoアクセストークン |

会員が予約一覧から1件を選択したときに呼び出す。

```json
{
  "id": "reservation_001",
  "status": "confirmed",
  "store": {
    "id": "store_001",
    "name": "渋谷店",
    "address": "東京都渋谷区..."
  },
  "menu": {
    "id": "menu_001",
    "name": "パーソナルトレーニング 60分",
    "duration_minutes": 60
  },
  "trainer": {
    "id": "staff_001",
    "name": "山田 花子"
  },
  "starts_at": "2026-10-10T10:00:00+09:00",
  "ends_at": "2026-10-10T11:00:00+09:00",
  "free_cancellation_until": "2026-10-09T10:00:00+09:00",
  "can_cancel": true
}
```

`free_cancellation_until`は、予約作成時に保存したキャンセル規定から算出する。店舗のキャンセル規定が後から変更されても、既存予約の期限は変更しない。`can_cancel`が`true`の場合だけ、会員画面でキャンセル操作を表示する。

### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `404 Not Found` | 予約が存在しない、または本人の予約ではない |

## 追加APIの共通ルール

- `/management/*`は事業者管理者・店舗管理者用、`/system-admin/*`はSaaS運営管理者用とする。事業者管理者の対象事業者はアクセストークンに対応するスタッフプロフィールから特定する。店舗管理者は有効な店舗所属と役割を都度確認する。
- 一覧は`{"items":[...],"next_cursor":null}`を返す。`limit`は省略時20、最大100とし、`cursor`で続きを取得する。対象外の事業者・店舗のデータは返さない。
- 認証失敗は`401`、役割不足は`403`、対象が存在しないかアクセス範囲外なら`404`、状態や同時更新の衝突は`409`、入力形式違反は`422`とする。サーバー側はエラーコードとメッセージを返し、個人情報や内部識別子をエラーに含めない。
- `POST`による作成は`201`、更新・状態変更・削除では`200`で変更後の内容を返す。削除申請のような非同期の受付は`202`を返す。`DELETE`で関連付けを外す場合も業務上の履歴が必要なデータは物理削除しない。
- 状態変更と履歴、利用回数の増減は同じDBトランザクションで保存する。外部のCognito操作を含む場合は、失敗時の補償と再実行可能性をFastAPI実装時に確認する。
- `date`、`starts_on`、`ends_on`は`YYYY-MM-DD`、日時はタイムゾーン付きISO 8601、時刻は`HH:MM`で送る。店舗の営業日・予約判定は日本時間で扱い、保存時にUTCへ正規化する。
- 状態を変えるAPIは不正な遷移を`409`で拒否する。利用停止・閉店・契約一時停止など、事前対応が必要な操作は、未対応の未来予約が残れば`409`とする。対象事業者が`terminated`の場合は読み取り以外を許可しない。`preparing`と`suspended`では要件定義書で許された初期設定・解消操作に限定する。

## 事業者の利用開始と復旧

これらはすべてSaaS運営管理者のみが実行する。一般公開の利用申込フォームは設けない。

### 登録済み事業者を検索する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/system-admin/organizations` | 登録済み事業者を検索する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status`、`limit`、`cursor`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。`id`、`name`、`status`の一覧。停止中・終了済みも検索できる。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 契約済み事業者を登録する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/system-admin/organizations` | 契約済み事業者を登録する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`name`。

#### 正常時のレスポンス

HTTPステータス`201 Created`。`id`と`status=preparing`を返す。契約済みの事業者だけを登録する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 事業者の設定と状態を取得する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/system-admin/organizations/{organization_id}` | 事業者の設定と状態を取得する | Cognitoアクセストークン |

#### リクエスト・パラメータ

事業者ID。

#### 正常時のレスポンス

HTTPステータス`200 OK`。基本情報、状態、登録済み店舗および状態変更履歴を返す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 事業者の利用状態を変更する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PATCH` | `/api/v1/system-admin/organizations/{organization_id}/status` | 事業者の利用状態を変更する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status`、`reason`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。変更後の状態を返す。`active`へは初期管理者と店舗の準備後に変更する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 最初の事業者管理者を招待する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/system-admin/organizations/{organization_id}/initial-admin` | 最初の事業者管理者を招待する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`name`、`email`。

#### 正常時のレスポンス

HTTPステータス`201 Created`。最初の店長を`organization_admin`として招待する。初回ログイン後に本人が最初の店舗を作り、店舗管理者役割を付与する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 本人確認後に事業者管理者の利用を復旧する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/system-admin/organizations/{organization_id}/recover-admin` | 本人確認後に事業者管理者の利用を復旧する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`staff_id`、`verification_reference`、`reason`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。本人確認済みの記録を条件に管理者アカウントを復旧し、有効な管理者を確保する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

状態変更は`preparing → active`、`active ↔ suspended`、`active/suspended → terminated`を許可する。`terminated`からの復帰はPhase 1では許可しない。`reason`、実行者、変更前後の状態、日時を`organization_status_histories`へ残す。`suspended`や`terminated`でも過去の契約・予約は削除しない。

初期管理者招待ではCognitoの招待ユーザー、`user_accounts`、`staff`および事業者管理者役割を作成する。初回ログイン後、その店長が`POST /api/v1/management/stores`で最初の店舗を登録し、既存の`POST /api/v1/staff/{staff_id}/store-memberships`で自身へ`store_admin`と必要なら`trainer`を付与する。初期店舗と両方の管理者役割がそろうまで事業者を`active`にしない。重複するメールアドレス・初期招待は`409`とする。復旧APIは本人確認の完了を示す管理記録なしでは`403`を返し、対象者と操作理由を監査記録に残す。

## 店舗と営業時間

`GET /api/v1/stores`は会員の予約候補用として維持する。管理画面では`/management/stores`を使用する。事業者管理者は事業者内の全店舗、店舗管理者は担当店舗だけを参照・更新できる。店舗の新規登録は事業者管理者のみとする。

### 管理対象店舗を取得する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/management/stores` | 管理対象店舗を取得する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status`、`limit`、`cursor`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。店舗ID、名称、状態、住所の一覧。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 店舗を登録する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/management/stores` | 店舗を登録する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`name`、`address`、`phone_number`。

#### 正常時のレスポンス

HTTPステータス`201 Created`。`status=draft`、`booking_interval_minutes=30`、`free_cancellation_hours=24`の店舗を返す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 店舗の設定を取得する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/management/stores/{store_id}` | 店舗の設定を取得する | Cognitoアクセストークン |

#### リクエスト・パラメータ

店舗ID。

#### 正常時のレスポンス

HTTPステータス`200 OK`。基本情報、予約開始間隔、無料キャンセル期限、通常営業時間、特定日設定を返す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 店舗の基本設定を更新する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PATCH` | `/api/v1/management/stores/{store_id}` | 店舗の基本設定を更新する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`name`、`address`、`phone_number`、`booking_interval_minutes`、`free_cancellation_hours`の変更分。

#### 正常時のレスポンス

HTTPステータス`200 OK`。変更後の店舗を返す。予約開始間隔は`10/15/30`、無料キャンセル期限は`0`〜`168`時間。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 店舗の状態を変更する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PATCH` | `/api/v1/management/stores/{store_id}/status` | 店舗の状態を変更する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status`、`reason`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。`draft → active`、`active ↔ suspended`、`active/suspended → closed`。閉店前に未来の予約と店舗専用契約への対応を要求する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 通常営業時間をまとめて設定する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PUT` | `/api/v1/management/stores/{store_id}/regular-hours` | 通常営業時間をまとめて設定する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`hours:[{day_of_week,opens_at,closes_at}]`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。店舗の通常営業時間を曜日ごとに置き換えて返す。休業曜日は行を省略する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 特定日の営業設定を保存する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PUT` | `/api/v1/management/stores/{store_id}/special-days/{date}` | 特定日の営業設定を保存する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`is_closed`、`reason`、`hours:[{opens_at,closes_at}]`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。指定日の設定と時間帯をまとめて保存して返す。休業日は`hours=[]`。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 特定日の設定を解除する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `DELETE` | `/api/v1/management/stores/{store_id}/special-days/{date}` | 特定日の設定を解除する | Cognitoアクセストークン |

#### リクエスト・パラメータ

対象日。

#### 正常時のレスポンス

HTTPステータス`200 OK`。特定日の上書きを解除し、通常営業時間へ戻す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

営業時間は同じ日の時間帯の重複を拒否する。`PUT`は全件置換を1トランザクションで行い、既存の`confirmed`予約を営業時間外にする変更は`409`とする。店舗を`suspended`にしても既存予約を自動キャンセルしない。`closed`店舗は過去履歴の確認だけに使う。

## メニューとトレーナーの担当設定

事業者管理者は事業者内の全メニューを管理する。店舗管理者は担当店舗での提供と担当トレーナーを設定できるが、事業者共通のメニュー本体は作成・変更しない。

### 管理対象メニューを取得する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/management/menus` | 管理対象メニューを取得する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`store_id`、`status`、`limit`、`cursor`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。メニューID、名称、所要時間、状態、店舗提供状態の一覧。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### メニューを登録する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/management/menus` | メニューを登録する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`name`、`description`、`duration_minutes`。

#### 正常時のレスポンス

HTTPステータス`201 Created`。`status=draft`のメニューを返す。事業者内の同名は`409`。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### メニューの内容・状態を変更する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PATCH` | `/api/v1/management/menus/{menu_id}` | メニューの内容・状態を変更する | Cognitoアクセストークン |

#### リクエスト・パラメータ

名称、説明、所要時間、`status`の変更分。

#### 正常時のレスポンス

HTTPステータス`200 OK`。更新後のメニューを返す。状態は`draft/active/inactive`。既存予約のスナップショットは変えない。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 店舗のメニュー提供状態を設定する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PUT` | `/api/v1/management/stores/{store_id}/menus/{menu_id}` | 店舗のメニュー提供状態を設定する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status=active/inactive`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。店舗とメニューの提供設定を返す。同一事業者内の組み合わせに限る。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### トレーナーの担当メニューを設定する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PUT` | `/api/v1/management/staff/{staff_id}/store-memberships/{membership_id}/menus/{menu_id}` | トレーナーの担当メニューを設定する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status=active/inactive`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。トレーナーの店舗ごとの担当設定を返す。有効な`trainer`役割と店舗提供設定を確認する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

停止操作では未来の確定予約を自動取消しない。新しい予約の候補は、店舗、メニュー、店舗提供設定、トレーナー担当設定、契約の利用条件がすべて有効な場合だけ表示する。

## プランと契約

プラン本体と利用可能な店舗・メニューは事業者管理者が設定する。会員は自分の事業者で申込み受付中のプランを参照する。店舗管理者は担当店舗に紐づく契約申込みを審査する。

### 会員が申し込めるプランを取得する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/plans` | 会員が申し込めるプランを取得する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`store_id`、`limit`、`cursor`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。会員が申し込める`active`プランの名称、料金、回数、期間、利用可能店舗・メニューを返す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 管理対象プランを取得する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/management/plans` | 管理対象プランを取得する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status`、`limit`、`cursor`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。`draft`・`inactive`を含む管理対象プラン一覧。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### プランを登録する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/management/plans` | プランを登録する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`name`、`usage_type`、`period_type`、`usage_limit`、`period_months`、`price_yen`、`carryover_limit`。

#### 正常時のレスポンス

HTTPステータス`201 Created`。`status=draft`のプランを返す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### プランの条件・状態を変更する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PATCH` | `/api/v1/management/plans/{plan_id}` | プランの条件・状態を変更する | Cognitoアクセストークン |

#### リクエスト・パラメータ

プラン条件および`status`の変更分。

#### 正常時のレスポンス

HTTPステータス`200 OK`。更新後のプランを返す。既存契約の`plan_snapshot`は変更しない。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### プランの利用可能店舗を設定する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PUT` | `/api/v1/management/plans/{plan_id}/stores/{store_id}` | プランの利用可能店舗を設定する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status=active/inactive`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。プラン利用可能店舗の設定を返す。同一事業者の店舗に限定する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### プランの利用可能メニューを設定する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PUT` | `/api/v1/management/plans/{plan_id}/menus/{menu_id}` | プランの利用可能メニューを設定する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status=active/inactive`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。プラン利用可能メニューの設定を返す。同一事業者のメニューに限定する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 会員がプランへ申し込む

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/members/me/contracts` | 会員がプランへ申し込む | Cognitoアクセストークン |

#### リクエスト・パラメータ

`plan_id`、`starts_on`。

#### 正常時のレスポンス

HTTPステータス`201 Created`。`pending`の申込みと`plan_snapshot`の要約を返す。終了日はプラン期間から計算する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 管理対象の契約申込み・契約を検索する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/management/contracts` | 管理対象の契約申込み・契約を検索する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`store_id`、`member_id`、`status`、`limit`、`cursor`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。申込み・契約の一覧。店舗管理者は担当店舗で利用する契約のみ。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 契約の内容・状態・履歴を取得する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/management/contracts/{contract_id}` | 契約の内容・状態・履歴を取得する | Cognitoアクセストークン |

#### リクエスト・パラメータ

契約ID。

#### 正常時のレスポンス

HTTPステータス`200 OK`。プランの申込み時条件、状態、期間、利用回数、変更履歴を返す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 申込みを承認する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/management/contracts/{contract_id}/approve` | 申込みを承認する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`reason`（任意）。

#### 正常時のレスポンス

HTTPステータス`200 OK`。`pending`から、開始日が未来なら`scheduled`、当日以前なら`active`へ変更する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 申込みを理由付きで拒否する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/management/contracts/{contract_id}/reject` | 申込みを理由付きで拒否する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`reason`（必須）。

#### 正常時のレスポンス

HTTPステータス`200 OK`。`pending → rejected`として履歴を残す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 契約を一時停止する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/management/contracts/{contract_id}/pause` | 契約を一時停止する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`reason`（必須）。

#### 正常時のレスポンス

HTTPステータス`200 OK`。`active → paused`。対象の未来予約が残る場合は`409`。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 契約を再開する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/management/contracts/{contract_id}/resume` | 契約を再開する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`reason`（必須）。

#### 正常時のレスポンス

HTTPステータス`200 OK`。`paused → active`。利用期間、重複契約、店舗状態を確認する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 契約を終了する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/management/contracts/{contract_id}/terminate` | 契約を終了する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`reason`（必須）。

#### 正常時のレスポンス

HTTPステータス`200 OK`。`scheduled/active/paused → terminated`。対象の未来予約が残る場合は`409`。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 契約期限・利用回数を理由付きで調整する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/management/contracts/{contract_id}/adjustments` | 契約期限・利用回数を理由付きで調整する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`reason`、`ends_on`または`usage_delta`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。延長または回数の付与・返却を記録し、変更後の期間・残数を返す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

`usage_type=limited`なら`usage_limit`は正の整数、`unlimited`なら指定しない。`carryover_limit`は回数制かつ定期更新プランだけに設定する。料金は0以上、期間は1か月以上とする。

申込み作成時にプラン・店舗・メニューの有効性と同一会員の期間重複を確認し、プラン条件と利用可能店舗・メニューを`plan_snapshot`へ固定する。承認・状態変更は`contracts`と`contract_status_histories`を同じトランザクションで更新する。回数調整は`usage_entries`にも理由・実行者・増減を記録し、残数が負になる変更は`409`とする。異なるプランへの変更は旧契約の期間調整と新しい申込みで扱い、自動繰越はしない。

契約期限の調整は`scheduled`、`active`または`paused`の契約を対象とし、変更後の期間が確定済み予約を外したり他契約と重複したりする場合は`409`とする。`ends_on`と`usage_delta`の同時指定は受け付けず、調整ごとに理由と変更前後を記録する。

`scheduled → active`、`active → expired`、定期更新時の回数付与・繰越・失効はバックエンドの定期処理で行う。処理は冪等にし、契約状態履歴と利用回数履歴を残す。店舗管理者が申込みを審査できるのは、`plan_snapshot`内の利用可能店舗と自身の担当店舗が一致する場合だけとする。

## 会員登録・管理・退会

会員用Cognitoでメールアドレスを確認した後にプロフィールを作成する。会員番号は事業者内で一意にサーバー側で発行する。店舗管理者の検索・訂正対象は担当店舗に契約または予約履歴がある会員だけとし、事業者管理者は事業者内の全会員を扱う。

### メール確認済み会員のプロフィールを作成する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/members/me/registration` | メール確認済み会員のプロフィールを作成する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`organization_id`、`name`、`name_kana`、`phone_number`、`birth_date`（任意）、同意文書の版。

#### 正常時のレスポンス

HTTPステータス`201 Created`。確認済みメールの`sub`と紐づく会員プロフィール、会員番号を返す。`active`事業者だけで登録可能。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 管理対象会員を検索する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/management/members` | 管理対象会員を検索する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`member_number`、`name`、`name_kana`、`phone_number`、`email`、`status`、`contract_status`、`limit`、`cursor`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。権限範囲内の会員一覧。退会者は`status=withdrawn`指定時だけ含める。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 管理対象会員の詳細を取得する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/management/members/{member_id}` | 管理対象会員の詳細を取得する | Cognitoアクセストークン |

#### リクエスト・パラメータ

会員ID。

#### 正常時のレスポンス

HTTPステータス`200 OK`。プロフィール、状態、契約要約、権限範囲内の予約要約を返す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 理由付きで会員プロフィールを訂正する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PATCH` | `/api/v1/management/members/{member_id}` | 理由付きで会員プロフィールを訂正する | Cognitoアクセストークン |

#### リクエスト・パラメータ

氏名、フリガナ、電話番号、生年月日の変更分、`reason`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。訂正後のプロフィールを返す。変更前後の値・理由・実行者を監査記録に残す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 会員の利用停止・再開を行う

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `PATCH` | `/api/v1/management/members/{member_id}/status` | 会員の利用停止・再開を行う | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status=active/suspended`、`reason`、緊急停止の有無。

#### 正常時のレスポンス

HTTPステータス`200 OK`。事業者管理者が`active ↔ suspended`で利用停止・再開する。通常の停止前は未来予約への対応が必須。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 会員が事業者から退会する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/members/me/withdraw` | 会員が事業者から退会する | Cognitoアクセストークン |

#### リクエスト・パラメータ

本人による退会確認。

#### 正常時のレスポンス

HTTPステータス`200 OK`。有効・一時停止中の契約、未来の確定予約、未処理調整がなければ`withdrawn`と`withdrawn_at`を返す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 退会した会員が再入会する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/members/me/rejoin` | 退会した会員が再入会する | Cognitoアクセストークン |

#### リクエスト・パラメータ

再入会確認。

#### 正常時のレスポンス

HTTPステータス`200 OK`。`withdrawn → active`。過去契約は復活させない。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 会員がサービスアカウント削除を申請する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/members/me/account-deletion` | 会員がサービスアカウント削除を申請する | Cognitoアクセストークン |

#### リクエスト・パラメータ

直近の本人認証確認、削除範囲の確認。

#### 正常時のレスポンス

HTTPステータス`202 Accepted`。未処理事項がなければ削除申請を受理し、ログインを無効化する。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

既存の`PATCH /api/v1/members/me`は生年月日も更新できる。ログイン用メールアドレスの変更と確認コード送信はCognitoの本人確認フローで行い、業務プロフィールの更新APIへメールアドレスを含めない。

会員登録画面は事業者ごとの案内リンクから`organization_id`を受け取る。FastAPIは事業者が`active`であることを確認し、Cognitoトークン内の`sub`と確認済みメール属性から会員を特定する。管理者によるプロフィール訂正の変更前後はアクセス制御した監査データに保持し、CloudWatchログへ氏名・電話番号の完全な値を出さない。

アカウント削除申請と退会は別操作とする。削除申請を受理したら`user_accounts.deletion_requested_at`と`status=deletion_pending`を記録し、Cognitoのログインを無効化する。30日以内の匿名化、長期未利用3年・事前通知30日の判定と処理はバックエンドの定期処理で行う。匿名化後は業務履歴を保持し、個人を再特定できる紐付けを残さない。

## スタッフ・勤務予定で追加する操作

既存のスタッフ招待APIでは、店舗管理者も担当店舗へ`trainer`のみ招待できる。店舗管理者は担当店舗のトレーナー所属・役割・利用状態を変更できるが、`store_admin`と`organization_admin`の権限は操作できない。トレーナーは自身の勤務予定を既存の`POST/PATCH /work-shifts`と`POST /work-shifts/{shift_id}/cancel`で管理できる。

### 事業者管理者がスタッフを再雇用する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/staff/{staff_id}/reactivate` | 事業者管理者がスタッフを再雇用する | Cognitoアクセストークン |

#### リクエスト・パラメータ

再雇用理由、復帰後の店舗・役割。

#### 正常時のレスポンス

HTTPステータス`200 OK`。事業者管理者がCognitoのユーザーを有効化し、`staff.status=active`へ戻す。店舗管理者は担当店舗でトレーナーのみ再雇用できる。必要な店舗所属と役割は新しい期間として作る。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 事業者管理者役割を解除する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `DELETE` | `/api/v1/staff/{staff_id}/organization-admin-role` | 事業者管理者役割を解除する | Cognitoアクセストークン |

#### リクエスト・パラメータ

対象スタッフID。

#### 正常時のレスポンス

HTTPステータス`200 OK`。事業者管理者が役割を無効化する。最後の有効な事業者管理者なら`409`。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 権限範囲内の勤務予定を一括登録する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/work-shifts/bulk` | 権限範囲内の勤務予定を一括登録する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`items:[{staff_id,store_id,starts_at,ends_at}]`。

#### 正常時のレスポンス

HTTPステータス`201 Created`。最大31件を1トランザクションで登録し、作成した勤務予定の一覧を返す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

一括勤務登録では各件に単発登録と同じ所属・権限・営業時間・重複予約の検証を適用し、1件でも失敗すれば全件を取り消す。トレーナーは自身の勤務予定だけを一括登録できる。再雇用時は過去の勤務・予約・所属・役割の履歴を上書きしない。店舗管理者による再雇用は、当該スタッフに他店舗の所属や管理者役割がない場合に限る。Cognitoの再有効化とDB更新の片方だけが成功した場合の補償・再試行を実装時に設計する。

## 店舗都合キャンセル・状態訂正・運営調査



### スタッフが店舗都合で予約を取消す

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/staff/me/reservations/{reservation_id}/cancel` | スタッフが店舗都合で予約を取消す | Cognitoアクセストークン |

#### リクエスト・パラメータ

`reason`（必須）。

#### 正常時のレスポンス

HTTPステータス`200 OK`。担当トレーナーは自分の予約、店舗管理者は担当店舗、事業者管理者は事業者内の開始前`confirmed`予約を店舗都合で取消す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### 管理者が誤った予約状態を訂正する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/management/reservations/{reservation_id}/correct-status` | 管理者が誤った予約状態を訂正する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`status`、`reason`（必須）。

#### 正常時のレスポンス

HTTPステータス`200 OK`。店舗・事業者管理者が誤登録を訂正し、状態変更履歴と必要な利用回数の増減を残す。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `404 Not Found` | 対象が存在しない、またはアクセス範囲外 |
| `409 Conflict` | 現在の状態や関連データと操作内容が衝突する |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

### SaaS運営管理者が調査対象予約を確認する

| メソッド | パス | 用途 | 認証 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/system-admin/reservations` | SaaS運営管理者が調査対象予約を確認する | Cognitoアクセストークン |

#### リクエスト・パラメータ

`organization_id`、`reservation_id`または期間、`case_reference`、`limit`、`cursor`。

#### 正常時のレスポンス

HTTPステータス`200 OK`。問い合わせ・障害調査に必要な予約情報だけを返す。通常の店舗運用には使用しない。

#### エラー時のレスポンス

| HTTPステータス | 条件 |
| --- | --- |
| `401 Unauthorized` | アクセストークンがない、有効期限切れ、または不正 |
| `403 Forbidden` | 利用者の役割、所属または対象事業者の状態が操作を許さない |
| `422 Unprocessable Content` | パラメータまたはリクエストの形式が不正 |

店舗都合キャンセルでは、無料キャンセル期限後でも確保中の利用回数を返却する。予約状態、状態変更履歴、回数履歴を同じトランザクションで保存し、予約可能時間を再計算できる状態にする。状態訂正は既存履歴を編集せず、訂正理由と変更前後の状態を追加する。SaaS運営管理者による予約確認では問い合わせ番号`case_reference`を必須とし、対象・理由・日時を監査記録へ残す。変更APIは提供しない。

## 要件との対応

| 要件定義書の領域 | 主なAPIまたは処理 |
| --- | --- |
| 事業者の利用開始 | 事業者登録、初期管理者招待、初期店舗登録、事業者状態変更 |
| 認証・認可 | Cognito Managed Loginと既存の`GET /me`、業務APIごとの役割・所属判定 |
| スタッフ・権限管理 | 既存の招待・所属・役割変更と、再雇用・管理者復旧・管理者役割解除 |
| 店舗・トレーナー管理 | 店舗設定、営業時間・特定日、店舗所属、担当メニュー |
| トレーナー勤務予定・予約可能時間 | 既存の勤務予定・予約不可時間・空き枠APIと一括勤務登録 |
| メニュー・プラン・契約管理 | メニュー・プラン設定、会員申込み、審査、契約状態変更、回数調整、定期更新処理 |
| 予約作成・状態管理 | 既存の予約作成・確認・会員取消・来店登録に、店舗都合取消と状態訂正を追加 |
| 会員管理 | 登録、検索、訂正、利用停止、退会、再入会、削除申請、長期未利用処理 |

## 実装前にそろえるデータ設計

APIから必要になるが、現在の[テーブル設計書](./テーブル設計書.md)に保持先や一意性が未定義の事項がある。FastAPI実装前に確定する。

- 規約・プライバシーポリシー同意の文書種別、版、同意日時。
- 管理者によるプロフィール訂正、権限復旧、調査閲覧の監査記録。
- 削除・匿名化の申請、処理結果、長期未利用通知の送信結果と再実行状態。
- 同時実行時の事業者管理者最低1人制約と、Cognito操作を伴う復旧・停止の整合性。

これらを未実装のまま「APIがあるので要件を満たした」とは扱わない。設計書上はPhase 1の対象として追跡する。
