# CookBattle / 요리왕(COOKUP) — 뭉테크톤 MVP

매일(또는 3일) 주어지는 요리 주제로 사진을 올리고, 투표로 우승자를 가리는 데일리 요리 대결 서비스.

## v4.0 — 백엔드 통합 업데이트

팀에 두 개의 독립적인 백엔드(`feat/backend-full-a`, `feat/backend-full-b`)와 새 19화면 프론트(`feat/frontend-cookup`, `backend-full-a`에 이미 연결되어 검증됨)가 각각 만들어졌어요. 이번 업데이트는 **backend-full-a를 기본으로** 하고 (이미 실제 프론트와 연결되어 있어서), **backend-full-b의 강점을 이식**했습니다.

- **관리자 데모 도구** — `/admin/battles/{id}/phase`, `/admin/battles/{id}/close`로 날짜를 기다리지 않고 즉시 요리→투표→종료 전환 (발표용)
- **사진 재사용 탐지** — 지각 해시(dHash)로 이전 사진 재사용(리사이즈/재압축 포함) 차단
- **작품 댓글 + 별점** — 배틀 출품작에 평가 남기기 (`/entries/{id}/comments`)
- **포인트 경제 재설계** — 이전 버전이 스스로 지적했던 "포인트 경제가 안 맞다" 문제를 팀 기획 수치(참가 10P·투표 2P·순위 100/60/40P)로 해결
- **상점 안전장치** — 상품별 월 재고 한도, 1인당 월 교환 횟수 제한, 포인트 유효기간(365일)

자세한 내용과 팀에서 확인해야 할 가정 사항은 **`API_CONTRACT.md`**를 보세요. **친구 기능은 이번 통합에서 빠졌어요** (19개 화면 어디에도 화면이 없어서 — 필요하면 추가 가능).

## 폴더 구조

```
cookbattle/
  backend/    ← FastAPI + SQLAlchemy + SQLite. 지금 작업 중인 것
  frontend/   ← 예전 v1 API 기준 React 스켈레톤 (지금 백엔드와 안 맞음, 손대지 않음)
  API_CONTRACT.md  ← API 명세. 여기부터 읽으세요.
```

> `feat/frontend-cookup` 브랜치의 19화면 프론트가 이 백엔드와 실제로 맞는 프론트예요. 이 브랜치의 `frontend/`는 그 이전 버전(v1)이라 이 백엔드와 API가 안 맞습니다.

## 실행 방법

### 백엔드
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env        # ADMIN_EMAILS, GOOGLE_CLIENT_ID 등 설정
uvicorn app.main:app --reload --port 8000
```
- 첫 실행 시 테이블 생성 + 상점 상품 4개 + 공식 레시피 8개가 자동으로 들어갑니다 (시드 스크립트 별도 실행 불필요).
- API 문서(Swagger): http://localhost:8000/docs
- DB는 SQLite 파일(`backend/cookbattle.db`)이라 별도 서버 설치가 필요 없습니다.
- 관리자 계정: `.env`의 `ADMIN_EMAILS`에 적은 이메일로 가입하면 자동으로 관리자가 됩니다.

### 테스트
```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```
36개 테스트(pytest, 시간 고정·동시성 테스트 포함) 전부 통과해야 합니다.

### 프론트엔드 (이 백엔드와 맞는 것은 `feat/frontend-cookup` 브랜치)
```bash
git checkout feat/frontend-cookup -- frontend   # 또는 그 브랜치를 따로 체크아웃
cd frontend
npm install
npm run dev
```
- http://localhost:5173 에서 확인. `VITE_API_URL` 기본값이 `http://localhost:8000`이라 별도 `.env` 없이도 동작합니다.
- 구글 로그인을 쓰려면 프론트 `.env`에 `VITE_GOOGLE_CLIENT_ID`, 백엔드 `.env`에 `GOOGLE_CLIENT_ID`가 필요합니다 (없어도 이메일/닉네임 로그인은 정상 동작).

## 지금 되는 것

**Must**
- 이메일(선택) + 닉네임 + 비밀번호 로그인, 이메일 없으면 닉네임으로 로그인. 구글 로그인
- 가입 시 실력(초급/중급/상급) 선택 → 대결 그룹. 정보 수정에서 바꾸면 "다음 주부터" 적용
- 오늘의 대결(그룹별, 주간) + 테마 대결(전체 공통, 3일 주기, 예: "망한 요리 대회") 동시 진행
- 카메라로 찍은 사진만 인정(갤러리 차단), 1시간 안에 제출, 재사용된 사진 차단(지각 해시), 참가 즉시 +10P(첫 대결이면 +30P 추가)
- 대회 종료 → 24시간 투표 창 → 자동 집계(득표순, 동점은 먼저 제출한 사람). 1/2/3등 +100/60/40P(참가자 10명 미만이면 절반), 3명 미만이면 무효
- 작품에 댓글 + 별점(1~5) 남기기
- 레벨(누적 포인트 100/300/700/1500P 구간, 이후 800P씩), 우승자 레시피 공유

**Should**
- 레시피: 검색·필터(종류/예산/시간/난이도/자취필수)·정렬, 저장, 후기, 최근 본 레시피
- 홈: 레벨 진행바, 이번 달 요리 횟수, 절약한 식비, 참가 이력, 내가 쓴 후기
- 상점: 포인트 교환, 레벨 제한, **월 재고 한도 + 1인당 월 2회 제한**(적자 방지), 포인트 유효기간(365일)
- 관리자: 대결 강제 전환/종료, 상점 상품 추가

규칙 숫자(포인트, 레벨 기준, 대결 기간, 사진 재사용 판정 거리 등)는 전부 `backend/app/content.py`에 있습니다.

## Git 협업 팁

- `main` 브랜치는 항상 실행되는 상태로 유지하고, 각자 `feat/backend-xxx`, `feat/frontend-xxx` 같은 브랜치에서 작업 후 PR로 합치는 걸 추천합니다.
- 백엔드가 API 스펙을 바꾸면 `API_CONTRACT.md`를 같이 수정해서 커밋하세요.
- 이미지 업로드 테스트할 때는 서로 다른 사진을 쓰세요 (같은 사진은 재사용 탐지에 걸립니다).
