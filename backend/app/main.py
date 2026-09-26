import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine, migrate_sqlite
from .routers import admin, auth, battles, feedback, friends, meta, recipes, shop, submissions, users, votes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cookbattle")

Base.metadata.create_all(bind=engine)
migrate_sqlite()
os.makedirs(settings.upload_dir, exist_ok=True)

app = FastAPI(title="CookBattle API")

# 토큰은 Authorization 헤더로 보내므로 쿠키(credentials)는 필요 없다 → '*'와 함께 써도 안전
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    """아주 큰 요청은 읽기 전에 거절 (서버 메모리·디스크 보호)."""
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > settings.max_request_mb * 1024 * 1024:
        return JSONResponse(status_code=413, content={"detail": f"요청이 너무 커요 (최대 {settings.max_request_mb}MB)"})
    return await call_next(request)


FIELD_NAMES = {
    "email": "이메일", "password": "비밀번호", "nickname": "닉네임", "skill": "요리 실력", "title": "제목",
    "content": "내용", "rating": "별점", "files": "사진", "file": "사진", "shots": "구도", "steps": "조리 과정",
    "ingredients": "재료", "new_password": "새 비밀번호", "limit": "개수",
}


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    """422 입력 오류를 사람이 읽을 수 있는 한 줄로 (detail은 항상 문자열 → 프론트는 그대로 띄우면 됨)."""
    parts = []
    for err in exc.errors():
        loc = [str(x) for x in err.get("loc", []) if x not in ("body", "query", "path", "form")]
        name = FIELD_NAMES.get(loc[-1], loc[-1]) if loc else "입력값"
        msg = err.get("msg", "").replace("Value error, ", "")
        if err.get("type") == "missing":
            msg = "필수 항목이에요"
        parts.append(f"{name}: {msg}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "입력값을 확인해 주세요 — " + " / ".join(parts[:5]),
            "errors": [{"loc": [str(x) for x in e.get("loc", [])], "msg": e.get("msg", ""), "type": e.get("type", "")}
                       for e in exc.errors()],  # 직렬화 안 되는 ctx는 빼고
        },
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    """예상 못 한 오류: 사용자에겐 안내 문구만, 자세한 내용은 서버 로그에."""
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "서버에 문제가 생겼어요. 잠시 후 다시 시도해 주세요"})


app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

for r in (auth, users, friends, meta, battles, submissions, votes, feedback, recipes, shop, admin):
    app.include_router(r.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# 웹앱(요리왕 화면): http://localhost:8000 에서 바로 열림. API 경로보다 나중에 등록해야 API를 가리지 않는다.
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
if os.path.isdir(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
