# 요리왕(COOKUP) API 계약

디자인 "요리왕 리디자인" 2026-09-27 버전(화면 19개, Google 로그인 + 테마 대결 + 대회 후 투표) 기준이에요. 정확한 요청/응답 필드는 서버를 띄운 뒤 **http://localhost:8000/docs** (Swagger)에서 직접 눌러볼 수 있어요. 이 문서는 "어떤 화면에서 무엇을 부르는지"와 "화면만 봐서는 알 수 없는 규칙"을 정리한 거예요.

> **v4.0 — 백엔드 통합 업데이트**: `feat/backend-full-a`(이 문서의 원래 설계, 구글 로그인·테마 대결·실제 프론트와 이미 연결·검증됨)를 기본으로 하고, `feat/backend-full-b`에서 만들었던 기능을 이식했어요.
> - **관리자 데모 도구 (신규)**: `POST /admin/battles/{id}/phase`, `POST /admin/battles/{id}/close` — 날짜를 기다리지 않고 즉시 요리→투표→종료 전환. `POST /admin/shop/items`로 상품 추가. `.env`의 `ADMIN_EMAILS`로 가입하면 자동으로 관리자.
> - **작품 댓글 + 별점 (신규)**: `POST/GET /entries/{id}/comments`, `GET /entries/{id}/comments/mine`, `PATCH/DELETE /comments/{id}` — 배틀 출품작에 평가 남기기. `EntryOut`에 `rating_avg`/`rating_count`/`comment_count` 추가.
> - **사진 재사용 탐지 (신규)**: 지각 해시(dHash)로 이전에 올라온 사진과 같은 사진(리사이즈·재압축 포함)이면 `POST /photos`가 409 `photo_reused`. 기존 카메라 전용 업로드 + 1시간 만료 + 1회용 제한과 함께 동작.
> - **포인트 경제 수정**: 이 문서 앞 버전(v3.x)이 스스로 "포인트 경제가 안 맞다"고 지적했던 문제를 팀 기획 수치로 해결했어요 — 참가 1P→**10P**, 투표 1P→**2P**, 순위 5/4/3P→**100/60/40P**. 레벨 기준(Lv.2=**100P**, Lv.3=**300P**, Lv.4=**700P**, Lv.5=**1500P**, 이후 800P씩)과 상점 가격(편의점 **120P**, 아메리카노 **240P**, 학식 **650P**, 치킨 **2600P**)이 서로 맞게 재설계됐어요.
> - **상점 안전장치 (신규)**: 상품마다 `monthly_limit`(월 재고, 매달 자동 초기화), 1인당 월 교환 **2회** 제한. 초과 시 `state: "sold_out_this_month"` / `"monthly_limit_reached"`.
> - **포인트 유효기간 (신규)**: 적립 후 **365일**이 지나면 보유(`points`) 포인트에서 자동 소멸 (누적 `total_points`·레벨은 그대로). `/me`, `/me/home`, `/shop` 호출 시점에 정리됨.
> - **뺀 것**: 친구 기능(backend-full-b에는 있었지만, 이 디자인의 19개 화면 어디에도 친구 화면이 없어서 이번 통합에서는 빠졌어요. 필요하면 추가 가능).
> - 테스트: pytest 29개(기존) + 신규 기능 7개 = **36개** 전부 통과. `cd backend && pytest`

> **이후 업데이트**
> - **구도 인증 AI (신규, 온라인 사진 도용 방지)**: 대결 참가엔 정면 사진 + 대결마다 무작위로 정해지는 구도 사진, 두 장이 필요해요(`BattleOut.required_angle*`, `POST /battles/{id}/entries`의 `angle_photo_id`). Claude Vision API(`services/vision.py`)가 같은 음식인지·요청한 구도가 맞는지 판정하고, 실패하면 400 `angle_mismatch`. `ANTHROPIC_API_KEY`가 없으면 로컬 개발용으로 판정을 건너뛰어요.
> - **작품 평가에 "따라하기 쉬움" 추가 (기획서 반영)**: `docs/feature-plan-자취요리왕.md`가 원래 명시한 3항목(비주얼/가성비/따라하기 쉬움)에 맞춰 `ease_rating`을 추가했어요. `overall_rating`은 이제 세 항목의 평균.
> - **"따라 만들었어요" 레시피 완료 인증 (신규, 기획서 반영)**: `POST /recipes/{id}/cook` — 레시피 하나당 1인 1회, `RECIPE_COOK_POINTS`(기본 5P) 지급. 이미 인증했으면 409 `already_cooked`. `RecipeCard`/`RecipeDetailOut`에 `cooks`/`is_cooked` 추가.
> - **전자레인지 요리 대회 테마 추가 (기획서 반영)**: `content.THEME_BATTLES`에 "도구 제한(전자레인지만)" 테마를 추가했어요.
> - **투표 취소 (신규)**: `DELETE /entries/{entry_id}/vote` — 투표 기간에만, 받았던 +2P도 함께 회수. 취소하면 같은 대결의 다른 작품에 다시 투표할 수 있어요.
> - **작품 평가가 투표 화면에 통합 (변경)**: 투표 직후 그 작품에 댓글 + 비주얼/가성비 별점을 바로 남길 수 있어요(프론트 Vote 화면). 원래 있던 `rating`(맛 포함 단일 별점) 대신 `visual_rating`/`value_rating`로 나뉘었고, 맛은 평가 항목에서 뺐어요(사진만 보고 투표하니 실제로 먹어보지 않고는 평가할 수 없어서). `overall_rating`은 두 항목의 평균.

## 공통 규칙

- **인증**: 로그인/회원가입/닉네임 중복확인 외 전부 `Authorization: Bearer <access_token>` 필요. 없거나 틀리면 401. 로그아웃은 토큰을 지우면 끝(서버 호출 없음).
- **에러 형식**: 항상 `{ "detail": "<화면에 보여줄 문장>", "code": "<기계용 코드>" }`. `detail`은 언제나 문자열이라 그대로 렌더링해도 안전해요. 422만 `errors: [{field, message}]`가 추가로 붙어요.
- **시간**: 전부 UTC ISO 8601(`2026-09-25T12:52:36Z`). "방금 전" 같은 표시는 프론트에서 계산하세요. 대결 남은 시간은 `ends_at`/`voting_ends_at`과 `server_time`(또는 `seconds_left`, `days_left`)으로.
- **실력 코드**: `beginner`(초급) · `intermediate`(중급) · `advanced`(상급). 응답에 `tier_label`/`difficulty_label`이 같이 와요.
- **이미지**: `photo_url`, `avatar_url`은 `/uploads/xxx.png` 상대경로 → `${API_BASE_URL}${photo_url}`. 없으면 `null`(자리표시 이미지를 보여주세요). 아바타 글자("유")는 `nickname` 첫 글자로.
- **목록**: `?limit=20&offset=0` → `{ items, has_more }` (레시피는 `total`도).
- **저장/북마크**: POST = 켜기, DELETE = 끄기. 연타해도 결과가 같아요.

## 화면 → API

| # | 화면 | 호출 |
|---|------|------|
| 01 | Main (로그인) | `POST /auth/login` `{email, password}` → `{access_token, user}`. **이메일 없이 가입한 계정은 `email` 칸에 닉네임을 넣으면 돼요**(`@`가 있으면 이메일로 봐요) · [Google로 계속하기] `POST /auth/google` (아래 참고) |
| 02 | Signup (회원가입) | 닉네임 중복 에러: `GET /auth/nickname-available?nickname=` → `{available}` · [가입하기]: `POST /auth/signup` `{nickname, password, tier}` (`email`은 선택) → 로그인과 같은 응답이라 바로 로그인된 상태. 닉네임이 겹치면 409 `nickname_taken` · [Google로 계속하기]도 `POST /auth/google` (실력 선택 없이 바로 온보딩) |
| 03 | Home | `GET /me/home` 한 번이면 돼요 (아래 참고) |
| 04 | Recipes | `GET /recipes?q=&category=&budget=&time=&difficulty=&essential=&sort=latest\|popular` · 카드의 저장 아이콘 `POST/DELETE /recipes/{id}/save` |
| 05 | Filter | 같은 API. "레시피 N개 보기"는 선택한 조건에 `limit=1`을 붙여 부르고 응답의 `total`을 쓰세요 |
| 06 | Battle | **`GET /battles/home?tier=`** 한 번으로 오늘의 대결 + 테마 대결 + 지난 대회 투표 카드까지 다 옴 (아래 참고) |
| 07 | Onboarding (앱 사용법) | 서버 호출 없음 |
| 08 | ProfileEdit | `PATCH /me` `{nickname?, email?, password?, tier?}` · [사진 변경] `PUT /me/avatar` (multipart, 필드명 `file`) |
| 09 | RecipeDetail | `GET /recipes/{id}` · 저장 `POST/DELETE /recipes/{id}/save` · [따라 만들었어요] `POST /recipes/{id}/cook`(1인 1회, +5P) · 댓글 `GET/POST /recipes/{id}/reviews` |
| 10 | Menu | `GET /me`(프로필 요약, `saved_recipe_count`, `review_count`) · 저장한 레시피 `GET /me/saved-recipes` · 최근 본 레시피 `GET /me/recent-recipes` · 내가 쓴 후기 `GET /me/reviews` |
| 11 | Offline | 프론트 화면. 요청이 네트워크 오류로 실패하면 이 화면으로 |
| 12b | CookVerifyCamera (촬영) | 정면 사진 + `BattleOut.required_angle_instruction`이 안내하는 구도 사진, 두 장을 각각 `POST /photos` (multipart, 필드명 `file`) → `{photo_id, photo_url, captured_at, expires_at}`. 이전에 올라온 사진과 같은 사진(재압축·리사이즈 포함)이면 409 `photo_reused` |
| 12 | CookVerify (요리 인증) | "촬영 완료" 미리보기는 두 `photo_url`. [다시 촬영]은 다시 `POST /photos` · [제출] `POST /battles/{battle_id}/entries` `{photo_id, angle_photo_id, dish_name, description}` (JSON) — `battle_id`는 오늘의 대결이면 `GET /battles/current` 응답의 `id`, 테마 대결이면 `GET /battles/current?kind=theme`의 `id` |
| 13 | JoinDone | 제출 응답 그대로: `points_awarded`(참가 10P, **첫 대결이면 +30P 추가**), `entry`("치즈 스크램블 에그 by 나") · [대회 종료 시 알림 받기] `POST /entries/{entry_id}/notify` (다시 누르면 꺼져요) |
| 14 | Vote | `GET /battles/{battle_id}/entries` · [투표하기 +2P] `POST /entries/{entry_id}/vote` (응답에 `points_awarded`) · [취소] `DELETE /entries/{entry_id}/vote` (받은 포인트도 회수, 투표 기간에만 가능) |
| 15 | BattleResult | `GET /battles/{battle_id}/result` |
| 16 | Shop | `GET /shop` |
| 17 | ShopSheet | 필요/보유/교환 후 포인트는 `price_points`와 `points`로 계산 · [교환하기] `POST /shop/items/{id}/exchange` |
| 18 | ShopDone | 위 응답 그대로: `item_name`, `points`(남은 포인트) |
| 14 | Vote (작품 평가) | 투표 직후 그 작품에 댓글 + 비주얼/가성비 별점: `POST /entries/{id}/comments`. 조회 `GET /entries/{id}/comments`, `GET /entries/{id}/comments/mine`, 수정/삭제 `PATCH/DELETE /comments/{id}` |

## Google 로그인 (`POST /auth/google`)

로그인·회원가입 화면 둘 다 같은 엔드포인트예요. 프론트가 Google Identity Services로 받은 ID 토큰을 그대로 보내면 서버가 검증하고 계정을 찾거나 새로 만들어요.

```json
{ "id_token": "eyJhbGci..." }
```

- 이미 그 구글 계정으로 가입했으면 바로 로그인.
- 처음 보는 구글 계정인데 같은 이메일로 이미 가입돼 있으면 그 계정에 연결.
- 완전히 새 계정이면 구글 이름으로 닉네임을 만들고(겹치면 숫자를 붙여요) 새로 가입 — **실력은 `초급`으로 시작해요** (아래 "가정한 것" 5번 참고).
- 서버에 `GOOGLE_CLIENT_ID`가 설정 안 돼 있으면 500 `google_not_configured`. 프론트 `.env`에는 `VITE_GOOGLE_CLIENT_ID`가 필요해요.

## 화면별 메모

**Home** `GET /me/home` → `me`(닉네임, 아바타, `tier_label`="중급", `progress`), `cooking_count_this_month`("이번 달 요리 8회"), `saved_amount_krw`("절약한 식비"), `history`(참가 이력).
- `progress`: `level`(Lv.2), `points`(보유 포인트), `points_to_next_level` → 다음 레벨은 `level + 1`.
- `history` 항목의 `status`: `in_progress`(진행 중) · `ranked` · `void`(무효). `rank`가 없으면 "참가", 있으면 "2등". 빈 배열이면 참가 이력이 없는 상태예요. **테마 대결 참가 이력은 `tier`/`tier_label`이 `null`이에요** — "중급 그룹" 대신 "전체" 같은 문구로 처리해주세요.
- `reviews`(내가 쓴 후기)도 같이 오지만 이번 디자인의 홈에는 없어서 안 써도 돼요.

**Battle** `GET /battles/home?tier=` (생략하면 내 그룹) → `{ daily, theme, voting }`
- `daily`: 그룹별 "오늘의 대결"(실력 그룹 탭마다 `tier`를 바꿔 다시 불러요). `theme`: 전체 공통 "테마 대결"(그룹 탭 상관없이 항상 같은 값 — `tier`가 `null`이에요).
- 두 대결 다 [참가하기 +10P]는 `can_join`이 true일 때만 활성. false면: `is_my_group`이 false → "내 그룹(중급) 대결에만 참가할 수 있어요"(테마는 항상 `is_my_group: true`), `has_joined` → 이미 참가, `phase`가 `cooking`이 아니면 마감.
- `voting`: "지난 대회 투표하기" 카드. 투표 가능한 대회가 없으면 `null`. `group_label`이 `null`이면 테마 대결이에요. `hours_left`로 "투표 마감까지 18시간" 표시.
- 각 배틀의 `phase`: `cooking`(참가 가능) → `voting`(대회 종료 후 24시간, 투표만) → `closed`(집계 완료).

**참가 흐름 (촬영 → 요리 인증 → 제출)**
1. 카메라 화면에서 정면 사진, 이어서 `BattleOut.required_angle_instruction`이 안내하는 구도로 한 장 더, 총 두 장을 각각 `POST /photos`. 서버가 촬영 시각을 찍고, **1시간 안에** [제출]해야 해요(`expires_at`). 지나면 400 `photo_expired` → 다시 촬영. 이전에 올라온 사진과 같은 사진이면 409 `photo_reused` → 다시 촬영.
2. [제출] `POST /battles/{id}/entries` `{"photo_id": 1, "angle_photo_id": 2, "dish_name": "치즈 스크램블 에그", "description": "…"}`. 두 사진은 서로 달라야 하고(400 `same_photo_twice`), 한 사진은 한 번만(정면이든 구도든) 쓸 수 있어요(409 `photo_already_used`).
3. 갤러리 사진 차단은 앱(카메라 API)에서 하는 거라, 서버는 "카메라 업로드 API로 올라온 1시간 이내의, 재사용 아닌 사진"인지만 확인해요.
4. **구도 인증 (신규, 온라인 사진 도용 방지)**: `POST /battles/{id}/entries`는 두 사진을 비전 AI(`services/vision.py`, Claude Vision)로 심사해요 — 같은 음식인지, 두 번째 사진이 정말 요청한 구도인지. 통과 못 하면 400 `angle_mismatch`(`detail`에 이유). `ANTHROPIC_API_KEY`가 `.env`에 없으면 로컬 개발용으로 이 검사를 건너뛰고 항상 통과시켜요.
5. 어떤 구도를 요구할지는 대결이 만들어질 때(주/사이클마다) 무작위로 정해지고 고정돼요(`BattleOut.required_angle`/`required_angle_label`/`required_angle_instruction`, `content.ANGLE_POOL`에서 정의) — 미리 준비해둔 사진으로는 맞추기 어렵게 하는 게 목적이에요.
6. 참가 완료 화면의 [대회 종료 시 알림 받기]는 `POST /entries/{entry_id}/notify`(토글). **MVP: 실제 알림 발송은 없고 원하는지만 저장돼요.**

**투표** — **대회가 끝난 뒤 24시간 동안만** 할 수 있어요(요리 기간에는 아무도 못 해요). `GET /battles/{id}/entries` → 항목마다 `state`로 버튼을 정해요: `votable`=[투표하기 +2P] · `mine`=[내 작품] "투표 불가" · `voted`=내가 투표한 작품 · `vote_done`=이미 다른 작품에 투표 · `unavailable`=투표할 수 없는 상태(요리 기간·마감·다른 그룹). 이미 투표했는지는 `has_voted`. 투표하면 즉시 **+2P**(`VoteOut.points_awarded`). 각 항목에 `comment_count`/`rating_avg`/`rating_count`도 붙어서 "★4.5 (3)" 같은 표시가 가능해요.
**투표 취소 (신규)** — `DELETE /entries/{entry_id}/vote`, 투표 기간에만 가능(404 `vote_not_found`면 그 작품에 투표한 적이 없는 것, 400 `voting_not_started`/`voting_closed`는 기간 밖). 받았던 +2P도 함께 회수되고(`VoteOut.points_awarded`가 `-2`로 옴), 취소 후에는 같은 대결의 다른 작품에 다시 투표할 수 있어요.

**결과** `GET /battles/{id}/result` (투표 기간이 끝나기 전이면 409 `battle_not_finished`)
- `podium`(시상대 1~3등), `top10`, `participants`.
- `me`: `rank`, `rank_points`("+40P", 참가 포인트와 별개), `level_from` → `level_to`, `leveled_up`("레벨 업! Lv.1 → Lv.2"), `can_share_recipe`.
- `top10[].tie`: `first`="동점 · 먼저 제출", `tied`="동점", null=동점 아님 (`submitted_at`으로 "18:02" 표시). 1등 행에는 "레시피 공유" 표시를 보여주세요(`is_winner`, 누가 봐도 true). **누를 수 있는 [레시피 공유] 버튼은 `can_share_recipe`가 true일 때만** — 내가 1등이고 아직 공유하지 않았을 때예요.
- `status`가 `void`면 참가자가 3명 미만이라 순위가 없어요(`podium`, `top10`은 빈 배열, 참가 포인트는 지급됨).
- **참가자가 10명 미만이면 `rank_points`는 절반**만 지급돼요 (표시된 값은 이미 절반이 반영된 실제 지급액).

**작품 평가 (댓글 + 비주얼/가성비/따라하기 쉬움 별점, 투표 화면에 통합)** — 투표하고 나면 그 작품에 바로 댓글 + 별점을 남길 수 있어요. 기획서(`docs/feature-plan-자취요리왕.md`)가 명시한 3항목 그대로예요. 한 사람이 한 작품에 평가 1개(수정 가능), 내 작품엔 불가, 순위엔 영향 없음. **맛은 평가 항목이 아니에요** — 사진만 보고 투표하니 실제로 먹어보지 않고는 맛을 평가할 수 없어서 뺐어요. 세 항목의 평균이 `overall_rating`.
- `POST /entries/{id}/comments` `{ "text": "...", "visual_rating": 5, "value_rating": 4, "ease_rating": 5 }` → 400 `own_entry` / 409 `already_reviewed`
- `GET /entries/{id}/comments?sort=latest|rating_high|rating_low` → `{ summary: {average, visual_average, value_average, ease_average, count, distribution}, items: [...] }` (`rating_high`/`rating_low`는 `overall_rating` 기준)
- `GET /entries/{id}/comments/mine` → 내 평가 또는 `null`
- `PATCH /comments/{id}` `{ text?, visual_rating?, value_rating? }`, `DELETE /comments/{id}` — 본인 또는 관리자만

**Shop** `GET /shop` → `points`, `level`, `items[].state`: `available`=[교환] · `insufficient_points`=비활성 "N P 더 필요해요"(`points_short`) · `locked`=비활성 "Lv.`required_level`부터 교환 가능" · `sold_out_this_month`=비활성 "이번 달 물량이 다 나갔어요" · `monthly_limit_reached`=비활성 "한 달에 2번까지 교환할 수 있어요".

**레시피 필터**(여러 개 선택 가능, 같은 그룹 안은 OR / 그룹끼리는 AND). 같은 파라미터를 여러 번 붙이세요: `?category=rice&category=noodle&budget=under_5000`
- `category`: `rice`(밥) `noodle`(면) `pasta`(파스타) `meat`(고기) `soup`(국·찌개) `side`(반찬) `healthy`(건강식) `dessert`(디저트)
- `budget`: `under_5000`(5,000원 이하) · `5000_to_10000`(5,001~10,000) · `over_10000`(10,000 초과)
- `time`: `le_10` · `le_15` · `le_30`(N분 이하) · `ge_60`(1시간 이상)
- `difficulty`: `beginner` `intermediate` `advanced`
- 빠른 칩: 전체=파라미터 없음 · 5천원 이하=`budget=under_5000` · 15분 이내=`time=le_15` · 초급=`difficulty=beginner` · **자취 필수=`essential=true`**
- `q`는 요리 이름, 재료 이름, "밥 요리 대결" 같은 우승 문구를 검색해요. `sort=popular`는 저장 수 많은 순. `total`이 0이면 "조건에 맞는 레시피가 없어요".
- (조리 도구 `tool=` 필터도 있지만 이번 디자인엔 없어서 안 써도 돼요.)

## 게임 규칙 (서버가 계산하니 화면엔 응답값만 쓰세요)

- **대결 두 종류가 동시에 진행돼요.** `daily`(오늘의 대결): 실력 그룹마다 따로, 매주 월요일 00:00(한국시간) ~ 다음 월요일 00:00, 주제는 8주 주기. `theme`(테마 대결): 전체 공통(그룹 구분 없음), 3일 주기로 돌아가요("망한 요리 대회" 등, `backend/app/content.py`의 `THEME_BATTLES`).
- **참가**: (daily는) 내 그룹 대결만, 대결 하나에 1번. 촬영 사진 필수(재사용된 사진은 거절). 참가하면 즉시 **+10P**, **내 생애 첫 참가면 +30P 추가**.
- **대회 종료 → 24시간 투표 → 결과 발표.** 요리 기간이 끝나면 바로 집계하지 않고, **24시간 동안 투표만 받은 뒤** 결과가 나와요(`VOTING_WINDOW`, `backend/app/content.py`). 투표는 이 24시간 동안만, 대결 하나에 1표, 자기 작품 불가, 하면 **+2P**.
- **결과 집계**: 투표 기간이 끝난 뒤 **첫 API 요청 때 자동으로** 집계돼요(별도 스케줄러 없음). 득표 수 순, 동점이면 먼저 제출한 사람이 앞. **1등 +100P · 2등 +60P · 3등 +40P**가 참가 포인트에 더해져요. **참가자가 10명 미만이면 순위 포인트는 절반**. 참가자가 3명 미만이면 무효.
- **레벨**: 지금까지 **모은 포인트(`total_points`)** 기준이라 상점에서 써도 안 떨어져요. Lv.2=100P, Lv.3=300P, Lv.4=700P, Lv.5=1500P, 그 이후는 레벨마다 +800P.
- **실력 변경**: 정보 수정에서 바꾸면 "다음 대결부터" 적용돼요. 응답의 `pending_tier`, `pending_tier_applies_at`으로 안내할 수 있어요.
- **교환**: 포인트 차감과 교환 내역 저장이 한 번에 일어나요. **상품마다 월 재고 한도**(`monthly_limit`, 매달 자동 초기화)와 **1인당 월 2회** 제한이 있어요. MVP라 실제 발송은 없어요.
- **포인트 유효기간**: 적립 후 **365일**이 지나면 보유(`points`) 포인트에서 자동 소멸해요 (누적 `total_points`·레벨은 그대로). `/me`, `/me/home`, `/shop` 호출 시점에 정리돼요.
- **레시피 공유**: 대결 1등만 `POST /entries/{entry_id}/recipe`로 자기 레시피를 레시피 탭에 올릴 수 있어요.
- **작품 평가**: 한 사람이 한 작품에 평가 1개(수정 가능), 내 작품 불가, 순위엔 영향 없음.
- **로그인 제한**: 같은 로그인 아이디로 10분 안에 10번 틀리면 429 `too_many_attempts`.

## 관리자 (`.env`의 `ADMIN_EMAILS` 이메일로 가입하면 자동 부여, 신규)

시연/발표용 도구예요. 날짜를 기다리지 않고 대결을 즉시 다음 단계로 넘길 수 있어요.

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | /admin/battles/{id}/phase | `{ "phase": "voting" }` 또는 `"cooking"` — 요리/투표 기간 즉시 전환 |
| POST | /admin/battles/{id}/close | 투표 기간까지 통째로 건너뛰고 즉시 집계 → `GET /battles/{id}/result`로 바로 결과 확인 |
| GET | /admin/shop/items | 상품 목록 |
| POST | /admin/shop/items | `{ "name", "price_points", "required_level", "monthly_limit" }` 상품 추가 |
| POST | /admin/shop/items/{id}/deactivate | 상품 비활성화 |

## 에러 코드 (자주 쓰는 것)

`nickname_taken`(409) · `email_taken`(409) · `invalid_credentials`(401) · `too_many_attempts`(429) · `google_not_configured`(500) · `invalid_google_token`(401) · `unsupported_image`(400) · `photo_expired`(400) · `photo_already_used`(409) · `photo_reused`(409 — 재사용된 사진) · `photo_not_found`(404) · `same_photo_twice`(400, 신규 — 정면/구도 사진이 같음) · `angle_mismatch`(400, 신규 — 구도 인증 AI 판정 실패) · `wrong_group`(403) · `battle_closed`(400) · `already_entered`(409) · `voting_not_started`(400) · `voting_closed`(400) · `already_voted`(409) · `own_entry`(400) · `battle_not_finished`(409) · `insufficient_points`(400) · `level_locked`(403) · `sold_out_this_month`(400) · `monthly_limit_reached`(400) · `not_winner`(403) · `already_shared`(409) · `already_reviewed`(409) · `already_cooked`(409, 신규 — 이미 "따라 만들었어요" 인증한 레시피) · `vote_not_found`(404, 신규 — 취소하려는데 그 작품에 투표한 적이 없음) · `not_your_comment`(403) · `admin_only`(403)

## 디자인에서 정해지지 않아 백엔드가 가정한 것

프론트/기획과 확인이 필요해요. 중요한 순서예요.

1. **회원가입에 이메일 칸이 없는데 로그인은 이메일이에요.** 그대로는 로그인할 방법이 없어서, 백엔드는 (a) 가입 때 이메일을 선택으로 받고 (b) 이메일 없는 계정은 로그인 칸에 **닉네임**을 넣으면 되게 했어요. **로그인 입력칸이 `type="email"`이면 닉네임이 막혀요** → 칸을 일반 텍스트로 바꾸거나("이메일 또는 닉네임"), 회원가입에 이메일 칸을 넣는 게 더 안전해요.
2. ~~**포인트 경제가 안 맞아요.**~~ → v4.0에서 해결: 팀 기획 수치(참가 10P·투표 2P·순위 100/60/40P, 레벨 100/300/700/1500P, 상점 120~2600P)로 재설계했어요.
3. **테마 대결이 그룹별인지 전체 공통인지 디자인에 명시가 없어요.** 참가자 41명(테마)이 24명(오늘의 대결)보다 많은 걸 보고 "전체 공통"으로 가정했어요(`tier: null`). 그룹별로 나눠야 한다면 `get_or_create_theme_battle`을 daily처럼 그룹별로 바꿔야 해요.
4. **Google 가입엔 실력 선택 화면이 없어요.** 그래서 구글로 처음 가입하면 **초급으로 자동 시작**하고, 정보 수정에서 바꿀 수 있게 했어요(다음 대결부터 적용). 원하는 기본값이 다르면 `GOOGLE_SIGNUP_DEFAULT_TIER`(`backend/app/routers/auth.py`)에서 바꿔요.
5. **"진행 중인 대결의 출품작 투표"와 "지난 대결 결과" 링크가 이번 대결 홈 화면에서 빠졌어요.** 결과 화면(BattleResult)으로 가는 길이 화면에 없어서, 투표 화면(Vote)에서 결과 화면으로 넘어가는 버튼이 필요할 수 있어요.
6. **"자취 필수"**의 기준이 디자인에 없어요. 지금은 운영자가 직접 지정하는 표시(`is_essential`)이고, 샘플 3개(김치볶음밥·참치마요 덮밥·비빔국수)만 켜뒀어요.
7. **투표 자격**: 디자인엔 조건이 없어서 "내 그룹 대결이면 참가하지 않아도 투표 가능"으로 했어요.
8. **1등 레시피 공유 화면이 없어요.** `POST /entries/{entry_id}/recipe`의 입력 필드는 레시피 상세 화면을 기준으로 정했어요.
9. **"이번 달 요리 N회" = 이번 달 대결 참가 횟수, "절약한 식비" = 횟수 × 4,000원**(목업의 8회 → 32,000원에서 역산)으로 했어요.
10. **샘플 레시피 8개**를 공식 계정 "요리왕" 이름으로 넣어뒀어요(처음엔 1등 레시피가 하나도 없어서 레시피 탭이 비니까요).
11. **없는 것**: 실제 알림 발송(구독 여부만 저장), 알림 설정, "재료로 찾기"(링크만 있고 화면 없음), 친구 기능. 조리 시간 30분 초과~1시간 미만은 필터 칸이 없어서 어디에도 안 잡혀요.
12. **대결 주제 문구**는 계란 요리(daily) 외에는 임시로 썼어요(`backend/app/content.py`의 `BATTLE_THEMES`, `THEME_BATTLES`).
13. **작품 평가(댓글+별점)는 투표 화면(14)에 통합돼 있어요.** 맛은 평가 항목이 아니에요(사진만 보고 투표라서).
14. **사진 재사용 탐지(dHash)의 판정 거리**는 `backend/app/content.py`의 `PHOTO_DUP_HAMMING_DISTANCE`(기본 10/64)에서 조정할 수 있어요.
