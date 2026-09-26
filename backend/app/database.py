import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

log = logging.getLogger("cookbattle")
IS_SQLITE = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 15} if IS_SQLITE else {},
)

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        # WAL: 읽기와 쓰기를 동시에 → 여러 명이 동시에 써도 'database is locked'가 덜 난다
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=15000")
        cur.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def migrate_sqlite() -> None:
    """마이그레이션 도구 대신, 이전 버전 DB에 새로 생긴 컬럼·인덱스만 추가 (DB 삭제 없이 업데이트)."""
    if not IS_SQLITE:
        return
    new_columns = {
        "users": {"token_version": "INTEGER NOT NULL DEFAULT 0"},
        "categories": {"kind": "VARCHAR NOT NULL DEFAULT 'league'"},
        "battles": {"kind": "VARCHAR NOT NULL DEFAULT 'league'", "vote_start_date": "DATE"},
        "recipes": {"cook_minutes": "INTEGER", "difficulty": "VARCHAR", "food_type": "VARCHAR", "tags": "JSON",
                    "updated_at": "DATETIME"},
        "comments": {"rating": "INTEGER", "updated_at": "DATETIME"},
        "submission_images": {"shot_type": "VARCHAR", "phash": "VARCHAR", "taken_at": "DATETIME"},
        "submissions": {"ai_status": "VARCHAR", "ai_result": "JSON"},
        "point_logs": {"expired": "BOOLEAN NOT NULL DEFAULT 0"},
        "shop_items": {"monthly_limit": "INTEGER"},
    }
    with engine.begin() as conn:
        for table, cols in new_columns.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            if not existing:
                continue  # 테이블이 아직 없음 → create_all이 새로 만듦
            for name, ddl in cols.items():
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                'CREATE UNIQUE INDEX IF NOT EXISTS uq_open_battle_per_group ON battles ("group") WHERE is_closed = 0'
            )
    except Exception as e:  # 예전 DB에 이미 중복 대결이 있으면 인덱스 없이 진행
        log.warning("대결 중복 방지 인덱스를 만들지 못했습니다: %s", e)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
