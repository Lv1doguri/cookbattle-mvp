# CookBattle (쿡배틀) — 뭉테크톤 MVP

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
cp .env.example .env        # 선택. 없어도 개발용 기본값으로 뜹니다
uvicorn app.main:app --reload --port 8000
```
- API 문서(Swagger): http://localhost:8000/docs — 프론트팀이 실제 요청/응답을 직접 눌러볼 수 있습니다.
- DB는 SQLite 파일(`backend/cookbattle.db`)이라 별도 서버 설치가 필요 없고, 테이블과 상점 상품은 첫 실행 때 자동으로 만들어집니다. 스키마가 바뀌었을 땐 `cookbattle.db`를 지우고 다시 켜세요.
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

## 백엔드가 지금 되는 것 (COOKUP 디자인 15화면 기준)

- 회원가입/로그인(JWT), 요리 실력(초급/중급/고급) 선택
- 카메라 인증 사진 업로드 → 레시피 포함 게시물 (재료·조리방법·비용·시간·난이도)
- 홈 피드(추천/팔로잉), 좋아요·저장·댓글·답글, 팔로우, 프로필
- 실력 단계별 오늘의 대결 · 리더보드 · XP/레벨/코인 지급
- 레시피 검색·필터·우승 레시피·평점
- 상점 · 코인으로 쿠폰 구매 · 내 쿠폰 · 쿠폰 사용

화면별 호출 API와 게임 규칙은 `API_CONTRACT.md`에 있습니다.

## 다음 회의에서 정할 것 (TBD)

- 요일별 대결 주제와 단계별 문구 (`backend/app/content.py`의 `WEEKLY_THEMES`, 지금 문구는 임시)
- 보상 수치: 일반 게시 XP/코인, 하루 보상 한도, 대결 보상, 레벨당 필요 XP (`backend/app/content.py`)
- 실제 기프티콘 발급 연동 방식 (지금 쿠폰 번호는 앱에서 만든 임의 번호)
- `API_CONTRACT.md` 맨 아래 "디자인에서 정해지지 않아 백엔드가 가정한 것" 7가지

## Git 협업 팁

- `main` 브랜치는 항상 실행되는 상태로 유지하고, 각자 `feat/backend-xxx`, `feat/frontend-xxx` 같은 브랜치에서 작업 후 PR로 합치는 걸 추천합니다.
- 백엔드가 API 스펙을 바꾸면 `API_CONTRACT.md`를 같이 수정해서 커밋하세요. 프론트팀이 그 커밋만 보고도 뭐가 바뀌었는지 알 수 있게요.
- 이미지 업로드 테스트할 때는 아무 jpg/png 파일이나 써도 됩니다 (8MB 이하).
