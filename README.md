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

## 🚀 한 번에 실행하기 (화면 + 서버)

**Windows**: `backend` 폴더의 **`start.bat`을 더블클릭**하세요. 끝!
**Mac/Linux**: `backend` 폴더에서 `./start.sh`

처음 한 번은 설치 때문에 1~2분 걸리고, 브라우저가 자동으로 **http://localhost:8000** 을 엽니다.
- 필요한 것: Python 3.10 이상 (설치 시 "Add python.exe to PATH" 체크). **Node.js는 필요 없어요.**
- 화면(웹앱)은 `backend/web/`에 있고 서버가 같이 띄워 줍니다. API 문서는 http://localhost:8000/docs
- 끄기: 까만 창에서 `Ctrl + C` (또는 창 닫기)
- 휴대폰으로 보기: 같은 와이파이에서 `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`으로 켜고 `http://내PC_IP:8000`

**시연 순서 (웹앱에서)**
1. `admin@test.com`으로 가입 (`.env`의 ADMIN_EMAILS → 메뉴에 "관리자" 생김) + 다른 브라우저/시크릿 창으로 같은 실력의 계정 2개 더 가입
2. 대결 탭 → 참가하기 → 구도별 사진 촬영(업로드) → 제출
3. 관리자 계정: 메뉴 → 관리자 → **투표 기간**으로 전환
4. 각 계정: 출품작 보고 투표 → 작품 눌러 별점 평가
5. 관리자: **종료·결과** → 시상대, 포인트, 레벨업 확인 → 우승자는 "우승 레시피 공유하기"
6. 레시피 탭에서 검색·필터·재료로 찾기, 상점에서 교환

> `frontend/` 폴더(React)는 프론트팀 작업용으로 그대로 두었어요. 예전 API(v1) 기준이라 현재 서버와는 맞지 않습니다.
> 화면별 API 사용 예시는 `backend/web/app.js`를 참고하세요.

## 실행 방법

### 백엔드
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # ADMIN_EMAILS 등 설정
python -m app.seed          # 카테고리 10개 + 공식 레시피 2개 + 상점 상품 시드 (이미 있으면 건너뜀)
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

## 지금 되는 것 (백엔드, 9/25 기획서 기준)

**Must**
- 이메일+비밀번호 로그인, 가입 시 닉네임(중복 확인) + 요리 실력(상/중/하) 설정 → 대결 그룹 고정 배정
- 1주일 대회 = **요리 기간 5일 + 투표 기간 2일**, 투표는 **그 대회 참가자만**
- 리그(하/중/상)별 대결 + 리그와 별개인 **망한 요리 대회**(전체 참가) 동시 진행, 주제 랜덤 자동 선정
- 다중 구도 인증샷(정면 + 랜덤 구도 + 키워드 인증샷)+요리명+설명으로 참가 → 즉시 +1P, 1인 1표 투표, 내 작품 투표 차단
- 인증샷 검사: 해상도·밝기, 같은 사진 중복/재사용 차단(지각 해시), EXIF 촬영일 확인, 저장 시 위치정보 제거
- 이미지 인식 AI(Claude Vision): 음식 여부, 구도 일치, 키워드 메모 인식, 같은 요리인지, 화면 촬영/광고 이미지 판별 → `AI 인증` 배지
- 종료 시 득표순 1~3등 → 5/4/3P, 동점은 먼저 제출한 사람 우선, 3명 미만이면 무효(참가 포인트만)
- 누적 포인트 10P마다 레벨업, 결과 화면에 레벨업 여부 제공
- 데모용 관리자 수동 종료

**Should**
- 레시피: 누구나 올리기·수정·삭제, 우승자 공유(배지), 검색(재료·이름·키워드), 필터(종류·예산·조리 시간·난이도·태그), 재료로 찾기, 정렬(최신·인기·저렴·빠른), 저장, 후기
- 홈: 프로필, 레벨 진행 바, 참가 이력, 이번 달 요리 횟수, 절약한 식비(배달 평균 − 재료비), 내가 쓴 후기
- 상점: 보유 포인트로 교환(레벨 제한/품절/포인트 부족 안내), 교환 내역 기록
- 튜토리얼 진행 저장(이어보기/건너뛰기/다시 보기)
- 메뉴: 저장한 레시피, 최근 본 레시피, 후기 모음, 알림 설정

**그 외 (기획 보완)**
- 인증 키워드, 이미지 실제 내용 검사, 신고 누적 자동 숨김, 작품 댓글 피드백
- [Could] 3주 연속 참여 보너스, 친구 초대 포인트, 레시피 따라하기 완료 인증
- 친구: 닉네임 검색, 요청/수락/거절/취소, 초대 가입 시 자동 친구, 친구 랭킹, 친구 활동 피드, 공개 프로필

규칙 숫자(포인트, 레벨 기준, 대결 기간, 최소 인원, 배달 평균 금액 등)는 전부 `backend/app/rules.py`에 있습니다.

## ⚠️ 이전 버전에서 업데이트한 경우

DB 구조가 바뀌었습니다. `backend/cookbattle.db`를 **삭제한 뒤** `python -m app.seed` → 서버 실행 순서로 하세요.
`.env`도 `.env.example`을 다시 복사하세요 (관리자 지정: `ADMIN_EMAILS=admin@test.com`).

## 보안 설정 (v3.6)

- **업데이트 후 `pip install -r requirements.txt` 한 번 실행** (토큰 라이브러리가 PyJWT로 바뀜)
- `JWT_SECRET`을 `.env`에 안 넣으면 `backend/.jwt_secret`에 랜덤 키를 자동 생성해서 씀 (git 제외됨)
- 관리자: `.env`의 `ADMIN_EMAILS`로 가입하거나, 이미 가입한 계정을 `python -m app.make_admin 이메일`로 지정
  - ⚠️ 서버를 인터넷에 공개할 땐 `ADMIN_EMAILS`를 비우고 `make_admin`만 쓰세요 (이메일 인증이 없어서 먼저 가입한 사람이 관리자가 될 수 있음)
- 배포 시 `.env`에 `CORS_ORIGINS=https://프론트주소`로 제한
- 로그인 실패 10회/10분 잠금, AI 검사 30회/시간, 가입 30회/시간/IP, 요청 본문 30MB 제한
- 비밀번호 변경·`/auth/logout-all` 시 기존 토큰 전부 무효
- 업로드 사진은 전부 검사 후 EXIF(위치정보) 제거한 JPEG로 재저장

## 이미지 인식 AI 켜기

1. https://console.anthropic.com 에서 API 키 발급 (사용량만큼 과금, 참가 1건당 사진 3장 분석)
2. `backend/.env`에 `ANTHROPIC_API_KEY=sk-ant-...` 입력 → 서버 재시작
3. Swagger `GET /admin/ai/status`에서 `"enabled": true` 확인
- 키는 **절대 git에 올리지 마세요** (`.env`는 .gitignore 대상인지 확인)
- 키가 없으면 AI 검사만 건너뛰고 나머지는 정상 동작 (발표 중 네트워크 문제 대비)
- `AI_CHECK_MODE=advisory`로 두면 거절 없이 판정 결과만 기록

## 시연 순서 (Swagger)

1. `admin@test.com`(ADMIN_EMAILS) + 일반 계정 3개를 같은 실력(`low`)으로 가입
2. 각자 `GET /battles/current` → `GET /battles/{id}/shot-guide` → 가이드 구도대로 `POST /battles/{id}/submissions`
3. 관리자로 `POST /admin/battles/{id}/phase` `{"phase": "voting"}` → 참가자끼리 `POST /submissions/{id}/vote`
4. 관리자로 `POST /admin/battles/{id}/close` → `GET /battles/{id}/results`로 시상대·레벨업 확인
5. 우승자로 `POST /submissions/{id}/recipe` → 다른 계정으로 레시피 저장·후기 → `GET /users/me/home`, 상점 교환

전체 흐름 자동 확인: `pip install httpx` 후 `python -m tests.smoke_test`

## Git 협업 팁

- `main` 브랜치는 항상 실행되는 상태로 유지하고, 각자 `feat/backend-xxx`, `feat/frontend-xxx` 같은 브랜치에서 작업 후 PR로 합치는 걸 추천합니다.
- 백엔드가 API 스펙을 바꾸면 `API_CONTRACT.md`를 같이 수정해서 커밋하세요. 프론트팀이 그 커밋만 보고도 뭐가 바뀌었는지 알 수 있게요.
- 이미지 업로드 테스트할 때는 아무 jpg/png 파일이나 써도 됩니다 (8MB 이하, 짧은 변 400px 이상, 구도마다 다른 사진).
