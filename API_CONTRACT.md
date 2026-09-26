# 요리왕(COOKUP) API 계약

디자인 "요리왕" 2026-09-26 버전(화면 17개) 기준이에요. 정확한 요청/응답 필드는 서버를 띄운 뒤 **http://localhost:8000/docs** (Swagger)에서 직접 눌러볼 수 있어요. 이 문서는 "어떤 화면에서 무엇을 부르는지"와 "화면만 봐서는 알 수 없는 규칙"을 정리한 거예요.

## 공통 규칙

- **인증**: 로그인/회원가입/닉네임 중복확인 외 전부 `Authorization: Bearer <access_token>` 필요. 없거나 틀리면 401. 로그아웃은 토큰을 지우면 끝(서버 호출 없음).
- **에러 형식**: 항상 `{ "detail": "<화면에 보여줄 문장>", "code": "<기계용 코드>" }`. `detail`은 언제나 문자열이라 그대로 렌더링해도 안전해요. 422만 `errors: [{field, message}]`가 추가로 붙어요.
- **시간**: 전부 UTC ISO 8601(`2026-09-25T12:52:36Z`). "1시간 전" 같은 표시는 프론트에서 계산하세요. 대결 남은 시간은 `ends_at`과 `server_time`(또는 `seconds_left`, `days_left`)로.
- **실력 코드**: `beginner`(초급) · `intermediate`(중급) · `advanced`(상급). 응답에 `tier_label`/`difficulty_label`이 같이 와요.
- **이미지**: `photo_url`, `avatar_url`은 `/uploads/xxx.png` 상대경로 → `${API_BASE_URL}${photo_url}`. 없으면 `null`(자리표시 이미지를 보여주세요). 아바타 글자("유")는 `nickname` 첫 글자로.
- **목록**: `?limit=20&offset=0` → `{ items, has_more }` (레시피는 `total`도).
- **저장/북마크**: POST = 켜기, DELETE = 끄기. 연타해도 결과가 같아요.

## 화면 → API

| # | 화면 | 호출 |
|---|------|------|
| 01 | Main (로그인) | `POST /auth/login` `{email, password}` → `{access_token, user}` |
| 02 | Level (회원가입) | 닉네임 중복 에러: `GET /auth/nickname-available?nickname=` → `{available}` · 가입하기: `POST /auth/signup` `{email, nickname, password, tier}` → 로그인과 같은 응답. 닉네임이 겹치면 409 `nickname_taken` ("이미 사용 중인 닉네임입니다") |
| 03 | Tutorial | 서버 호출 없음 |
| 04 | Home | `GET /me/home` 한 번이면 돼요 (아래 참고) |
| 05 | Profile (정보 수정) | `PATCH /me` `{nickname?, email?, password?, tier?}` · [사진 변경] `PUT /me/avatar` (multipart, 필드명 `file`). 실패하면 화면의 "저장하지 못했어요" |
| 06 | Recipes | `GET /recipes?q=&category=&budget=&time=&difficulty=&tool=&sort=latest\|popular` |
| 06-1 | RecipeFilter | 같은 API. "레시피 N개 보기"는 선택한 조건에 `limit=1`을 붙여 부르고 응답의 `total`을 쓰세요 |
| 07 | RecipeDetail | `GET /recipes/{id}` · 저장/저장됨 `POST/DELETE /recipes/{id}/save` · 댓글 `GET/POST /recipes/{id}/reviews` |
| 08 | Menu | 저장한 레시피 `GET /me/saved-recipes` · 최근 본 레시피 `GET /me/recent-recipes` · 내가 쓴 후기 `GET /me/reviews` · 개수는 `GET /me`의 `saved_recipe_count`, `review_count` |
| 09 | Camera (네트워크 오류) | 프론트 화면. 요청이 실패(네트워크)하면 이 화면으로 |
| 10 | Battle | `GET /battles/current?tier=` (그룹 탭마다 tier를 바꿔 호출, 생략하면 내 그룹) · 헤더 보유 포인트는 `GET /me`의 `progress.points` |
| 11 | Compose (요리 인증) | `POST /battles/{battle_id}/entries` (**multipart**: `dish_name`, `description`, `photo`) |
| 12 | Done (참가 완료) | 위 응답 그대로: `points_awarded`(+1P), `entry`("치즈 스크램블 에그 by 나") |
| 13 | Post (투표) | `GET /battles/{battle_id}/entries` · [투표] `POST /entries/{entry_id}/vote` |
| 14 | Leaderboard (대결 결과) | `GET /battles/{battle_id}/result` |
| 15 | Shop | `GET /shop` |
| 16 | Purchase | 필요/보유/교환 후 포인트는 `price_points`와 `points`로 계산 · [교환하기] `POST /shop/items/{id}/exchange` |
| 17 | MyCoupons (교환 완료) | 위 응답 그대로: `item_name`, `points`(남은 포인트) |

## 화면별 메모

**Home** `GET /me/home` → `me`(닉네임, 아바타, `tier_label`="중급", `progress`), `cooking_count_this_month`("이번 달 요리 8회"), `saved_amount_krw`("절약한 식비"), `history`(참가 이력), `reviews`(내가 쓴 후기).
- `progress`: `level`(Lv.2), `points`(보유 1,240P), `points_to_next_level`(6P) → 다음 레벨은 `level + 1`.
- `history`가 빈 배열이면 "아직 참가한 대결이 없어요". 항목의 `status`: `in_progress`(진행 중) · `ranked` · `void`(무효). `rank`가 없으면 "참가", 있으면 "2등".

**Battle** `GET /battles/current`
- `title`("계란 요리 대결"), `description`, `days_left`("남은 기간 3일"), `participants`, `week_label`("9월 3주차").
- 버튼: `can_join`이 true면 [참가하기 (+1P)]. false면 비활성 — `is_my_group`이 false면 "내 그룹(중급) 대결에만 참가할 수 있어요", `has_joined`면 이미 참가, `is_open`이 false면 마감.
- `last_result`: "지난 대결 결과 — 라면 대결 · 내 순위 2등" (`my_rank`가 null이면 순위 줄은 숨기세요).

**투표** `GET /battles/{id}/entries` → 항목마다 `state`로 버튼을 정해요: `votable`=[투표] · `mine`="투표 불가" · `voted`="투표함" · `vote_done`="투표 완료" · `unavailable`=투표할 수 없는 상태(마감/다른 그룹). 상단 "투표 완료! 이미 투표하셨습니다"는 `has_voted`.

**결과** `GET /battles/{id}/result` (마감 전이면 409 `battle_not_finished`)
- `status`가 `void`면 "대결이 무효 처리됐어요"(참가자 3명 미만). 이때도 참가 +1P는 지급돼요. `podium`, `top10`은 빈 배열.
- `me`: `rank`, `rank_points`("+4P"), `level_from` → `level_to`, `leveled_up`("레벨 업!"), `can_share_recipe`.
- `top10[].tie`: `first`="먼저 제출", `tied`="동점", null=동점 아님 (`submitted_at`으로 시각 표시). `can_share_recipe`는 1등 "레시피 공유 가능" 표시용.

**Shop** `GET /shop` → `points`, `level`, `items[].state`: `available` · `insufficient_points`("N P 더 필요해요" = `points_short`) · `locked`("Lv.`required_level`부터 교환 가능").

**레시피 필터**(여러 개 선택 가능, 같은 그룹 안은 OR / 그룹끼리는 AND). 같은 파라미터를 여러 번 붙이세요: `?category=rice&category=noodle&budget=under_5000`
- `category`: `rice`(밥) `noodle`(면) `pasta`(파스타) `meat`(고기) `soup`(국·찌개) `side`(반찬) `healthy`(건강식) `dessert`(디저트)
- `budget`: `under_5000`(5,000원 이하) · `5000_to_10000`(5,001~10,000) · `over_10000`(10,000 초과)
- `time`: `le_10` · `le_15` · `le_30`(N분 이하) · `ge_60`(1시간 이상)
- `difficulty`: `beginner` `intermediate` `advanced` · `tool`: `microwave`(전자레인지만) `pan`(프라이팬 하나) `airfryer`(에어프라이어) `rice_cooker`(밥솥)
- 빠른 칩: 5천원 이하=`budget=under_5000` · 15분 이내=`time=le_15` · 초급=`difficulty=beginner` · 건강식=`category=healthy` · 디저트=`category=dessert`
- `q`는 요리 이름, 재료 이름, "밥 요리 대결" 같은 우승 문구를 검색해요. `total`이 0이면 "조건에 맞는 레시피가 없어요".

## 게임 규칙 (서버가 계산하니 화면엔 응답값만 쓰세요)

- **대결**: 매주 월요일 00:00(한국시간) ~ 다음 월요일 00:00. 실력 그룹(초급/중급/상급)마다 따로 열리고 주제는 같아요. 주제는 8주 주기로 돌아가요.
- **참가**: 내 그룹 대결만, 대결 하나에 1번. 사진 필수. 참가하면 즉시 **+1P**.
- **투표**: 내 그룹 대결만, 대결 하나에 1표, 자기 작품 불가. 마감 후엔 못 해요.
- **결과 집계**: 마감 후 **첫 API 요청 때 자동으로** 집계돼요(별도 스케줄러 없음). 득표 수 순, 동점이면 먼저 제출한 사람이 앞. **1등 +5P · 2등 +4P · 3등 +3P**가 참가 포인트에 더해져요. 참가자가 3명 미만이면 무효.
- **레벨**: 지금까지 **모은 포인트** 기준이라 상점에서 써도 안 떨어져요. Lv.2=5P, Lv.3=15P, Lv.4=30P, Lv.5=50P … (Lv.N = 5·N·(N−1)/2 P)
- **실력 변경**: 정보 수정에서 바꾸면 "다음 대결부터" 적용돼요. 응답의 `pending_tier`, `pending_tier_applies_at`으로 안내 문구를 만들 수 있어요.
- **교환**: 포인트 차감과 교환 내역 저장이 한 번에 일어나요. MVP라 실제 발송은 없어요.
- **레시피 공유**: 대결 1등만 `POST /entries/{entry_id}/recipe`로 자기 레시피를 레시피 탭에 올릴 수 있어요.

## 에러 코드 (자주 쓰는 것)

`nickname_taken`(409) · `email_taken`(409) · `invalid_credentials`(401) · `unsupported_image`(400) · `wrong_group`(403) · `battle_closed`(400) · `already_entered`(409) · `already_voted`(409) · `own_entry`(400) · `battle_not_finished`(409) · `insufficient_points`(400) · `level_locked`(403) · `not_winner`(403) · `already_shared`(409)

## 디자인에서 정해지지 않아 백엔드가 가정한 것

프론트/기획과 확인이 필요해요. 중요한 순서예요.

1. **회원가입 화면에 이메일 입력이 없어요.** 그런데 로그인은 이메일이라, 이메일 없이 가입하면 로그인할 방법이 없어요. 그래서 `email`을 필수로 받아요 → 회원가입 화면에 이메일 칸이 필요해요.
2. **포인트 경제가 안 맞아요.** 참가 +1P, 순위 보상 3~5P인데 상점은 800~5,000P예요. 매번 1등을 해도(대결당 6P) 커피 기프티콘 하나에 대결을 167번 참가해야 해요. 게다가 800P를 모으면 이미 레벨이 18이라 "Lv.5부터 교환 가능" 잠금은 사실상 의미가 없어요. 목업 숫자(1,240P, Lv.2)와도 안 맞아서, 보상 수치 또는 상점 가격을 정해야 해요. (수치는 `backend/app/content.py`에서 바꿔요)
3. **레벨 기준**은 목업에서 역산했어요("2등 +4P로 Lv.1→2", "Lv.2에서 6P 더 필요"가 동시에 맞는 값).
4. **순위 보상 5/4/3P**는 이전 기획 문서의 점수표를 가져왔고, 참가 +1P와 별개로 더해줘요. 화면의 "+4P"가 합계인지 추가인지는 확정이 필요해요.
5. **투표 자격**: 디자인엔 조건이 없어서 "내 그룹 대결이면 참가하지 않아도 투표 가능"으로 했어요.
6. **1등 레시피 공유 화면이 없어요.** `POST /entries/{entry_id}/recipe`의 입력 필드는 레시피 상세 화면을 기준으로 정했어요.
7. **"이번 달 요리 N회" = 이번 달 대결 참가 횟수, "절약한 식비" = 횟수 × 4,000원**(목업의 8회 → 32,000원에서 역산)으로 했어요.
8. **샘플 레시피 8개**를 공식 계정 "요리왕" 이름으로 넣어뒀어요(처음엔 1등 레시피가 하나도 없어서 레시피 탭이 비니까요). 내용은 임시고, 저장 수는 0부터 시작해요.
9. **없는 것**: 알림, 설정(알림), "재료로 찾기"(링크가 `#`), 조리 시간 30분 초과~1시간 미만은 필터 칸이 없어서 어디에도 안 잡혀요.
10. **대결 주제 문구**는 계란 요리 외에는 임시로 썼어요(`backend/app/content.py`의 `BATTLE_THEMES`).
