"""게임 규칙 상수 모음. 기획 회의에서 숫자가 바뀌면 이 파일만 고치면 됩니다."""

# ---- 요리 실력 그룹 (가입 시 선택, 변경 불가) ----
SKILLS = {
    "low": {"label": "하", "description": "라면 끓이기 정도 가능"},
    "mid": {"label": "중", "description": "볶음밥, 찌개 같은 기본 요리 가능"},
    "high": {"label": "상", "description": "레시피 없이도 여러 요리를 해 본 경험이 있음"},
}

# ---- 포인트 / 레벨 ----
PARTICIPATION_POINTS = 1          # 대결 참가 즉시 지급
RANK_POINTS = [5, 4, 3]           # 1/2/3등 (득표 1표 이상일 때만)
POINTS_PER_LEVEL = 10             # 누적 포인트 N점마다 레벨 1 상승 (모두 1레벨 시작)
RECIPE_COMPLETE_POINTS = 1        # 레시피 따라하기 완료 인증 (레시피당 1회)
STREAK_WEEKS = 3                  # [Could] N주 연속 참가 시
STREAK_BONUS = 2                  #         보너스 (0으로 두면 끔)
INVITE_POINTS_INVITER = 2         # 친구 초대한 사람
INVITE_POINTS_INVITEE = 1         # 초대 코드로 가입한 사람
INVITE_AUTO_FRIEND = True         # 초대 코드로 가입하면 초대한 사람과 자동으로 친구
MAX_FRIENDS = 100                 # 친구 수 상한
MAX_PENDING_FRIEND_REQUESTS = 30  # 수락 대기 중인 보낸 요청 상한 (도배 방지)
AI_CALLS_PER_HOUR = 30            # 사용자당 이미지 인식 AI 호출 상한 (유료 API 남용 방지)

# ---- 대결 ----
# 1주일 = 요리(참가) 기간 5일 + 투표 기간 2일. 투표는 그 대결 참가자만 가능.
BATTLE_DURATION_DAYS = 7          # 대결 전체 기간
COOKING_DAYS = 5                  # 앞 5일: 사진 올리기 / 뒤 2일: 참가자끼리 투표
LEAGUE_GROUPS = ["low", "mid", "high"]  # 실력 리그 (SKILLS 키)
FAIL_GROUP = "fail"               # '망한 요리 대회' — 리그 구분 없이 전체 참가
FAIL_CONTEST_ENABLED = True
FAIL_RANK_POINTS = [3, 2, 1]      # 망한 요리 대회 1/2/3등 (재미 대회라 리그보다 적게)
BATTLE_KINDS = {"league": "리그 대결", "fail": "망한 요리 대회"}
PHASE_LABELS = {"cooking": "요리 기간", "voting": "투표 기간", "closed": "종료"}
MIN_PARTICIPANTS = 3              # 이보다 적으면 대결 무효 (참가 포인트만 지급)
HIDE_VOTES_UNTIL_CLOSED = False   # True면 마감 전 득표수 비공개 (기획서: 투표 화면에 투표 수 표시)
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024

# ---- 다중 구도 인증샷 ----
# 대결 참가 시 사용자마다 '촬영 가이드'가 정해진다: 고정 구도 + 랜덤 구도 N개.
# 랜덤 구도는 (대결, 사용자)마다 다르게 뽑혀서 미리 찍어 둔 사진·퍼온 사진으로 맞추기 어렵다.
SHOT_TYPES = {
    "front":   {"label": "완성샷 (정면 45°)", "guide": "완성된 요리를 45도 각도에서, 그릇 전체가 나오게 찍어 주세요"},
    "keyword": {"label": "키워드 인증샷", "guide": "오늘의 인증 키워드를 종이에 써서 요리 옆에 두고 함께 찍어 주세요"},
    "top":     {"label": "위에서 (탑뷰)", "guide": "요리 바로 위에서 수직으로 내려다보며 찍어 주세요"},
    "side":    {"label": "옆에서 (측면)", "guide": "그릇 높이에 카메라를 맞추고 옆에서 찍어 주세요"},
    "closeup": {"label": "클로즈업", "guide": "가장 맛있어 보이는 부분을 가까이에서 찍어 주세요"},
    "process": {"label": "조리 과정", "guide": "재료를 손질하거나 조리하는 중간 모습을 찍어 주세요"},
}
SHOT_FIXED = ["front", "keyword"]                     # 항상 필요한 구도
SHOT_RANDOM_POOL = ["top", "side", "closeup", "process"]  # 여기서 랜덤으로
SHOT_RANDOM_COUNT = 1                                 # N개 추가 → 기본 총 3장

PHOTO_MIN_SIDE = 400              # 짧은 변 최소 픽셀
PHOTO_MIN_BRIGHTNESS = 20         # 평균 밝기(0~255) 미만이면 너무 어두움
PHOTO_MIN_CONTRAST = 8            # 밝기 표준편차 미만이면 빈/단색 사진
PHOTO_DUP_DISTANCE = 10           # 지각 해시 거리 이하면 같은 사진으로 판단 (0~64, 다른 사진은 보통 20~40)
PHOTO_EXIF_TOLERANCE_DAYS = 1     # 촬영일이 대결 기간 ±N일 밖이면 거절
PHOTO_MAX_EDGE = 1600             # 저장 시 긴 변을 이 크기로 축소 (용량 절약)

# ---- 이미지 인식 AI ----
AI_MIN_CONFIDENCE = 0.7           # 구도 불일치는 AI 확신도가 이 이상일 때만 거절 (애매하면 통과)
AI_IMAGE_MAX_EDGE = 768           # AI에 보낼 때 축소 크기 (속도·비용 절약)
AI_TIMEOUT_SECONDS = 40
REPORT_HIDE_THRESHOLD = 3         # 신고 N회 누적 시 자동 숨김
VERIFICATION_KEYWORDS = [
    "고등어", "치즈", "양파", "대파", "라면", "김치", "우유", "감자", "두부", "참치",
    "버섯", "당근", "계란", "마늘", "햄", "만두", "호박", "베이컨", "콩나물", "어묵",
]

# ---- 레시피 (디자인: 05 필터 / 04 레시피 목록) ----
RECIPE_FOOD_TYPES = {  # 종류
    "rice": "밥", "noodle": "면", "pasta": "파스타", "meat": "고기",
    "soup": "국·찌개", "side": "반찬", "healthy": "건강식", "dessert": "디저트",
}
RECIPE_DIFFICULTIES = {"easy": "초급", "normal": "중급", "hard": "상급"}  # 난이도
RECIPE_TAGS = ["자취 필수", "전자레인지", "원팬", "야식", "도시락", "다이어트"]  # 태그 (고정 목록)
# 필터 화면의 칩 → API 파라미터
RECIPE_BUDGET_OPTIONS = [
    {"label": "5,000원 이하", "params": {"max_cost": 5000}},
    {"label": "5,000~10,000원", "params": {"min_cost": 5000, "max_cost": 10000}},
    {"label": "10,000원 이상", "params": {"min_cost": 10000}},
]
RECIPE_TIME_OPTIONS = [
    {"label": "10분 이하", "params": {"max_minutes": 10}},
    {"label": "15분 이하", "params": {"max_minutes": 15}},
    {"label": "30분 이하", "params": {"max_minutes": 30}},
    {"label": "1시간 이상", "params": {"min_minutes": 60}},
]
# 목록 화면 상단 빠른 칩
RECIPE_QUICK_FILTERS = [
    {"label": "전체", "params": {}},
    {"label": "5천원 이하", "params": {"max_cost": 5000}},
    {"label": "15분 이내", "params": {"max_minutes": 15}},
    {"label": "초급", "params": {"difficulty": "easy"}},
    {"label": "자취 필수", "params": {"tag": "자취 필수"}},
]
RECIPE_SORTS = {"latest": "최신순", "popular": "인기순", "cheap": "저렴한순", "quick": "빠른순"}
RECIPE_UPLOADS_PER_HOUR = 10       # 레시피 도배 방지

# ---- 홈 통계 ----
DELIVERY_AVG_PRICE = 15000        # 절약 식비 = 배달 1회 평균 금액 - 재료비

# ---- 튜토리얼 ----
TUTORIAL_STEPS = 4


def level_for(total_points: int) -> int:
    return 1 + max(total_points, 0) // POINTS_PER_LEVEL


def next_level_points(total_points: int) -> int:
    return level_for(total_points) * POINTS_PER_LEVEL


def level_progress(total_points: int) -> float:
    """현재 레벨 진행률 0.0 ~ 1.0 (레벨 진행 바용)."""
    return (max(total_points, 0) % POINTS_PER_LEVEL) / POINTS_PER_LEVEL


def skill_label(key: str) -> str:
    return SKILLS.get(key, {}).get("label", key)
