"""Seed a handful of today's topics so the app isn't empty on first run.

Run with: python -m app.seed
"""
import datetime as dt

from .database import Base, SessionLocal, engine
from .models import Topic

SAMPLE_TOPICS = [
    ("한 그릇 파스타", "재료 3개 이하로 만드는 한 그릇 파스타"),
    ("자취 야식", "10분 안에 완성하는 야식 메뉴"),
    ("계란 요리 챌린지", "계란을 메인 재료로 쓴 요리 아무거나"),
    ("에어프라이어 요리", "에어프라이어만 사용한 요리"),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        today = dt.date.today()
        already = db.query(Topic).filter(Topic.active_date == today).count()
        if already:
            print(f"오늘({today}) 주제가 이미 {already}개 있어 시드를 건너뜁니다.")
            return
        for name, desc in SAMPLE_TOPICS:
            db.add(Topic(name=name, description=desc, active_date=today))
        db.commit()
        print(f"오늘({today}) 주제 {len(SAMPLE_TOPICS)}개를 추가했습니다.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
