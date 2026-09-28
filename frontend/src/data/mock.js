// Mock data standing in for the backend. Swap these for API calls later
// (see src/state/AppContext.jsx for where each piece is consumed).

export const SKILLS = [
  { id: 'beginner', label: '초급', desc: '라면 끓이기 정도 할 수 있어요', icon: 'sprout', tint: '#ECECEA', ink: '#5B5B5B' },
  { id: 'intermediate', label: '중급', desc: '볶음밥·파스타는 자신 있어요', icon: 'pan', tint: '#ECECEA', ink: '#A85814' },
  { id: 'advanced', label: '상급', desc: '소스부터 직접 만들어요', icon: 'chefHat', tint: '#EFE6D8', ink: '#8A6A42' },
];

export const skillLabel = (id) => SKILLS.find((s) => s.id === id)?.label ?? '';

export const TAKEN_NICKNAMES = ['자취생', '요리왕', '관리자'];

export const INITIAL_USER = {
  nickname: 'Yuri',
  email: 'you@university.ac.kr',
  skill: 'intermediate',
  level: 2,
  levelProgress: 0.58, // 0–1 toward next level
  pointsToNextLevel: 6,
  points: 1240,
  monthlyCooks: 8,
  savedMoney: 32000,
};

// Photo placeholder palettes from the prototype
const TONES = {
  rose: ['#E8D6CE', '#D9BBAC', '#A25C46'],
  mustard: ['#EFE7C6', '#DFCB92', '#8A6A38'],
  cream: ['#F4EDE2', '#E6D6BD', '#8A6A3C'],
  gray: ['#E2E2E2', '#CACACA', '#5B5B5B'],
  wheat: ['#EAD9BE', '#D9BE8E', '#8A6640'],
};

export const RECIPES = [
  {
    id: 'kimchi-fried-rice', name: '김치볶음밥', award: '밥 요리 대결 1등', category: '밥',
    minutes: 15, cost: 3500, skill: 'beginner', saves: 12, createdAt: '2026-09-21', tone: TONES.rose, tags: ['자취 필수'],
    ingredients: [['김치', '1컵'], ['밥', '1공기'], ['계란', '1개'], ['식용유', '1큰술']],
    steps: ['김치를 잘게 썬다.', '팬에 기름을 두르고 김치를 볶는다.', '밥을 넣고 고루 볶는다.'],
  },
  {
    id: 'tuna-mayo-bowl', name: '참치마요 덮밥', award: '5천원 이하 대결 1등', category: '밥',
    minutes: 10, cost: 2800, skill: 'beginner', saves: 21, createdAt: '2026-09-18', tone: TONES.mustard, tags: ['자취 필수'],
    ingredients: [['참치캔', '1개'], ['밥', '1공기'], ['마요네즈', '2큰술'], ['김가루', '약간']],
    steps: ['참치의 기름을 뺀다.', '참치와 마요네즈를 섞는다.', '밥 위에 올리고 김가루를 뿌린다.'],
  },
  {
    id: 'cream-pasta', name: '크림 파스타', award: '면 요리 대결 1등', category: '파스타',
    minutes: 20, cost: 4500, skill: 'intermediate', saves: 15, createdAt: '2026-09-14', tone: TONES.cream, tags: [],
    ingredients: [['파스타면', '100g'], ['우유', '200ml'], ['베이컨', '2줄'], ['치즈', '1장']],
    steps: ['면을 삶는다.', '베이컨을 볶다가 우유를 붓는다.', '치즈를 녹이고 면을 넣어 섞는다.'],
  },
  {
    id: 'bibim-guksu', name: '비빔국수', award: '면 요리 대결 1등', category: '면',
    minutes: 15, cost: 3000, skill: 'beginner', saves: 9, createdAt: '2026-09-10', tone: TONES.gray, tags: [],
    ingredients: [['소면', '1인분'], ['고추장', '1큰술'], ['식초', '1큰술'], ['설탕', '1작은술']],
    steps: ['소면을 삶아 찬물에 헹군다.', '양념을 섞는다.', '면과 양념을 비빈다.'],
  },
  {
    id: 'egg-roll', name: '폭신 계란말이', award: '계란 요리 대결 3등', category: '반찬',
    minutes: 10, cost: 1500, skill: 'beginner', saves: 18, createdAt: '2026-09-22', tone: TONES.mustard, tags: ['자취 필수'],
    ingredients: [['계란', '3개'], ['대파', '약간'], ['소금', '약간']],
    steps: ['계란을 풀고 파와 소금을 넣는다.', '약불에서 조금씩 부어 만다.', '한 김 식힌 뒤 썬다.'],
  },
  {
    id: 'doenjang-jjigae', name: '된장찌개', award: '국·찌개 대결 1등', category: '국·찌개',
    minutes: 25, cost: 6000, skill: 'intermediate', saves: 14, createdAt: '2026-09-05', tone: TONES.wheat, tags: [],
    ingredients: [['된장', '2큰술'], ['두부', '1/2모'], ['애호박', '1/3개'], ['양파', '1/2개']],
    steps: ['물에 된장을 푼다.', '채소를 넣고 끓인다.', '두부를 넣고 한소끔 더 끓인다.'],
  },
  {
    id: 'chicken-salad', name: '닭가슴살 샐러드', award: '건강식 대결 2등', category: '건강식',
    minutes: 10, cost: 5500, skill: 'beginner', saves: 7, createdAt: '2026-09-02', tone: TONES.cream, tags: [],
    ingredients: [['닭가슴살', '1팩'], ['양상추', '한 줌'], ['방울토마토', '5개'], ['드레싱', '2큰술']],
    steps: ['채소를 씻어 물기를 뺀다.', '닭가슴살을 찢는다.', '모두 담고 드레싱을 뿌린다.'],
  },
  {
    id: 'rose-tteokbokki', name: '로제 떡볶이', award: '분식 대결 1등', category: '면',
    minutes: 30, cost: 8000, skill: 'advanced', saves: 26, createdAt: '2026-08-29', tone: TONES.rose, tags: [],
    ingredients: [['떡', '200g'], ['고추장', '1큰술'], ['우유', '150ml'], ['생크림', '100ml']],
    steps: ['고추장과 버터를 볶는다.', '우유와 생크림을 붓는다.', '떡을 넣고 졸인다.'],
  },
];

export const QUICK_FILTERS = [
  { id: 'all', label: '전체' },
  { id: 'cheap', label: '5천원 이하', test: (r) => r.cost <= 5000 },
  { id: 'quick', label: '15분 이내', test: (r) => r.minutes <= 15 },
  { id: 'beginner', label: '초급', test: (r) => r.skill === 'beginner' },
  { id: 'solo', label: '자취 필수', test: (r) => r.tags.includes('자취 필수') },
];

export const FILTER_GROUPS = [
  {
    id: 'category', title: '종류',
    options: ['밥', '면', '파스타', '고기', '국·찌개', '반찬', '건강식', '디저트'].map((c) => ({ id: c, label: c, test: (r) => r.category === c })),
  },
  {
    id: 'budget', title: '예산',
    options: [
      { id: 'b1', label: '5,000원 이하', test: (r) => r.cost <= 5000 },
      { id: 'b2', label: '5,000~10,000원', test: (r) => r.cost > 5000 && r.cost <= 10000 },
      { id: 'b3', label: '10,000원 이상', test: (r) => r.cost > 10000 },
    ],
  },
  {
    id: 'time', title: '조리 시간',
    options: [
      { id: 't10', label: '10분 이하', test: (r) => r.minutes <= 10 },
      { id: 't15', label: '15분 이하', test: (r) => r.minutes <= 15 },
      { id: 't30', label: '30분 이하', test: (r) => r.minutes <= 30 },
      { id: 't60', label: '1시간 이상', test: (r) => r.minutes >= 60 },
    ],
  },
  {
    id: 'skill', title: '난이도',
    options: SKILLS.map((s) => ({ id: s.id, label: s.label, test: (r) => r.skill === s.id })),
  },
];

// Within a group options are OR-ed, across groups AND-ed.
export function applyFilters(recipes, selected) {
  return recipes.filter((r) =>
    FILTER_GROUPS.every((g) => {
      const picked = g.options.filter((o) => selected[g.id]?.includes(o.id));
      return picked.length === 0 || picked.some((o) => o.test(r));
    }),
  );
}

export const BATTLES = {
  beginner: { topic: '라면', subtitle: '나만의 라면 레시피', daysLeft: 3, participants: 31 },
  intermediate: { topic: '계란 요리', subtitle: '계란이 메인인 든든한 한 끼', daysLeft: 3, participants: 24 },
  advanced: { topic: '파스타', subtitle: '소스까지 직접 만든 파스타', daysLeft: 3, participants: 12 },
};

export const BATTLE_HISTORY = [
  { id: 'h1', title: '계란 요리 대결', meta: '9월 3주차 · 중급 그룹', result: '2등', icon: 'egg', tint: '#EFE9D2', ink: '#8A6A38', medal: true },
  { id: 'h2', title: '라면 대결', meta: '9월 2주차 · 중급 그룹', result: '참가', icon: 'ramen', tint: '#EBDED8', ink: '#A25C46' },
];

export const VOTE_ENTRIES = [
  { id: 'e1', name: '스크램블 에그', author: '민수', hearts: 12, art: 'egg', bg: ['#FFF1C2', '#FFD970'] },
  { id: 'e3', name: '에그 인 헬', author: '준호', hearts: 15, art: 'eggBowl', bg: ['#E8D6CE', '#D9BBAC'] },
  { id: 'e4', name: '폭신 계란말이', author: '서연', hearts: 9, art: 'eggRoll', bg: ['#FFF4D6', '#FFE39C'] },
];

export const LAST_RESULT = {
  title: '라면 대결',
  group: '중급 그룹',
  participants: 24,
  myRank: 2,
  reward: 4,
  levelUp: { from: 1, to: 2 },
  ranking: [
    { rank: 1, name: '민수', votes: 42, sharedRecipe: true },
    { rank: 2, name: 'Yuri', votes: 38, me: true },
    { rank: 3, name: '준호', votes: 35 },
    { rank: 4, name: '서연', votes: 30, note: '동점 · 먼저 제출 18:02' },
  ],
};

// 이름은 백엔드 SHOP_SEED(app/content.py)와 정확히 같아야 해요 — Shop.jsx가 이름으로
// 매칭해서 아이콘/색만 여기서 가져가고, 가격·레벨·재고는 API 값을 그대로 써요.
export const SHOP_ITEMS = [
  { id: 'cvs', name: '편의점 1,000원권', price: 120, minLevel: 1, icon: 'store', bg: ['#E1E6EC', '#C7D2DE'], ink: '#4A6178' },
  { id: 'coffee', name: '저가 커피 아메리카노', price: 240, minLevel: 2, icon: 'coffee', bg: ['#EFE6D9', '#DECBB4'], ink: '#6E5A40' },
  { id: 'meal', name: '학식 식권', price: 650, minLevel: 3, icon: 'cutlery', bg: ['#E2E2E2', '#CACACA'], ink: '#A85814' },
  { id: 'chicken', name: '치킨 기프티콘', price: 2600, minLevel: 5, icon: 'burger', bg: ['#EAD9BE', '#D9BE8E'], ink: '#8A6640' },
];

export const ONBOARDING = [
  { title: '하단 탭으로 이동해요', body: '레시피 · 대결 · 홈 · 상점 · 메뉴를 오갈 수 있어요.\n홈에서는 내 레벨과 포인트를 볼 수 있어요.', highlight: 2, hint: '여기를 눌러요!' },
  { title: '매주 대결에 참가해요', body: '내 실력 그룹의 주제로 요리하고\n앱 카메라로 인증하면 +1P를 받아요.', highlight: 1, hint: '대결은 여기!' },
  { title: '마음에 드는 요리에 투표해요', body: '한 대결에 한 표씩 투표할 수 있어요.\n내 작품에는 투표할 수 없어요.', highlight: 1, hint: '1인 1표' },
  { title: '포인트로 기프티콘을 받아요', body: '모은 포인트는 상점에서 교환해요.\n레벨이 오르면 더 많은 상품이 열려요.', highlight: 3, hint: '상점은 여기!' },
];

export const won = (n) => n.toLocaleString('ko-KR');
