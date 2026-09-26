# CookBattle (쿡배틀) — Hello World MVP

매일 주어지는 요리 주제로 사진을 올리고, 투표로 우승자를 가리는 데일리 요리 대결 서비스.
Must Have 4개 기능(일일 주제 / 사진 업로드·대결 등록 / 투표 / 우승자 집계) 백엔드·프론트 뼈대가 모두 동작하는 상태로 만들어져 있습니다.

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
python -m app.seed          # 오늘 날짜 주제 4개 시드 (최초 1회, 이미 있으면 건너뜀)
uvicorn app.main:app --reload --port 8000
```
- API 문서(Swagger): http://localhost:8000/docs — 프론트팀이 실제 요청/응답을 직접 눌러볼 수 있습니다.
- DB는 SQLite 파일(`backend/cookbattle.db`)이라 별도 서버 설치가 필요 없습니다.

### 프론트엔드
```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_URL이 백엔드 주소를 가리키는지 확인
npm run dev
```
- http://localhost:5173 에서 확인. 백엔드가 먼저 떠 있어야 정상 동작합니다.

## 지금 되는 것 (Must Have)

- 회원가입/로그인 (JWT)
- 오늘의 주제 목록 조회
- 주제별 요리 사진 업로드 (1인 1일 1주제 1장 제한)
- 참가자 간 투표 (본인 사진 투표 불가, 주제당 1표 제한)
- 마감 후 득표 기준 우승자 집계 (동점 시 먼저 제출한 사람 우선)

## 다음 회의에서 정할 것 (TBD)

- 오픈 시 노출할 실제 주제 N개 목록 (`backend/app/seed.py`의 `SAMPLE_TOPICS` 수정)
- 주제 마감 시점을 어떻게 정할지 (현재는 `is_closed` 플래그를 수동/배치로 바꾸는 구조만 있고 자동 마감 로직은 없음 — Should Have 단계에서 크론이나 스케줄러 추가 필요)
- 우승자 베네핏(포인트/뱃지) 구체적 정책 — 현재 API 계약에는 없음, Should Have 범위
- 결과 공유 카드 이미지 생성 방식 — Should Have 범위

## Git 협업 팁

- `main` 브랜치는 항상 실행되는 상태로 유지하고, 각자 `feat/backend-xxx`, `feat/frontend-xxx` 같은 브랜치에서 작업 후 PR로 합치는 걸 추천합니다.
- 백엔드가 API 스펙을 바꾸면 `API_CONTRACT.md`를 같이 수정해서 커밋하세요. 프론트팀이 그 커밋만 보고도 뭐가 바뀌었는지 알 수 있게요.
- 이미지 업로드 테스트할 때는 아무 jpg/png 파일이나 써도 됩니다 (8MB 이하).
