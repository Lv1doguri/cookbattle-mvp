# CookBattle API 계약 (v3.9 — 대결 일정·포인트 체계 개편, 수익화 기획 반영)

베이스 URL: `http://localhost:8000` · Swagger: `http://localhost:8000/docs`
인증: `Authorization: Bearer <access_token>` (가입/로그인/중복확인/`/meta` 제외 전부)
에러: **모든 에러는 `{ "detail": "한국어 안내 문구" }`** → 그대로 토스트/팝업에 띄우면 됩니다.
| 코드 | 의미 | 프론트 처리 |
|---|---|---|
| 400 / 403 / 404 | 규칙 위반, 권한 없음, 없음 | `detail` 표시 |
| 401 | 로그인 필요 (토큰 없음·만료·비밀번호 변경·전체 로그아웃) | **저장된 토큰 삭제 후 로그인 화면으로** |
| 413 | 요청이 너무 큼 (30MB 초과) | `detail` 표시 |
| 422 | 입력 형식 오류. `detail`은 한 줄 문자열 (예: "입력값을 확인해 주세요 — 비밀번호: 영문과 숫자를 모두 포함해 주세요"), 자세한 건 `errors` | `detail` 표시 |
| 429 | 너무 잦은 요청 (로그인 실패 10회/10분, AI 검사 30회/시간 등). `Retry-After` 헤더 | `detail` 표시 |
| 500 | 서버 오류 ("서버에 문제가 생겼어요…") | `detail` 표시 |

> **v3.9 변경 (프론트 수정 필요, 수익화·포인트 기획 반영)**
> - **대결 일정**: 리그 대결 = **요리 1일 + 투표 1일**(총 2일, 예전 7일에서 대폭 단축), 망한 요리 대회 = **요리 3일 + 투표 1일**(총 4일)
> - **포인트 대거 인상**: 가입 **+30P**(신규), 첫 대결 참가 **+30P**(신규, 1회), 대결 참가 1P→**10P**, 투표하면 **+2P**(신규), 순위 1/2/3등 5/4/3P→**100/60/40P**
>   - 참가자가 10명 미만이면 순위 포인트는 **절반**만 지급 (계정 여러 개로 순위 나눠 먹기 방지). 3명 미만이면 기존처럼 대결 자체가 무효
>   - 레시피 후기 작성 **+1P**(신규, 하루 최대 3P), 3주 연속 참가 보너스 2P→**20P**
> - **레벨 기준표 변경**: 포인트당 균등 증가(10P/레벨) → **누적 100/300/700/1500P**에서 Lv.2~5, 그 이후는 800P씩 증가. `GET /meta`의 `points.level_thresholds`로 확인
> - **상점 안전장치**: 상품마다 **월 재고 한도**(`monthly_limit`, 매달 자동 초기화), **1인당 월 교환 횟수 상한**(`GET /meta`의 `shop.max_exchanges_per_month_per_user`), 초과 시 `blocked_reason`에 안내 문구
> - **포인트 유효기간**: 적립 후 12개월 지나면 보유(상점용) 포인트에서 자동 소멸 (누적 포인트·레벨은 그대로) — `GET /users/me`, `GET /users/me/home`, `GET /shop/items` 호출 시점에 정리됨
>
> **v3.8 변경**: `GET /recipes` 응답이 **`{ total, items }`**로 바뀜, 필터(종류·예산·시간·난이도·태그·재료로 찾기)·정렬 추가,
> 레시피에 `cook_minutes`·`difficulty`·`food_type`·`tags`·`badge`·재료 `amount` 추가, **누구나 레시피 올리기/수정/삭제**
>
> **v3.7 변경**: 대결 1주일 = **요리 기간 5일 + 투표 기간 2일**, **투표는 그 대결 참가자만**,
> 리그와 별개로 **망한 요리 대회**(`GET /battles/fail/current`) 동시 진행, 대결 객체에 `phase`·`can_submit`·`can_vote` 등 추가
>
> **v3.6 변경**: 비밀번호 **8자 이상 + 영문·숫자**, 닉네임 **2~12자 한글·영문·숫자·_** (운영진 사칭 단어 금지),
> 422 `detail`이 문자열로 통일, `PATCH /users/me` 응답이 `{ "user", "access_token" }`, `POST /auth/logout-all` 추가

> **v2 → v3 주요 변경 (프론트 수정 필요)**
> - **이메일 + 비밀번호로 로그인**, 닉네임은 가입할 때 따로 설정(중복 불가), 가입 시 **요리 실력(`skill`: low/mid/high)** 필수
> - `topics` → **`battles`**. 실력 그룹별로 대결 1개씩, 카테고리 랜덤 자동 선정. `GET /battles/current`로 내 대결 조회
> - 제출 시 **요리명(`title`) 필수**, **촬영 가이드의 구도별 사진 + `shots`** 필수, 재료비(`ingredient_cost`) 선택. 참가 즉시 +1P
> - 투표: 항목별 → **1인 1표**(본문 없음), 투표 수 공개
> - 포인트: `score` → **`total_points`(누적, 레벨용)** + **`points`(보유, 상점용)**
> - 리그 → 실력 그룹, 기프티콘 추첨 → **상점**
> - 신규: 홈, 튜토리얼, 설정, 레시피 저장/후기/최근 본, 상점

---

## 하단 탭 ↔ API 한눈에 보기

| 탭 | 주요 API |
|---|---|
| 레시피 | `GET /recipes/options`, `GET /recipes`(검색·필터), `GET /recipes/count`, `GET /recipes/{id}`, `POST /recipes`(올리기), 저장 `POST/DELETE /recipes/{id}/save`, 후기 `GET/POST /recipes/{id}/reviews` |
| 대결 | `GET /battles/current`, `GET /battles/fail/current`(망한 요리 대회), `GET /battles/{id}/shot-guide`, `POST /battles/{id}/shot-check`, `POST /battles/{id}/submissions`, `GET /battles/{id}/submissions`, `POST /submissions/{id}/vote`, `GET /battles/{id}/results` |
| 홈 | `GET /users/me/home`, `PATCH /users/me` |
| 상점 | `GET /shop/items`, `POST /shop/items/{id}/exchange` |
| 친구 (홈/메뉴 안) | `GET /users/search`, `POST /friends/requests`, `GET /friends/requests`, `GET /friends`, `GET /friends/ranking`, `GET /friends/activity`, `GET /users/{id}/profile` |
| 메뉴 | `GET /users/me/saved-recipes`, `GET /users/me/recent-recipes`, `GET /reviews`, `PATCH /users/me`(설정), `PATCH /users/me/tutorial` |

---

## 1. 진입: 가입 / 로그인 / 튜토리얼

### GET /meta (인증 불필요)
실력 카드 문구, 포인트 규칙 등. 하드코딩 대신 사용.
```json
{
  "skills": {
    "low":  { "label": "하", "description": "라면 끓이기 정도 가능" },
    "mid":  { "label": "중", "description": "볶음밥, 찌개 같은 기본 요리 가능" },
    "high": { "label": "상", "description": "레시피 없이도 여러 요리를 해 본 경험이 있음" }
  },
  "points": { "signup_bonus": 30, "first_battle_bonus": 30, "participation": 10, "vote": 2,
              "rank": [100, 60, 40], "rank_fail": [50, 30, 20], "rank_full_min_participants": 10,
              "level_thresholds": [0, 100, 300, 700, 1500], "recipe_complete": 1,
              "recipe_review": 1, "recipe_review_daily_cap": 3, "streak_weeks": 3, "streak_bonus": 20,
              "invite_inviter": 2, "invite_invitee": 1, "expiry_days": 365 },
  "battle": { "league_cooking_days": 1, "league_vote_days": 1, "fail_cooking_days": 3, "fail_vote_days": 1,
              "min_participants": 3, "hide_votes_until_closed": false },
  "photos": { "shot_types": { "front": { "label": "...", "guide": "..." }, ... }, "fixed_shots": ["front", "keyword"],
              "random_shot_count": 1, "min_side": 400, "max_bytes": 8388608 },
  "delivery_avg_price": 15000,
  "tutorial_steps": 4,
  "ai_check": { "enabled": true, "mode": "strict" },
  "shop": { "max_exchanges_per_month_per_user": 2 }
}
```

### GET /auth/check-nickname?nickname=지원
`{ "nickname": "지원", "available": false, "reason": "이미 사용 중인 닉네임입니다" }` — 가입 화면 **중복 확인** 버튼용
- 형식(2~12자 한글·영문·숫자·_), 금지어("관리자", "운영자", "admin" 등 운영진 사칭), 중복을 한 번에 검사
- `available`이 false면 `reason`을 입력칸 아래에 표시

### GET /auth/check-email?email=a@test.com
`{ "email": "a@test.com", "available": true }` — 이메일 중복 확인용

> 중복 확인을 안 누르고 가입해도 서버가 가입 시점에 다시 검사합니다 (400 응답).

### POST /auth/signup
```json
{ "email": "a@test.com", "password": "pass1234", "nickname": "지원", "skill": "low", "invite_code": "A1B2C3" }
```
- email 형식 검사(틀리면 422), **password 8자 이상 + 영문·숫자 포함**, nickname 규칙은 위와 같음, `invite_code`는 선택
- 같은 IP에서 1시간에 30회 넘게 가입 시도하면 429
- 400: "이미 가입된 이메일입니다" / "이미 사용 중인 닉네임입니다" / "요리 실력(상/중/하)을 선택해 주세요" / "존재하지 않는 초대 코드입니다"

**응답** (login과 동일)
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1, "email": "a@test.com", "nickname": "지원", "skill": "low", "skill_label": "하",
    "level": 1, "total_points": 0, "points": 0,
    "next_level_points": 10, "points_to_next_level": 10, "level_progress": 0.0,
    "is_admin": false, "invite_code": "9F3K2A",
    "tutorial_step": 0, "tutorial_completed": false, "notifications_enabled": true
  }
}
```
- `total_points`: 누적 (레벨 계산, 줄지 않음) / `points`: 보유 (상점에서 차감)
- `level_progress`: 레벨 진행 바 0.0~1.0, `points_to_next_level`: "다음 레벨까지 N포인트"

### POST /auth/login
`{ "email": "a@test.com", "password": "pass1234" }` → 위와 동일. 401 "이메일 또는 비밀번호가 올바르지 않습니다"
- 같은 이메일로 10분에 10번 틀리면 429 (잠시 잠금), 성공하면 초기화

### POST /auth/logout-all
모든 기기에서 로그아웃 (지금까지 발급된 토큰 전부 무효). 이후 요청은 401 → 다시 로그인

### PATCH /users/me/tutorial
- 다음 장 넘길 때: `{ "step": 2 }` (중간 이탈 후 재접속 시 `user.tutorial_step`부터 이어보기)
- 완료/건너뛰기: `{ "completed": true }`
- 메뉴 > 튜토리얼 다시 보기: `{ "step": 0, "completed": false }`
- 첫 접속 판단: `user.tutorial_completed === false`면 튜토리얼 표시

---

## 2. 대결 탭

### 대회 일정 (종류별로 다름)
```
리그 대결 (총 2일):        1일차: 요리 기간 │ 2일차: 투표 기간 │ 종료 → 결과·포인트 지급 → 새 대결 자동 개최
망한 요리 대회 (총 4일):   1~3일차: 요리 기간 │ 4일차: 투표 기간 │ 종료 → 결과·포인트 지급 → 새 대회 자동 개최
```
- **요리 기간**: 참가(사진 올리기)만 가능, 투표 불가
- **투표 기간**: 참가 불가, **그 대결에 참가한 사람만** 투표 가능 (1인 1표, 내 작품 제외)
- 참가작이 신고로 숨김 처리되면 투표도 불가
- 대회 종류 2가지가 **동시에 따로** 진행됨

| 종류 | `kind` | 참가 대상 | API | 기간(요리+투표) | 1/2/3등 포인트 | 우승 레시피 공유 |
|---|---|---|---|---|---|---|
| 리그 대결 | `league` | 같은 실력(하/중/상)끼리 | `GET /battles/current` | 1일+1일 | 100 / 60 / 40 | O |
| 망한 요리 대회 | `fail` | 리그 구분 없이 **전체** | `GET /battles/fail/current` | 3일+1일 | 50 / 30 / 20 | X |

둘 다 참가 시 +10P, 투표하면 +2P. **참가자가 10명 미만이면 순위 포인트는 절반만** 지급(위 표는 10명 이상 기준 수치),
3명 미만이면 대결 자체가 무효(참가 포인트만 지급). 정확한 기간·포인트 숫자는 `GET /meta`의 `battle`/`points`를 참고하세요.

### GET /battles/current — 내 리그 대결 · GET /battles/fail/current — 망한 요리 대회
진행 중인 대회가 없으면 서버가 해당 종류의 주제 중에서 랜덤으로 새 대회를 엽니다.
```json
{
  "id": 3,
  "kind": "league", "kind_label": "리그 대결",
  "group": "low", "group_label": "하",
  "category": { "id": 1, "name": "계란 요리", "description": "계란을 메인 재료로 쓴 요리" },
  "start_date": "2026-09-25",
  "cooking_end_date": "2026-09-25",
  "vote_start_date": "2026-09-26",
  "end_date": "2026-09-26",
  "phase": "cooking", "phase_label": "요리 기간", "phase_days_left": 0,
  "days_left": 1,
  "verification_keyword": "김치",
  "is_closed": false, "is_void": false,
  "submission_count": 2,
  "has_submitted": false, "has_voted": false,
  "can_submit": true,
  "can_vote": false,
  "vote_block_reason": "투표는 09/26부터 시작해요 (지금은 요리 기간)",
  "is_my_group": true
}
```
- 망한 요리 대회는 `kind: "fail"`, `group: "fail"`, `group_label: "전체"`, 요리 3일+투표 1일이라 기간이 더 김
- **버튼 표시는 `can_submit` / `can_vote`로** 판단하고, 투표 버튼이 막혔을 땐 `vote_block_reason`을 아래에 표시
  - "투표는 09/26부터 시작해요 (지금은 요리 기간)" / "이 대결에 참가한 사람만 투표할 수 있어요" / "이미 투표하셨습니다" / "이미 끝난 대결입니다"
- 상단 배너 예: `phase_label` + "D-`phase_days_left`" (요리 기간 D-0, 투표 기간 D-0 …)
- `verification_keyword`: 인증샷에 이 단어를 종이에 써서 같이 찍도록 안내

### GET /battles/active
진행 중인 모든 대회: 리그 3개(하/중/상) + 망한 요리 대회 (구경용. 투표는 각 대회 참가자만)

### GET /battles/{id} · GET /battles/history?mine=true&group=low
단일 대결 / 끝난 대결 목록 (`mine=true`: 내가 참가한 것만)

### GET /battles/{battle_id}/shot-guide — 촬영 가이드 (참가 화면 진입 시)
이번 대결에서 **내가 찍어야 할 구도 목록**. 고정 구도(정면 완성샷, 키워드 인증샷) + **사용자·대결마다 랜덤한 구도 1개**.
새로고침해도 같은 결과가 나옵니다.
```json
{
  "battle_id": 3,
  "verification_keyword": "김치",
  "shots": [
    { "order": 1, "shot_type": "front",   "label": "완성샷 (정면 45°)", "guide": "완성된 요리를 45도 각도에서, 그릇 전체가 나오게 찍어 주세요", "is_random": false },
    { "order": 2, "shot_type": "top",     "label": "위에서 (탑뷰)",     "guide": "요리 바로 위에서 수직으로 내려다보며 찍어 주세요", "is_random": true },
    { "order": 3, "shot_type": "keyword", "label": "키워드 인증샷",     "guide": "오늘의 인증 키워드를 종이에 써서 요리 옆에 두고 함께 찍어 주세요", "is_random": false }
  ],
  "min_side": 400,
  "tips": ["구도마다 카메라 위치를 바꿔서 새로 찍어 주세요. ...", "..."]
}
```
프론트 권장 UI: `shots` 순서대로 **구도별 촬영 칸**(라벨 + 가이드 문구)을 보여주고, 칸마다 사진 1장씩 받기.
모바일이면 `<input type="file" accept="image/*" capture="environment">`로 카메라를 바로 열면 EXIF 원본이 유지되어 "촬영 인증"을 받기 쉽습니다.

### POST /battles/{battle_id}/shot-check — 사진 미리 검사 (구도 칸마다)
사용자가 구도 칸에 사진을 넣자마자 호출 → 칸에 ✅/❌ 표시. **저장하지 않음.**
`multipart/form-data`: `file`(1장), `shot`(구도 키)
```json
{
  "ok": false,
  "problems": ["'키워드 인증샷'에서 '김치' 메모가 보이지 않아요. 키워드를 종이에 크게 써서 함께 찍어 주세요"],
  "warnings": [],
  "ai_status": "failed",
  "ai_summary": "요리는 잘 보이지만 키워드 메모가 없어요",
  "ai_note": "종이 메모가 보이지 않아요",
  "time_verified": true
}
```
- `ok`: true면 이 칸 통과. `problems`: 제출 시 거절될 문제. `warnings`: 참고용(advisory 모드)
- AI 호출이 있어 **수 초 걸릴 수 있음** → 칸에 로딩 표시 권장
- AI 검사는 사용자당 **1시간 30회**까지 (미리 검사 + 제출 합산, 초과 시 429)
- 같은 사진끼리 비교·"같은 요리인지"는 최종 제출 때만 검사

### POST /battles/{battle_id}/submissions — 참가하기
`multipart/form-data`
| 필드 | 필수 | 설명 |
|---|---|---|
| `files` | O | 구도별 사진 (가이드의 `shots` 개수만큼), jpg/png/webp, 장당 8MB, 짧은 변 400px 이상 |
| `shots` | O | 각 사진의 구도 키. **`files`와 같은 순서로** 같은 개수 |
| `title` | O | 요리명 (40자) |
| `description` | | 설명 (300자) |
| `ingredient_cost` | | 재료비(원, 숫자) |

```js
const fd = new FormData();
guide.shots.forEach((shot) => {
  fd.append("files", photos[shot.shot_type]);   // 구도별로 받은 사진
  fd.append("shots", shot.shot_type);
});
fd.append("title", "폭신 계란말이");
fd.append("ingredient_cost", "2000");
await client.post(`/battles/${id}/submissions`, fd);
```

**서버 검사 (순서대로, 실패 시 400 + 안내 문구)**
| 검사 | 거절 문구 예시 |
|---|---|
| 구도 구성 | "필요한 사진이 빠졌어요: 위에서 (탑뷰)" / "'완성샷 (정면 45°)' 구도가 두 번 들어갔어요" / "이번 대결에 필요 없는 구도예요: side" |
| 형식 | "'위에서 (탑뷰)' 사진: 이미지 파일이 아닙니다" |
| 품질 | "... 사진이 너무 작아요 (짧은 변 400px 이상)" / "... 너무 어두워요" / "... 비어 있거나 한 가지 색만 있어요" |
| 같은 사진 중복 | "'완성샷'와 '위에서' 사진이 같은 사진이에요. 구도를 바꿔서 다시 찍어 주세요" |
| 재사용·도용 | "'완성샷' 사진은 이미 올라온 적 있는 사진이에요. 새로 찍어 주세요" (내 예전 사진, 남의 사진 모두) |
| 촬영 시각 | "'...' 사진은 대결 기간이 아닐 때 찍은 사진이에요 (촬영일 2020-01-01)" |

- 같은 사진 판별: 지각 해시(dHash) — 크기 변경·재압축·밝기 조절해도 같은 사진으로 잡힘
- 촬영 시각: EXIF 촬영일이 **있으면** 대결 기간(±1일)인지 확인. **없으면 거절하지 않고** `photo_verified: false`
- 저장 시 **EXIF(위치정보 포함)를 모두 제거**하고 JPEG로 재저장 → 자취방 위치 노출 방지
- **이미지 인식 AI** (Claude Vision, `.env`에 `ANTHROPIC_API_KEY` 설정 시):
  - 사진마다 **음식이 있는지**, **요구한 구도가 맞는지**(정면/탑뷰/측면/클로즈업/조리과정), 키워드 인증샷에 **키워드 메모가 보이는지**
  - 전체 사진이 **같은 요리인지**, **화면 촬영·캡처·광고 이미지** 같은지, 카테고리에 맞는지(기록만)
  - `AI_CHECK_MODE=strict`: 문제 있으면 거절 (구도 불일치는 AI 확신도 0.7 이상일 때만) / `advisory`: 거절 없이 기록 / `off`
  - 키가 없거나 AI 호출이 실패하면 **거절하지 않고** `ai_check.status`를 `skipped`/`error`로 기록 (서비스 중단 방지)
  - 거절 문구 예: "AI 사진 검사를 통과하지 못했어요: '위에서 (탑뷰)' 사진이 요구한 구도와 달라요 (AI 판단: 옆에서) / 사진들이 서로 다른 요리처럼 보여요"

**응답** → "참가 완료! +10P" 알림 (`points_earned`는 참가 10P + 그 사람의 **첫 대결 참가라면 +30P**가 합산된 값)
```json
{ "submission": { ...제출물 객체... }, "points_earned": 10, "level": 1, "leveled_up": false }
```
기타 에러: 403 "내 실력 그룹의 대결에만 참가할 수 있어요"(리그 대결만) / 400 "이미 참가한 대결입니다",
"요리 기간이 끝났어요. 지금은 투표 기간이에요 (~09/26)", "이미 끝난 대결입니다"

### GET /battles/{battle_id}/submissions — 출품작 목록
사용자마다 랜덤 순서(새로고침해도 유지)
```json
{
  "id": 7, "battle_id": 3, "user_id": 2, "nickname": "민준", "user_level": 1,
  "title": "스크램블 에그", "description": "", "ingredient_cost": 3000,
  "image_url": "/uploads/aaa.jpg", "image_urls": ["/uploads/aaa.jpg", "/uploads/bbb.jpg", "/uploads/ccc.jpg"],
  "images": [
    { "url": "/uploads/aaa.jpg", "shot_type": "front", "shot_label": "완성샷 (정면 45°)", "time_verified": true },
    { "url": "/uploads/bbb.jpg", "shot_type": "top", "shot_label": "위에서 (탑뷰)", "time_verified": true },
    { "url": "/uploads/ccc.jpg", "shot_type": "keyword", "shot_label": "키워드 인증샷", "time_verified": true }
  ],
  "photo_verified": true,
  "ai_verified": true,
  "ai_check": { "status": "passed", "summary": "모든 사진 확인 완료", "warnings": [] },
  "created_at": "2026-09-25T03:12:00",
  "vote_count": 2,
  "has_voted": false,
  "is_mine": false, "is_hidden": false, "comment_count": 1,
  "rating_avg": 4.5, "rating_count": 2
}
```
- `images`: 구도별 사진 (상세 화면에서 라벨과 함께 슬라이드로), `photo_verified`가 true면 "📷 촬영 인증" 배지
- `ai_verified`가 true면 "🤖 AI 인증" 배지. `ai_check`는 AI를 안 쓰던 시절 작품이면 null
- 투표 버튼 비활성화 조건: `is_mine` 이거나 대결의 `has_voted`가 true
- `created_at`은 UTC → 화면 표시 시 +9시간(한국)

### POST /submissions/{submission_id}/vote — 투표 (본문 없음)
`{ "submission_id": 7, "vote_count": 3 }`
- **투표 기간에만, 그 대결 참가자만** 가능
- 400: "내 작품에는 투표할 수 없어요" / "이미 투표하셨습니다" / "투표는 09/30부터 시작해요 (지금은 요리 기간)" / "이미 끝난 대결입니다"
- 403: "이 대결에 참가한 사람만 투표할 수 있어요" / "내 작품이 신고로 숨김 처리되어 투표할 수 없어요"

### GET /battles/{battle_id}/results — 결과 (종료 후에만, 전엔 400)
```json
{
  "battle": { ...대결 객체... },
  "is_void": false,
  "podium": [
    { "submission_id": 7, "user_id": 1, "nickname": "지원", "title": "계란말이",
      "image_url": "/uploads/a.jpg", "vote_count": 2, "rank": 1, "rank_points": 100 }
  ],
  "entries": [ ...전체 순위, 형식 동일... ],
  "my_result": {
    "submission_id": 7, "rank": 1, "points_earned": 112,
    "level_before": 1, "level_after": 2, "leveled_up": true,
    "can_share_recipe": true
  }
}
```
- 순위: 득표순, 동점이면 먼저 제출한 사람 우선. 0표는 순위 포인트 없음
- `podium`: 시상대(1~3등, 1표 이상)
- `my_result`: 참가 안 했으면 null. `points_earned`는 이 대결로 받은 참가+투표+순위 포인트 합계 (첫 대결 보너스는 별도 집계라 미포함).
  `leveled_up`이면 **레벨업 축하 팝업**, `can_share_recipe`면 "레시피 공유하기" 버튼
- `is_void`: 참가자 3명 미만 → 대결 무효, 시상대 없음, 참가 포인트만 지급 ("참가자가 부족해 무효 처리됐어요")
- **참가자가 10명 미만이면 `rank_points`는 절반만 지급됨** (표시된 값은 이미 절반이 반영된 실제 지급액)
- 망한 요리 대회는 `rank_points`가 50/30/20(10명 이상 기준)이고 `can_share_recipe`는 항상 false
- 대결이 끝나면 `GET /battles/current`가 자동으로 새 카테고리 대결을 엽니다

### 작품 평가 (댓글 + 별점)
대결에 올라온 요리에 **평가 내용 + 별점(1~5)**을 남깁니다. 한 사람이 한 작품에 1개(수정 가능), 내 작품에는 불가.
진행 중/종료된 대결 모두 가능. **별점은 순위에 영향 없음** (순위는 투표로만 결정).

**POST /submissions/{submission_id}/comments**
```json
{ "content": "계란이 폭신해 보여요!", "rating": 5 }
```
400: "내 작품에는 평가를 남길 수 없어요" / "이미 평가를 남겼어요. 기존 평가를 수정해 주세요" · 422: 별점이 1~5가 아님

**GET /submissions/{submission_id}/comments?sort=latest|rating_high|rating_low**
```json
{
  "summary": { "average": 4.5, "count": 2, "distribution": { "5": 1, "4": 1, "3": 0, "2": 0, "1": 0 } },
  "comments": [
    {
      "id": 3, "submission_id": 7, "user_id": 2,
      "nickname": "민준",
      "content": "계란이 폭신해 보여요!",
      "rating": 5,
      "created_at": "2026-09-25T05:03:00",
      "created_at_display": "2026-09-25 14:03",
      "is_edited": false, "is_mine": false
    }
  ]
}
```
- 화면 표시: **닉네임 · `created_at_display` · 별점(★ `rating`개) · 평가 내용**
- `created_at_display`는 한국 시간으로 변환된 문자열이라 그대로 띄우면 됨
- `is_edited`가 true면 "(수정됨)" 표시, `is_mine`이면 수정/삭제 버튼 노출
- `rating`이 null인 건 이전 버전에서 쓴 댓글 (별점 없이 표시)

**GET /submissions/{id}/comments/mine** — 내 평가 (없으면 `null`) → 작성 폼 / 수정 폼 전환용
**PATCH /comments/{id}** — `{ "content": "...", "rating": 4 }` 바꿀 것만 (본인만)
**DELETE /comments/{id}** — 본인 또는 관리자

출품작 객체(`GET /battles/{id}/submissions`)에도 `rating_avg`(평균, 없으면 null), `rating_count`, `comment_count`가 포함되어 카드에 "★ 4.5 (2)" 표시 가능.

### 신고
- `POST /submissions/{id}/report` `{ "reason": "..." }` → 3회 누적 시 자동 숨김

---

## 3. 레시피 탭 (디자인: 04 레시피 목록 · 05 필터 · 레시피 상세)

### GET /recipes/options — 필터·올리기 화면 선택지 (인증 불필요)
칩을 하드코딩하지 말고 이걸로 그리면 됩니다. 각 칩의 `params`를 **그대로 `GET /recipes` 쿼리에 붙이면** 필터가 적용돼요.
```json
{
  "food_types":   [{ "key": "rice", "label": "밥" }, { "key": "noodle", "label": "면" }, { "key": "pasta", "label": "파스타" },
                   { "key": "meat", "label": "고기" }, { "key": "soup", "label": "국·찌개" }, { "key": "side", "label": "반찬" },
                   { "key": "healthy", "label": "건강식" }, { "key": "dessert", "label": "디저트" }],
  "difficulties": [{ "key": "easy", "label": "초급" }, { "key": "normal", "label": "중급" }, { "key": "hard", "label": "상급" }],
  "tags": ["자취 필수", "전자레인지", "원팬", "야식", "도시락", "다이어트"],
  "budgets": [{ "label": "5,000원 이하", "params": { "max_cost": 5000 } },
              { "label": "5,000~10,000원", "params": { "min_cost": 5000, "max_cost": 10000 } },
              { "label": "10,000원 이상", "params": { "min_cost": 10000 } }],
  "times":   [{ "label": "10분 이하", "params": { "max_minutes": 10 } }, { "label": "15분 이하", "params": { "max_minutes": 15 } },
              { "label": "30분 이하", "params": { "max_minutes": 30 } }, { "label": "1시간 이상", "params": { "min_minutes": 60 } }],
  "quick_filters": [{ "label": "전체", "params": {} }, { "label": "5천원 이하", "params": { "max_cost": 5000 } },
                    { "label": "15분 이내", "params": { "max_minutes": 15 } }, { "label": "초급", "params": { "difficulty": "easy" } },
                    { "label": "자취 필수", "params": { "tag": "자취 필수" } }],
  "sorts": [{ "key": "latest", "label": "최신순" }, { "key": "popular", "label": "인기순" },
            { "key": "cheap", "label": "저렴한순" }, { "key": "quick", "label": "빠른순" }]
}
```

### GET /recipes — 레시피 목록 (검색 + 필터 + 정렬)
| 파라미터 | 화면 | 예시 |
|---|---|---|
| `q` | 검색창 "재료, 요리 이름, 키워드" (띄어쓰기 = 모두 포함) | `q=김치` |
| `type` | 필터 > 종류 (쉼표로 여러 개, 하나라도 맞으면) | `type=rice,noodle` |
| `min_cost` / `max_cost` | 필터 > 예산 | `max_cost=5000` |
| `min_minutes` / `max_minutes` | 필터 > 조리 시간 | `max_minutes=15` |
| `difficulty` | 필터 > 난이도 (쉼표로 여러 개) | `difficulty=easy` |
| `tag` | 빠른 칩 "자취 필수" 등 (쉼표 = 모두 포함) | `tag=자취 필수` |
| `have` | 필터 > **재료로 찾기** (가진 재료 쉼표 구분) | `have=계란,김치,밥` |
| `source` | 공식 / 대결 우승 / 사용자 | `source=winner` |
| `sort` | 최신순 ▾ | `latest`(기본) · `popular`(저장 많은) · `cheap` · `quick` |
| `limit` / `offset` | 무한 스크롤 | `limit=20&offset=20` |

```json
{
  "total": 8,
  "items": [ {
    "id": 3, "title": "김치볶음밥", "description": "자취생 국민 메뉴",
    "ingredients": [ { "name": "김치", "amount": "1컵", "price": 1500 }, { "name": "밥", "amount": "1공기", "price": 1300 } ],
    "steps": ["김치를 잘게 썬다.", "팬에 기름을 두르고 김치를 볶는다."],
    "estimated_cost": 3500, "cook_minutes": 15,
    "difficulty": "easy", "difficulty_label": "초급",
    "food_type": "rice", "food_type_label": "밥",
    "tags": ["자취 필수", "원팬"], "tools": "프라이팬",
    "source": "winner", "badge": "밥 요리 대결 1등",
    "author_id": 1, "author_nickname": "요리왕", "is_official": false, "is_mine": false,
    "source_submission_id": 7, "image_url": "/uploads/a.jpg",
    "save_count": 12, "review_count": 3, "completion_count": 1,
    "saved_by_me": false, "completed_by_me": false,
    "matched_ingredients": null, "missing_ingredients": null,
    "created_at": "..."
  } ]
}
```
**카드 표시 매핑 (04 레시피 목록)**
- 배지: `badge` ("밥 요리 대결 1등" / "요리왕 공식", 사용자 레시피는 null → 배지 없음)
- 제목: `title` / 시계 줄: "`cook_minutes`분 · ₩`estimated_cost`" / 아래 줄: "`difficulty_label` · 저장 `save_count`"
- 북마크: `saved_by_me` (누르면 저장/해제 API)
- "N개 결과": `total`
- 사진이 없으면(`image_url` null) `food_type`별 기본 아이콘·색

**재료로 찾기** (`have`): 가진 재료가 하나라도 쓰이는 레시피만, **부족한 재료가 적은 순**. 각 레시피에
`matched_ingredients`(있는 재료), `missing_ingredients`(더 필요한 재료)가 채워져서 "식용유만 있으면 돼요" 같은 표시 가능.

### GET /recipes/count — 필터 결과 개수
`GET /recipes`와 같은 파라미터 → `{ "total": 30 }`. 필터 화면 하단 **"레시피 30개 보기"** 버튼용 (칩을 누를 때마다 호출).

### GET /recipes/{id} — 상세 (호출 시 '최근 본 레시피'에 기록)
응답은 목록의 레시피 객체와 같음.
**상세 화면 매핑**: 작성자 줄 "`author_nickname` · `badge`", 통계 3칸 "예상 재료비 약 `estimated_cost`원 / 조리 시간 `cook_minutes`분 / 난이도 `difficulty_label`",
재료 목록 `ingredients[].name` + `amount`, 조리 과정 `steps` (번호는 순서대로), 하단 댓글 입력 → 후기 API

### POST /recipes — 레시피 올리기 (로그인한 누구나)
```json
{
  "title": "라면 볶이",
  "description": "야식으로 딱",
  "ingredients": [ { "name": "라면", "amount": "1봉", "price": 1000 }, { "name": "떡", "amount": "한 줌", "price": 800 } ],
  "steps": ["라면을 삶는다", "양념에 볶는다"],
  "cook_minutes": 12,
  "difficulty": "easy",
  "food_type": "noodle",
  "tags": ["야식"],
  "tools": "냄비"
}
```
- **필수**: `title`, `ingredients`(1개 이상), `steps`(1개 이상), `cook_minutes`(1~600), `difficulty`, `food_type`
- `ingredients[].price`를 입력하면 `estimated_cost`(예상 재료비) = 합계로 **자동 계산** (가격 없는 재료는 제외)
- `tags`는 `options.tags` 목록 안에서만 (최대 6개)
- 사진은 만든 뒤 **`POST /recipes/{id}/image`** (multipart `file` 1장, EXIF 위치정보 제거)
- 1시간에 10개까지. 관리자가 `?official=true`로 올리면 "요리왕 공식" 레시피
- 레시피를 올려도 포인트는 없음 (도배 방지)

### PATCH /recipes/{id} — 내 레시피 수정 · DELETE /recipes/{id} — 삭제
- 수정은 바꿀 항목만 (재료를 바꾸면 예상 재료비 재계산). 작성자 또는 관리자만 (403)
- 삭제하면 저장·후기·조회 기록도 함께 삭제

### GET /users/me/recipes — 내가 올린 레시피

### 저장
- `POST /recipes/{id}/save` / `DELETE /recipes/{id}/save` → 레시피 객체 (`saved_by_me`, `save_count` 갱신)

### 후기 (= 상세 화면 하단 댓글)
- `GET /recipes/{id}/reviews`, `POST /recipes/{id}/reviews` `{ "content": "..." }`, `DELETE /reviews/{id}`
```json
{ "id": 1, "recipe_id": 3, "recipe_title": "김치볶음밥", "user_id": 2, "nickname": "민준",
  "content": "따라해 봤는데 맛있어요", "created_at": "...", "is_mine": false }
```

### 우승자 레시피 공유 — POST /submissions/{submission_id}/recipe
결과 화면 `can_share_recipe`가 true일 때. 본문은 `POST /recipes`와 같음.
"`카테고리` 대결 1등" 배지가 붙고, 대표 사진은 대결 사진으로 자동 지정 (`POST /recipes/{id}/image`로 교체 가능).
대결 결과의 `entries[].recipe_id`가 채워져서 TOP 목록의 **"레시피 공유"** 표시·이동에 사용.
403 "대결 우승자만 레시피를 공유할 수 있어요" / 400 "이미 레시피를 공유했어요", 망한 요리 대회 작품은 400

### POST /recipes/{id}/complete — 따라하기 완료 인증
multipart `file` 1장 → +1P (레시피당 1회), 홈의 이번 달 요리 횟수에 포함

---

## 4. 홈 탭

### GET /users/me/home
```json
{
  "user": { ...user 객체 (레벨, 진행 바, 포인트)... },
  "this_month": { "cook_count": 3, "saved_money": 27500, "delivery_avg_price": 15000 },
  "history": [
    { "battle_id": 3, "category_name": "계란 요리", "start_date": "...", "end_date": "...",
      "submission_id": 7, "title": "계란말이", "image_url": "/uploads/a.jpg",
      "is_closed": true, "is_void": false, "rank": 1, "points_earned": 6 }
  ],
  "my_reviews": [ ...후기 객체... ]
}
```
- `cook_count`: 이번 달 대결 참가 + 레시피 따라하기 완료 횟수
- `saved_money`: Σ(배달 평균 15,000원 − 재료비). 재료비를 입력한 요리만 계산
- `history`가 비어 있으면 "첫 대결에 참가해 보세요!" + 대결 바로가기
- `rank`는 진행 중이거나 무효인 대결이면 null

### PATCH /users/me — 정보 수정 / 설정
```json
{ "nickname": "새닉네임", "current_password": "pass1234", "new_password": "newpass", "notifications_enabled": false }
```
필요한 필드만 보내면 됩니다. 비밀번호 변경은 `current_password` 필수. 실력(skill)은 변경 불가.
**응답**: `{ "user": { ...user 객체... }, "access_token": null }`
- 비밀번호를 바꾸면 **다른 기기의 로그인은 모두 풀리고**, `access_token`에 새 토큰이 옵니다 → 저장된 토큰을 이걸로 교체하세요

### GET /users/me · GET /users/me/points (포인트 적립 내역)

---

## 5. 상점 탭

### GET /shop/items
```json
[ { "id": 2, "name": "아메리카노 기프티콘", "description": "", "price": 240, "min_level": 2,
    "stock": null, "can_exchange": false, "blocked_reason": "2레벨부터 교환 가능" } ]
```
`blocked_reason`: "N포인트 더 필요해요" / "N레벨부터 교환 가능" / "품절" / "이번 달 물량이 다 나갔어요 (다음 달 1일 재입고)" /
"한 달에 N번까지 교환할 수 있어요" → `can_exchange`가 false면 버튼 비활성화 + 이 문구 표시

### POST /shop/items/{id}/exchange
`{ "id": 1, "item_id": 2, "item_name": "...", "price": 240, "created_at": "...", "points_left": 5 }` → 교환 완료 팝업
보유 포인트(`points`)만 차감, 누적 포인트·레벨은 그대로. MVP라 실제 발송 없음.
안전장치: 상품별 **월 재고 한도**(매달 자동 초기화, `POST /admin/shop/items`의 `monthly_limit`으로 설정)와
**1인당 월 교환 횟수 상한**(`GET /meta`의 `shop.max_exchanges_per_month_per_user`, 기본 2회)이 있습니다.
보유 포인트는 **적립 후 12개월이 지나면 자동 소멸**합니다 (누적 포인트·레벨은 그대로).

### GET /users/me/exchanges — 교환 내역

---

## 6. 메뉴 탭
- 저장한 레시피 `GET /users/me/saved-recipes`
- 최근 본 레시피 `GET /users/me/recent-recipes` (최대 20개)
- 후기 모음 `GET /reviews?limit=30`
- 설정(알림) `PATCH /users/me` `{ "notifications_enabled": true }`
- 튜토리얼 다시 보기 `PATCH /users/me/tutorial` `{ "step": 0, "completed": false }`

---

## 7. 친구

**흐름**: 닉네임 검색 → 친구 요청 → 상대가 수락 → 친구 목록·친구 랭킹·친구 활동에 표시
- 초대 코드로 가입하면 초대한 사람과 **자동으로 친구**
- 서로 동시에 요청하면 바로 친구
- 거절·취소·삭제하면 기록이 지워져 다시 요청 가능. 친구 최대 100명

### GET /users/search?nickname=고수 — 닉네임 검색 (부분 일치, 최대 20명)
```json
[ { "user_id": 5, "nickname": "고수", "level": 2, "skill": "high", "skill_label": "상",
    "relation": "none", "request_id": null } ]
```
`relation`에 따라 버튼 표시:
| relation | 버튼 |
|---|---|
| `none` | [친구 요청] |
| `request_sent` | [요청 취소] → `DELETE /friends/requests/{request_id}` |
| `request_received` | [수락] [거절] → `/friends/requests/{request_id}/accept`, `/reject` |
| `friend` | [친구 ✓] (프로필에서 삭제) |

### POST /friends/requests — 친구 요청
`{ "nickname": "고수" }` 또는 `{ "user_id": 5 }`
```json
{ "status": "pending", "request_id": 3, "friend": { ...UserBrief... }, "message": "고수님에게 친구 요청을 보냈어요" }
```
- 상대가 이미 나에게 요청했으면 `"status": "accepted"` (바로 친구)
- 400: "이미 친구예요" / "이미 친구 요청을 보냈어요" / "나 자신에게는 친구 요청을 보낼 수 없어요" · 404: "해당 닉네임의 사용자가 없어요"

### GET /friends/requests?box=received|sent — 받은/보낸 요청
```json
[ { "id": 3,
    "from_user": { "user_id": 1, "nickname": "지원", "level": 2, "skill": "low", "skill_label": "하" },
    "to_user":   { "user_id": 5, "nickname": "고수", "level": 2, "skill": "high", "skill_label": "상" },
    "created_at": "...", "created_at_display": "2026-09-25 14:03" } ]
```
받은 요청 개수를 알림 뱃지로 쓰면 좋아요.

### POST /friends/requests/{id}/accept · POST /friends/requests/{id}/reject · DELETE /friends/requests/{id}(보낸 요청 취소)

### GET /friends — 친구 목록 (닉네임순)
```json
[ { "user_id": 2, "nickname": "민준", "level": 1, "skill": "low", "skill_label": "하",
    "total_points": 6, "friends_since": "...", "last_cooked_at": "2026-09-25 14:03", "battle_count": 2 } ]
```
`last_cooked_at`: 마지막 대결 참가 시각 ("3일 전 요리" 같은 표시용), 없으면 null

### DELETE /friends/{user_id} — 친구 삭제

### GET /friends/ranking — 친구 랭킹 (나 포함, 누적 포인트순)
```json
[ { "rank": 1, "user_id": 1, "nickname": "지원", "level": 2, "skill": "low", "skill_label": "하",
    "total_points": 11, "win_count": 1, "is_me": true } ]
```

### GET /friends/activity?limit=20 — 친구 활동 피드
```json
[ { "submission_id": 7, "battle_id": 3, "user": { ...UserBrief... }, "category_name": "계란 요리",
    "title": "스크램블", "image_url": "/uploads/a.jpg", "created_at_display": "2026-09-25 14:03",
    "message": "민준님이 '계란 요리' 대결에 '스크램블'(으)로 참가했어요" } ]
```
탭하면 `GET /submissions/{submission_id}`로 작품 상세 → 투표·평가로 연결

### GET /users/{user_id}/profile — 다른 사람 프로필
```json
{ "user_id": 5, "nickname": "고수", "level": 2, "skill": "high", "skill_label": "상",
  "total_points": 12, "battle_count": 3, "win_count": 1, "friend_count": 4,
  "relation": "friend", "request_id": 3,
  "recent_submissions": [ { "submission_id": 9, "battle_id": 4, "category_name": "라면 변신",
                            "title": "짜파구리", "image_url": "/uploads/b.jpg", "created_at_display": "..." } ] }
```
출품작·후기·랭킹에서 닉네임을 누르면 이 프로필로 이동하면 자연스러워요.

---

## 관리자 (`.env`의 ADMIN_EMAILS 이메일로 가입)

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | /admin/battles/{id}/phase | **시연용 기간 전환** `{ "phase": "voting" }` 또는 `"cooking"` (날짜 기다릴 필요 없음) |
| POST | /admin/battles/{id}/close | **시연용 즉시 종료** → 순위 포인트 지급 |
| POST | /admin/battles/start | `{ "group": "low", "category_id": null }` 새 대회 (group: low/mid/high/**fail**, null이면 랜덤) |
| GET/POST | /admin/categories | 주제 목록/추가 `{ "name", "description", "kind": "league" 또는 "fail" }` |
| POST | /admin/shop/items | 상품 추가 `{ "name", "description", "price", "min_level", "stock", "monthly_limit" }` |
| GET | /admin/exchanges | 전체 교환 내역 |
| GET | /admin/ai/status | 이미지 인식 AI 설정 확인 (키 설정 여부, 모드, 모델) |
| POST | /admin/submissions/{id}/hide?hidden=true | 작품 숨김/복구 |

## 이미지 URL
`/uploads/파일명` 상대경로 → `${API_BASE_URL}${image_url}`
