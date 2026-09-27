# 요리왕 (COOKUP) — 뭉테크톤 MVP

자취생/기숙사생이 요리하고, 실력이 비슷한 사람끼리(그리고 전체가 함께) 대결(참가 → 대회 종료 후 24시간 투표 → 결과)을 하고, 모은 포인트로 기프티콘을 교환하는 서비스. 이메일/비밀번호 또는 Google로 로그인합니다.
백엔드는 디자인(2026-09-27, 화면 19개) 기준으로 만들어져 있고, 프론트는 디자인 팀 코드를 붙이는 단계입니다.

## 폴더 구조 & 담당 (2 프론트 / 2 백엔드 기준)

```
cookbattle/
  backend/    ← 백엔드 팀 담당 (FastAPI + SQLAlchemy + SQLite)
  frontend/   ← 프론트 팀 담당 (React + Vite)
  API_CONTRACT.md  ← 두 팀이 같이 보는 API 명세. 여기부터 읽으세요.
```

**규칙: 백엔드팀은 `backend/`만, 프론트팀은 `frontend/`만 건드립니다.** 같은 파일을 여러 명이 동시에 클로드로 고치면 깃 충돌이 잦아지니, 폴더 경계를 지키고 API는 `API_CONTRACT.md` 스펙대로 주고받으세요. 스펙을 바꿔야 하면 그 문서부터 고치고 팀에 공유한 다음 코드를 바꾸는 순서로 가면 충돌이 줄어듭니다.

## 실행 방법

### 백엔드
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # 선택. 없어도 개발용 기본값으로 뜹니다
uvicorn app.main:app --reload --port 8000
```
- API 문서(Swagger): http://localhost:8000/docs — 프론트팀이 실제 요청/응답을 직접 눌러볼 수 있습니다.
- Google 로그인을 쓰려면 `.env`에 `GOOGLE_CLIENT_ID`가 필요합니다(없으면 그 기능만 500 에러, 나머지는 정상 동작). 발급 방법은 `API_CONTRACT.md`의 Google 로그인 절 참고.
- DB는 SQLite 파일(`backend/cookbattle.db`)이라 별도 서버 설치가 필요 없고, 테이블·상점 상품·샘플 레시피는 첫 실행 때 자동으로 만들어집니다. 스키마가 바뀌었을 땐(예: 브랜치를 바꾼 뒤) `cookbattle.db`를 지우고 다시 켜세요.
- Windows에서는 venv 활성화가 `.venv\Scripts\activate` 입니다.
- 테스트: `pip install -r requirements-dev.txt` 후 `python -m pytest`

### 프론트엔드
```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_URL이 백엔드 주소를 가리키는지 확인
npm run dev
```
- http://localhost:5173 에서 확인. 백엔드가 먼저 떠 있어야 정상 동작합니다.

## 백엔드가 지금 되는 것 (요리왕 디자인 2026-09-27, 화면 19개 기준)

- 회원가입(닉네임 중복 확인, 실력 초급/중급/상급, 이메일은 선택)/로그인(JWT, 이메일 또는 닉네임) **또는 Google 로그인**, 정보 수정·프로필 사진
- **대결 두 종류가 동시에 진행**: 실력 그룹별 "오늘의 대결"(주간) + 전체 공통 "테마 대결"(3일 주기, 예: 망한 요리 대회)
- 앱 카메라 촬영 인증으로 참가(+1P) → **대회 종료 후 24시간 투표**(1인 1표, 투표하면 +1P) → 결과(1~3등 포인트·레벨업, 3명 미만이면 무효)
- 참가 완료 화면의 "대회 종료 시 알림 받기" 저장 (MVP: 실제 발송 없음)
- 홈(레벨·포인트·참가 이력·내가 쓴 후기), 이번 달 요리 횟수
- 레시피 목록·검색·필터(종류/예산/시간/난이도/자취 필수), 상세, 저장, 댓글(후기), 최근 본 레시피, 1등 레시피 공유
- 포인트로 기프티콘 교환 (MVP: 실제 발송 없음)

화면별 호출 API와 게임 규칙은 `API_CONTRACT.md`에 있습니다.

## 다음 회의에서 정할 것 (TBD)

- **포인트 경제**: 지금 수치로는 커피 기프티콘 하나에 대결을 167번 참가해야 해요 (`API_CONTRACT.md` 맨 아래 2번)
- **테마 대결이 그룹별인지 전체 공통인지** — 지금은 "전체 공통"으로 가정 (`API_CONTRACT.md` 맨 아래 4번)
- **Google 가입 시 실력 기본값**(지금은 초급으로 자동 시작) — 5번
- 보상·레벨 수치, 대결 주제와 문구 (`backend/app/content.py`, 지금 값은 임시)
- 실제 기프티콘 발급 연동 방식, 실제 알림 발송 연동
- `API_CONTRACT.md` 맨 아래 "디자인에서 정해지지 않아 백엔드가 가정한 것" 14가지

## Git 협업 팁

- `main` 브랜치는 항상 실행되는 상태로 유지하고, 각자 `feat/backend-xxx`, `feat/frontend-xxx` 같은 브랜치에서 작업 후 PR로 합치는 걸 추천합니다.
- 백엔드가 API 스펙을 바꾸면 `API_CONTRACT.md`를 같이 수정해서 커밋하세요. 프론트팀이 그 커밋만 보고도 뭐가 바뀌었는지 알 수 있게요.
- 이미지 업로드 테스트할 때는 아무 jpg/png 파일이나 써도 됩니다 (8MB 이하).
