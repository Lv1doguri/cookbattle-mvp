# COOKUP API 계약

정확한 요청/응답 필드는 서버를 띄운 뒤 **http://localhost:8000/docs** (Swagger)에서 직접 눌러볼 수 있어요. 이 문서는 "어떤 화면에서 무엇을 부르는지"와 "화면만 봐서는 알 수 없는 규칙"을 정리한 거예요.

## 공통 규칙

- **인증**: 회원가입/로그인 외 전부 `Authorization: Bearer <access_token>` 필요. 없으면/틀리면 401.
- **에러 형식**: 항상 `{ "detail": "<화면에 보여줄 문장>", "code": "<기계용 코드>" }`. `detail`은 언제나 문자열이라 그대로 렌더링해도 안전해요. 422만 `errors: [{field, message}]`가 추가로 붙어요.
- **시간**: 전부 UTC ISO 8601(`2026-09-25T12:52:36Z`). "2시간 전", "05:42:10 남음" 같은 표시는 프론트에서 계산하세요. 대결 남은 시간은 `ends_at`과 `server_time`(또는 `seconds_left`)를 쓰면 기기 시계가 틀려도 안전해요.
- **실력 단계 코드**: `beginner`(초급) · `intermediate`(중급) · `advanced`(고급). 응답에는 `tier_label`("중급")도 같이 와요.
- **이미지**: `photo_url`은 `/uploads/xxx.png` 상대경로 → `${API_BASE_URL}${photo_url}`.
- **목록 페이지네이션**: `?limit=20&offset=0` → `{ items: [...], has_more }`.
- **좋아요/저장/팔로우**: POST = 켜기, DELETE = 끄기. 몇 번 눌러도 결과가 같아요(연타 안전). 응답에 최신 개수가 와요.
- 아바타 글자("민", "유")는 `nickname`의 첫 글자로 프론트에서 만드세요.

## 화면 → API

| # | 화면 | 호출 |
|---|------|------|
| 01 | Main (로그인) | `POST /auth/login` `{email, password}` → `{access_token, user}` · 회원가입 링크 → `POST /auth/signup` `{email, password, nickname?}` |
| 02 | Level (실력 선택) | `PUT /me/tier` `{tier}` · 가입 직후 `user.needs_tier_selection == true`면 이 화면으로 |
| 03 | Home | `GET /feed?tab=recommended\|following` · 상단 배너 `GET /battles/today` (`theme`, `reward_xp`, `seconds_left`) · 좋아요 `POST/DELETE /posts/{id}/like` · 저장 `POST/DELETE /posts/{id}/save` · 팔로우 `POST/DELETE /users/{id}/follow` |
| 04 | Post | `GET /posts/{id}` (`author_follower_count` 포함) · 댓글 `GET/POST /posts/{id}/comments` · 댓글 좋아요 `POST/DELETE /comments/{id}/like` · 레시피 카드 → `GET /recipes/{id}` |
| 05 | Profile | `GET /me` · 프로필 수정 `PATCH /me` `{nickname?, bio?, handle?}` · 탭: 게시물 `GET /users/{내 id}/posts`, 좋아요 `GET /me/likes`, 저장 `GET /me/saved` · 다른 사람 프로필 `GET /users/{id}` |
| 06 | Camera | 서버 호출 없음. 촬영이 끝나면 `POST /photos` (multipart, 필드명 `file`) → `{photo_id, photo_url, captured_at, expires_at}` |
| 07 | Compose | `POST /photos`로 받은 `photo_id`와 함께 `POST /posts` (아래 참고). 대결 참가로 들어왔다면 `battle_id`도 함께 |
| 08 | Done | `POST /posts` 응답 그대로: `reward {xp, coins, leveled_up, ...}`, `progress {level, xp, next_level_xp, xp_to_next_level}` |
| 09 | Battle | `GET /battles/today?tier=` (탭마다 tier 변경) · 순위 미리보기 `GET /battles/{id}/leaderboard?limit=2` · 코인 `GET /me`의 `coins` |
| 10 | Leaderboard | `GET /battles/today?tier=`로 `id`를 얻고 `GET /battles/{id}/leaderboard?limit=100` · 하단 "나의 순위" = 응답의 `me` |
| 11 | Recipes | `GET /recipes?q=&category=&max_cost=5000&difficulty=&max_minutes=&sort=latest\|popular` · 우승 레시피 `GET /recipes/winners` · "5,000원 이하 인기" = `?max_cost=5000&sort=popular` |
| 12 | RecipeDetail | `GET /recipes/{id}` · 저장하기 `POST /posts/{id}/save` · 평점 `PUT /recipes/{id}/rating` `{score: 1~5}` |
| 13 | Shop | `GET /shop/items?category=cafe\|food\|convenience` (생략=전체) → `coins`, `available_coupon_count`("내 쿠폰 N"), `items` |
| 14 | Purchase | 필요/보유/구매 후 코인은 `price_coins`와 `coins`로 프론트에서 계산 · [구매하기] `POST /shop/items/{id}/purchase` → `{coupon, coins}` |
| 15 | MyCoupons | `GET /me/coupons?status=available\|used` → `available_count`, `used_count`(탭 숫자), `items` · [쿠폰 사용] `POST /me/coupons/{id}/use` |

`category` 코드: `rice`(밥) `noodle`(면) `pasta`(파스타) `meat`(고기) `healthy`(건강식) `dessert`(디저트) · 상점 카테고리: `cafe` `food` `convenience`

## 게시물 올리기 (Camera → Compose → Done)

1. 카메라 촬영 → `POST /photos` → `photo_id`. 사진은 **촬영 후 1시간 안에** 게시해야 하고(`expires_at`), 한 번 게시하면 다시 못 써요. 촬영 시각은 서버가 찍어서 `captured_at`으로 돌아와요("인증된 사진" 표시용).
2. [게시] → `POST /posts`

```json
{
  "photo_id": 1,
  "caption": "오늘 처음으로 파스타를 만들어봤어요!",
  "title": "크림 파스타",
  "ingredients": [{ "name": "파스타 면", "amount": "1인분" }, { "name": "마늘" }],
  "steps": [{ "text": "파스타를 8분 삶는다" }],
  "cost_krw": 4500,
  "cook_minutes": 20,
  "difficulty": "intermediate",
  "category": "pasta",
  "battle_id": 7
}
```

`ingredients[].amount`, `caption`, `category`, `battle_id`는 생략 가능. 재료·조리 방법은 1개 이상 필요.
갤러리 사진 차단은 앱(카메라)에서 하는 거라 서버는 "카메라 업로드용 엔드포인트로 올라온 최근 사진"인지만 확인해요.

## 게임 규칙 (서버가 계산하니 화면엔 응답값만 쓰세요)

- **레벨**: `level = xp ÷ 500 + 1` (1,250 XP → Lv.3, 다음 레벨은 1,500). "중급 Lv.3" = `tier_label` + `level`.
- **일반 게시**: +50 XP, +30 코인. 하루(한국시간 자정 기준) 3개까지만 보상, 그 뒤엔 `reward.daily_limit_reached: true`에 0/0.
- **대결 참가**: 대결 보상(초급 150XP/50코인, 중급 200/80, 고급 300/120)을 일반 보상 대신 받아요. 대결 1개당 1인 1회.
- **대결은 내 실력 단계에서만 참가**할 수 있어요(다른 탭은 보기 전용, `can_join: false`). 대결은 한국시간 자정에 마감.
- **순위 점수**: 참가 보상 + (다른 사람이 누른 좋아요 × 10). 대결이 열려 있는 동안만 오르내리고, 동점이면 먼저 참가한 사람이 위. 본인 좋아요는 점수에 안 들어가요.
- `leaderboard.me.xp_to_next_rank` = 바로 위 사람을 제치는 데 필요한 XP.
- **우승 레시피**: 단계별로 "최근 7일 안에 마감된 가장 최근 대결의 1위".
- **쿠폰**: 코인 차감과 쿠폰 발급은 동시에 일어나고, 쿠폰은 한 번만 쓸 수 있어요. 사용기한은 구매일 + 90일.

## 에러 코드 (자주 쓰는 것)

`email_taken`(409) · `invalid_credentials`(401) · `unsupported_image`(400) · `photo_expired`(400) · `photo_already_used`(409) · `wrong_tier`(403) · `battle_closed`(400) · `already_entered`(409) · `insufficient_coins`(400) · `coupon_already_used`(409) · `coupon_expired`(410) · `handle_taken`(409)

## 디자인에서 정해지지 않아 백엔드가 가정한 것

프론트/기획과 확인이 필요해요.

1. **회원가입 화면이 없음** — 로그인 화면의 "회원가입"이 바로 Level로 가서 닉네임 입력이 없어요. 그래서 `nickname`은 선택이고, 생략하면 이메일 앞부분이 닉네임/아이디(`@handle`)가 돼요. 프로필 수정(`PATCH /me`)에서 바꿀 수 있어요.
2. **Compose에 음식 종류 입력이 없음** — Recipes 화면엔 밥/면/파스타… 필터가 있는데 작성 화면엔 고르는 곳이 없어서, `category`는 선택 필드로만 열어뒀어요. 입력 UI를 넣지 않으면 카테고리 필터에는 아무것도 안 잡혀요.
3. **평점(4.8)을 입력하는 화면이 없음** — `PUT /recipes/{id}/rating`만 만들어뒀어요. 내 레시피에는 못 줘요.
4. **"6위 오르려면 +5 XP"** — 목업 숫자(내 순위 27위, 바로 위 26위와 5XP 차이)가 서로 안 맞아요. 서버는 "바로 위 사람을 제치기 위한 XP"를 줘요.
5. **추천 피드** — 아직 추천 알고리즘 없이 "전체 최신순"이에요.
6. **화면은 있는데 서버가 없는 것** — 알림(종 아이콘), 공유, 게시물 더보기(삭제/신고), 팔로워/팔로잉 목록, "만들어보기"로 만든 요리를 원본 레시피와 연결하는 기능.
7. **상점 쿠폰은 앱 안에서 만든 12자리 번호**예요. 실제 기프티콘 발급사 연동은 아직 없어요.
