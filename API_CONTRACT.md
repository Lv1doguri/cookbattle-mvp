# CookBattle API 계약

베이스 URL(로컬): `http://localhost:8000`
인증: `Authorization: Bearer <access_token>` 헤더 (회원가입/로그인 제외 전부 필요)

프론트엔드 개발 시, 백엔드 API가 아직 준비되지 않았다면 아래 응답 예시를 그대로 mock 데이터로 사용해서 화면부터 만들면 됩니다. 실제 연동 시 base URL만 바꿔 끼우면 됩니다.

---

## 인증

### POST /auth/signup
회원가입. 가입 시 요리 실력 등급(`skill_tier`)을 필수로 선택합니다. 이후 주제/제출/투표/결과는 모두 같은 등급 사용자끼리만 묶입니다(하수는 하수끼리, 중수는 중수끼리, 고수는 고수끼리).

**요청**
```json
{ "email": "a@test.com", "password": "pass1234", "nickname": "지원", "skill_tier": "beginner" }
```
`skill_tier`는 `"beginner"`(하) / `"intermediate"`(중) / `"advanced"`(상) 중 하나.

**응답 200**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": 1, "email": "a@test.com", "nickname": "지원", "skill_tier": "beginner" }
}
```

**에러**: 400 (이미 가입된 이메일), 422 (`skill_tier` 누락/잘못된 값)

### POST /auth/login
로그인. 요청/응답 형태는 signup과 동일(email, password만 받음). 에러 401(이메일/비밀번호 불일치).

---

## 주제(Topics)

### GET /topics/today
오늘 활성화된 주제 목록.

**응답 200**
```json
[
  {
    "id": 1,
    "name": "한 그릇 파스타",
    "description": "재료 3개 이하로 만드는 한 그릇 파스타",
    "active_date": "2026-09-22",
    "is_closed": false,
    "submission_count": 2,
    "has_submitted": false
  }
]
```

### GET /topics/{topic_id}
주제 상세 (위와 동일한 형태 단일 객체). 에러 404.

---

## 제출(Submissions)

### POST /topics/{topic_id}/submissions
요리 사진 업로드 및 대결 등록. `multipart/form-data`, 필드명 `file`.

**응답 200**
```json
{
  "id": 1,
  "topic_id": 1,
  "user_id": 1,
  "nickname": "지원",
  "image_url": "/uploads/xxxx.jpg",
  "created_at": "2026-09-22T12:53:21",
  "vote_count": 0,
  "is_mine": true,
  "has_voted": false
}
```

**에러**: 400(이미 제출함 / 마감된 주제 / 오늘 주제 아님 / 지원하지 않는 형식 / 용량초과), 404(주제 없음)

### GET /topics/{topic_id}/submissions
해당 주제의 모든 제출물 목록 (투표 화면에서 사용). 응답은 위 객체의 배열.

---

## 투표(Votes)

### POST /submissions/{submission_id}/vote
투표. 본문 없음.

**응답 200**
```json
{ "submission_id": 2, "vote_count": 1 }
```

**에러**: 400(본인 제출물 / 이미 이 주제에 투표함), 404(제출물 없음)

규칙: 한 유저는 주제당 1표만 행사 가능(어떤 제출물에 투표했는지와 무관하게 주제 단위로 제한).

---

## 결과(Results)

### GET /topics/{topic_id}/results

**응답 200**
```json
{
  "topic_id": 1,
  "topic_name": "한 그릇 파스타",
  "is_closed": false,
  "entries": [
    { "submission_id": 1, "nickname": "지원", "image_url": "/uploads/xxxx.jpg", "vote_count": 3, "rank": 1, "is_winner": true },
    { "submission_id": 2, "nickname": "민준", "image_url": "/uploads/yyyy.jpg", "vote_count": 1, "rank": 2, "is_winner": false }
  ]
}
```

동점 처리: 득표수가 같으면 업로드 시간이 빠른 쪽이 상위 순위.

---

## 이미지 URL

`image_url`은 `/uploads/파일명` 형태의 상대경로로 내려옵니다. 프론트에서는 `${API_BASE_URL}${image_url}`로 조합해서 `<img src>`에 사용하세요.
