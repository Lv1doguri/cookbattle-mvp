"""대결 카테고리 10개, 공식 레시피 2개, 상점 상품을 넣는다 (이미 있으면 건너뜀).

실행: python -m app.seed
대결 자체는 넣지 않는다 — /battles/current 를 처음 부르면 그룹별로 랜덤 카테고리 대결이 자동으로 열린다.
"""
from .database import Base, SessionLocal, engine
from .models import Category, Recipe, ShopItem

# 망한 요리 대회 주제 (리그 구분 없이 전체 참가, 가장 '처참한' 작품이 우승)
FAIL_CATEGORIES = [
    ("망한 요리 자랑", "처참하게 망한 요리를 자랑해 주세요. 가장 공감 가는 실패작이 우승!"),
    ("이게 뭐였더라?", "원래 뭘 만들려고 했는지 알아볼 수 없는 요리"),
    ("탄 요리 대잔치", "타 버린 요리 모음. 어떻게 태웠는지 설명도 적어 주세요"),
]

CATEGORIES = [
    ("계란 요리", "계란을 메인 재료로 쓴 요리"),
    ("라면 변신", "라면을 색다르게 업그레이드하기"),
    ("5,000원 한 끼", "재료비 5,000원 이하로 만든 한 끼"),
    ("전자레인지 요리", "불 없이 전자레인지만으로 완성"),
    ("10분 요리", "조리 시간 10분 이내"),
    ("참치캔 요리", "참치캔을 활용한 요리"),
    ("편의점 재료 요리", "편의점에서 산 재료만으로"),
    ("냉장고 털이", "남은 재료로 만드는 한 끼"),
    ("두부 요리", "두부를 메인 재료로"),
    ("야식 대결", "밤에 먹고 싶은 간단 야식"),
]

def _r(title, desc, food_type, difficulty, minutes, tags, ingredients, steps, tools=""):
    return {
        "title": title, "description": desc, "food_type": food_type, "difficulty": difficulty,
        "cook_minutes": minutes, "tags": tags, "tools": tools,
        "ingredients": [{"name": n, "amount": a, "price": p} for n, a, p in ingredients],
        "estimated_cost": sum(p for _, _, p in ingredients if p is not None) or None,
        "steps": steps,
    }


# 공식 레시피 (디자인 04 레시피 목록의 예시 + 필터 확인용으로 종류·가격·시간·난이도를 골고루)
RECIPES = [
    _r("김치볶음밥", "자취생 국민 메뉴. 신김치일수록 맛있어요", "rice", "easy", 15, ["자취 필수", "원팬"],
       [("김치", "1컵", 1500), ("밥", "1공기", 1300), ("계란", "1개", 500), ("식용유", "1큰술", 200)],
       ["김치를 잘게 썬다.", "팬에 기름을 두르고 김치를 볶는다.", "밥을 넣고 고루 볶는다.", "계란 프라이를 올린다."], "프라이팬"),
    _r("참치마요 덮밥", "불 없이 만드는 든든한 한 그릇", "rice", "easy", 10, ["자취 필수", "전자레인지"],
       [("햇반", "1개", 1200), ("참치캔", "1개", 1300), ("마요네즈", "2큰술", 200), ("김가루", "약간", 100)],
       ["참치캔 기름을 따라 버린다.", "참치에 마요네즈와 간장을 섞는다.", "데운 밥 위에 올리고 김가루를 뿌린다."], "전자레인지"),
    _r("크림 파스타", "우유로 만드는 간단 크림소스", "pasta", "normal", 20, ["원팬"],
       [("파스타면", "100g", 800), ("우유", "200ml", 600), ("베이컨", "3줄", 2000), ("양파", "1/2개", 400),
        ("슬라이스 치즈", "1장", 700)],
       ["면을 7분 삶는다.", "베이컨과 양파를 볶는다.", "우유와 치즈를 넣고 끓인다.", "면을 넣고 소스와 섞는다."], "냄비, 프라이팬"),
    _r("비빔국수", "새콤달콤 여름 별미", "noodle", "easy", 15, ["자취 필수"],
       [("소면", "100g", 600), ("고추장", "2큰술", 300), ("오이", "1/2개", 700), ("계란", "1개", 500),
        ("김치", "1/2컵", 700), ("설탕·식초", "약간", 200)],
       ["소면을 3분 삶아 찬물에 헹군다.", "고추장·설탕·식초로 양념장을 만든다.", "면과 양념, 채 썬 오이·김치를 비빈다."], "냄비"),
    _r("전자레인지 계란찜", "그릇 하나, 5분이면 끝나는 기숙사 필수 메뉴", "side", "easy", 5, ["전자레인지", "자취 필수"],
       [("계란", "2개", 800), ("물", "100ml", None), ("대파", "약간", 200), ("소금", "한 꼬집", None)],
       ["그릇에 계란을 풀고 물·소금을 섞는다.", "랩을 씌우고 구멍을 뚫는다.", "1분 30초 돌리고 저은 뒤 1분 더 돌린다."], "전자레인지"),
    _r("제육볶음", "도시락 반찬으로도 최고", "meat", "normal", 25, ["도시락"],
       [("돼지 앞다리살", "200g", 4500), ("양파", "1/2개", 400), ("고추장", "2큰술", 300), ("간장·설탕", "약간", 300),
        ("대파", "1/2대", 500)],
       ["고기에 양념을 버무려 10분 재운다.", "양파와 함께 센 불에 볶는다.", "대파를 넣고 1분 더 볶는다."], "프라이팬"),
    _r("된장찌개", "밥 한 공기 뚝딱", "soup", "normal", 30, [],
       [("된장", "1.5큰술", 300), ("두부", "1/2모", 900), ("애호박", "1/3개", 700), ("양파", "1/4개", 200),
        ("감자", "1개", 800)],
       ["물에 된장을 푼다.", "감자·양파를 넣고 5분 끓인다.", "애호박·두부를 넣고 5분 더 끓인다."], "냄비"),
    _r("닭가슴살 샐러드", "가볍지만 든든한 한 끼", "healthy", "easy", 10, ["다이어트"],
       [("닭가슴살", "1팩", 2500), ("양상추", "한 줌", 1500), ("방울토마토", "5개", 1000), ("드레싱", "2큰술", 500)],
       ["닭가슴살을 데워 찢는다.", "채소를 씻어 담는다.", "드레싱을 뿌린다."], "전자레인지"),
    _r("고구마 맛탕", "에어프라이어로 만드는 달달한 간식", "dessert", "easy", 20, ["야식"],
       [("고구마", "2개", 2000), ("설탕", "2큰술", 200), ("식용유", "1큰술", 200)],
       ["고구마를 깍둑썰기 한다.", "기름을 버무려 에어프라이어 180도 15분.", "녹인 설탕을 버무린다."], "에어프라이어"),
    _r("찹스테이크", "특별한 날 도전해 보는 고기 요리", "meat", "hard", 60, [],
       [("소고기 부챗살", "250g", 12000), ("파프리카", "1개", 1500), ("양파", "1/2개", 400), ("스테이크 소스", "3큰술", 800)],
       ["고기를 한입 크기로 썰어 밑간한다.", "센 불에 고기를 굽는다.", "채소를 넣고 볶다가 소스로 마무리."], "프라이팬"),
]

SHOP_ITEMS = [
    {"name": "편의점 3천원 상품권", "description": "GS25/CU 사용 가능", "price": 10, "min_level": 1, "stock": None},
    {"name": "아메리카노 기프티콘", "description": "", "price": 20, "min_level": 3, "stock": None},
    {"name": "배달앱 1만원 쿠폰", "description": "이번 달 한정", "price": 50, "min_level": 5, "stock": 10},
    {"name": "치킨 기프티콘", "description": "고수 전용", "price": 100, "min_level": 10, "stock": 5},
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(Category).filter(Category.kind == "fail").count():
            for name, desc in FAIL_CATEGORIES:
                db.add(Category(name=name, description=desc, kind="fail"))
            print(f"망한 요리 대회 주제 {len(FAIL_CATEGORIES)}개 추가")
        else:
            print("망한 요리 대회 주제: 이미 있어 건너뜀")
        for model, rows, label, build in (
            (Category, CATEGORIES, "카테고리", lambda r: Category(name=r[0], description=r[1], kind="league")),

            (ShopItem, SHOP_ITEMS, "상점 상품", lambda r: ShopItem(**r)),
        ):
            existing = db.query(model)
            if model is Category:
                existing = existing.filter(Category.kind == "league")
            if existing.count():
                print(f"{label}: 이미 있어 건너뜀")
                continue
            for r in rows:
                db.add(build(r))
            print(f"{label} {len(rows)}개 추가")
        # 공식 레시피: 제목이 없으면 추가, 예전 형식(조리 시간 없음)이면 새 정보로 채움
        added = updated = 0
        for r in RECIPES:
            existing = db.query(Recipe).filter(Recipe.title == r["title"], Recipe.is_official.is_(True)).first()
            if existing is None:
                db.add(Recipe(**r, is_official=True))
                added += 1
            elif existing.cook_minutes is None:
                for k, v in r.items():
                    setattr(existing, k, v)
                updated += 1
        print(f"공식 레시피: {added}개 추가, {updated}개 정보 보강")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
