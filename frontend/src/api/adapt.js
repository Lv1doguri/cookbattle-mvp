// Backend <-> mock-shape adapters, so screens keep reading the same field names
// they did against src/data/mock.js.
import { imageUrl } from './client';

// Deterministic placeholder color per recipe (the API has no color; the design
// prototype's photos were placeholders too).
const TONES = [
  ['#E8D6CE', '#D9BBAC', '#A25C46'],
  ['#EFE7C6', '#DFCB92', '#8A6A38'],
  ['#F4EDE2', '#E6D6BD', '#8A6A3C'],
  ['#E2E2E2', '#CACACA', '#5B5B5B'],
  ['#EAD9BE', '#D9BE8E', '#8A6640'],
];
export function toneFor(id) {
  let h = 0;
  for (const ch of String(id)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return TONES[h % TONES.length];
}

export const CATEGORY_LABEL_TO_CODE = {
  '밥': 'rice', '면': 'noodle', '파스타': 'pasta', '고기': 'meat',
  '국·찌개': 'soup', '반찬': 'side', '건강식': 'healthy', '디저트': 'dessert',
};
const BUDGET_CODE = { b1: 'under_5000', b2: '5000_to_10000', b3: 'over_10000' };
const TIME_CODE = { t10: 'le_10', t15: 'le_15', t30: 'le_30', t60: 'ge_60' };

// Frontend filter option ids (see data/mock.js FILTER_GROUPS) -> backend query params.
export function filtersToParams(filters) {
  const params = {};
  const categories = (filters.category ?? []).map((c) => CATEGORY_LABEL_TO_CODE[c]).filter(Boolean);
  if (categories.length) params.category = categories;
  const budgets = (filters.budget ?? []).map((b) => BUDGET_CODE[b]).filter(Boolean);
  if (budgets.length) params.budget = budgets;
  const times = (filters.time ?? []).map((t) => TIME_CODE[t]).filter(Boolean);
  if (times.length) params.time = times;
  if (filters.skill?.length) params.difficulty = filters.skill;
  return params;
}

export function quickFilterParams(quickId) {
  if (quickId === 'cheap') return { budget: ['under_5000'] };
  if (quickId === 'quick') return { time: ['le_15'] };
  if (quickId === 'beginner') return { difficulty: ['beginner'] };
  if (quickId === 'solo') return { essential: 'true' };
  return {};
}

export function toQueryString(params) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (Array.isArray(v)) v.forEach((x) => qs.append(k, x));
    else if (v !== undefined && v !== null && v !== '') qs.append(k, v);
  }
  const s = qs.toString();
  return s ? `?${s}` : '';
}

export function adaptRecipeCard(r) {
  return {
    id: r.id,
    name: r.name,
    award: r.win_label ?? '',
    category: r.category_label,
    minutes: r.minutes,
    cost: r.price,
    skill: r.difficulty,
    saves: r.saves,
    saved: r.is_saved,
    tags: r.is_essential ? ['자취 필수'] : [],
    tone: toneFor(r.id),
    photoUrl: imageUrl(r.photo_url),
    valueScore: r.value_score,
    caloriesKcal: r.calories_kcal,
    portionLabel: r.portion_label,
  };
}

export function adaptRecipeDetail(r) {
  return {
    ...adaptRecipeCard(r),
    author: r.author?.nickname ?? '요리왕',
    ingredients: r.ingredients.map((i) => [i.name, i.amount ?? '']),
    steps: r.steps.map((s) => ({ text: s.text, minutes: s.minutes })),
    failSafetyLabel: r.fail_safety_label,
    chefTip: r.chef_tip,
  };
}

// Progress -> the 0..1 bar + "다음 레벨까지 N포인트" the Home/Shop screens render.
export function adaptUser(me) {
  const p = me.progress;
  const span = p.next_level_points - p.level_start_points;
  return {
    id: me.id,
    nickname: me.nickname,
    email: me.email ?? '',
    avatar: imageUrl(me.avatar_url),
    skill: me.tier,
    level: p.level,
    levelProgress: span > 0 ? (p.points - p.level_start_points) / span : 0,
    pointsToNextLevel: p.points_to_next_level,
    points: p.points,
    savedRecipeCount: me.saved_recipe_count,
    reviewCount: me.review_count,
    streakWeeks: me.streak_weeks,
  };
}

export function adaptBattle(b) {
  return {
    id: b.id,
    kind: b.kind, // 'daily' | 'theme'
    tier: b.tier,
    tierLabel: b.tier_label,
    title: b.title,
    topic: b.theme,
    subtitle: b.description,
    daysLeft: b.days_left,
    secondsLeft: b.seconds_left,
    participants: b.participants,
    isMyGroup: b.is_my_group,
    isOpen: b.is_open,
    hasJoined: b.has_joined,
    canJoin: b.can_join,
    myEntry: b.my_entry,
    lastResult: b.last_result,
  };
}

// 대결 홈의 "지난 대회 투표하기" 카드. 투표 가능한 지난 대회가 없으면 null.
export function adaptVotingCard(v) {
  if (!v) return null;
  return {
    battleId: v.battle_id,
    kind: v.kind,
    title: v.title,
    groupLabel: v.group_label,
    participants: v.participants,
    hoursLeft: v.hours_left,
    hasVoted: v.has_voted,
  };
}

export function adaptBattleHome(h) {
  return { daily: adaptBattle(h.daily), theme: adaptBattle(h.theme), voting: adaptVotingCard(h.voting) };
}

function timeOfDay(iso) {
  return new Date(iso).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false });
}

export function adaptEntry(e, myId) {
  return {
    id: e.id,
    name: e.dish_name,
    author: e.author.nickname,
    hearts: e.vote_count,
    photoUrl: imageUrl(e.photo_url),
    mine: e.state === 'mine' || e.author.id === myId,
    voted: e.state === 'voted',
    votable: e.state === 'votable',
  };
}

export function adaptResult(r) {
  const noteFor = (row) => {
    if (row.tie === 'first') return `먼저 제출 ${timeOfDay(row.submitted_at)}`;
    if (row.tie === 'tied') return `동점 · ${timeOfDay(row.submitted_at)} 제출`;
    return null;
  };
  return {
    title: r.title,
    group: `${r.tier_label} 그룹`,
    participants: r.participants,
    isVoid: r.status === 'void',
    myRank: r.me.rank,
    reward: r.me.rank_points,
    joined: r.me.joined,
    levelUp: r.me.leveled_up ? { from: r.me.level_from, to: r.me.level_to } : null,
    canShareRecipe: r.me.can_share_recipe,
    sharedRecipeId: r.me.shared_recipe_id,
    ranking: r.top10.map((row) => ({
      rank: row.rank,
      entryId: row.entry_id,
      name: row.user.nickname,
      dishName: row.dish_name,
      photoUrl: imageUrl(row.photo_url),
      votes: row.vote_count,
      rankPoints: row.rank_points,
      me: row.is_me,
      sharedRecipe: row.is_winner,
      canShareRecipe: row.can_share_recipe,
      note: noteFor(row),
    })),
  };
}

export function adaptShopItem(i) {
  return {
    id: i.id,
    name: i.name,
    price: i.price_points,
    minLevel: i.required_level,
    locked: i.state === 'locked',
    soldOut: i.state === 'sold_out',
    short: i.state === 'insufficient_points' ? i.points_short : 0,
    photoUrl: imageUrl(i.photo_url),
  };
}
