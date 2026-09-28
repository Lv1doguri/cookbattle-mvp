import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, dataUrlToBlob, getToken, imageUrl, setToken } from '../api/client';
import { adaptBattle, adaptBattleHome, adaptEntry, adaptResult, adaptUser, filtersToParams, quickFilterParams, toQueryString } from '../api/adapt';

// Single client-side store. Every function here calls the real backend
// (see API_CONTRACT.md on feat/backend-full-a for the exact shapes).
const AppContext = createContext(null);

const EMPTY_FILTERS = { category: [], budget: [], time: [], skill: [] };

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loggedIn, setLoggedIn] = useState(false);
  const [booting, setBooting] = useState(true); // restoring a saved session on first load
  const [savedIds, setSavedIds] = useState([]);
  const [recentIds, setRecentIds] = useState([]);
  const [comments, setComments] = useState({}); // recipeId -> [{ author, text }]
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [draftPhotos, setDraftPhotos] = useState([]); // 각도별 dataURL 배열 (in-app camera)
  const [submission, setSubmission] = useState(null); // { name, description, photo, submittedAt }
  const [votedEntryId, setVotedEntryId] = useState(null);
  const [online, setOnline] = useState(typeof navigator === 'undefined' ? true : navigator.onLine);

  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener('online', up);
    window.addEventListener('offline', down);
    return () => {
      window.removeEventListener('online', up);
      window.removeEventListener('offline', down);
    };
  }, []);

  const applyMe = useCallback((me) => setUser((u) => ({ ...adaptUser(me), monthlyCooks: u?.monthlyCooks ?? 0, savedMoney: u?.savedMoney ?? 0 })), []);

  // Restore a saved login on refresh.
  useEffect(() => {
    (async () => {
      if (!getToken()) return setBooting(false);
      try {
        applyMe(await api('/me'));
        setLoggedIn(true);
      } catch {
        setToken(null);
      } finally {
        setBooting(false);
      }
    })();
  }, [applyMe]);

  const login = useCallback(async (email, password) => {
    const r = await api('/auth/login', { method: 'POST', auth: false, body: { email, password } });
    setToken(r.access_token);
    applyMe(r.user);
    setLoggedIn(true);
  }, [applyMe]);

  const logout = useCallback(() => {
    setToken(null);
    setLoggedIn(false);
    setUser(null);
    setSubmission(null);
    setVotedEntryId(null);
  }, []);

  const checkNickname = useCallback(async (name) => {
    const trimmed = name.trim();
    if (trimmed.length < 2) return true; // let required/length errors show first
    const r = await api(`/auth/nickname-available${toQueryString({ nickname: trimmed })}`, { auth: false });
    return !r.available;
  }, []);

  const checkUsername = useCallback(async (name) => {
    const trimmed = name.trim();
    if (trimmed.length < 4) return true; // let required/length errors show first
    const r = await api(`/auth/username-available${toQueryString({ username: trimmed })}`, { auth: false });
    return !r.available;
  }, []);

  const signup = useCallback(async ({ username, nickname, skill, password }) => {
    const r = await api('/auth/signup', { method: 'POST', auth: false, body: { username, nickname, password, tier: skill } });
    setToken(r.access_token);
    applyMe(r.user);
    setLoggedIn(true);
  }, [applyMe]);

  // Google Identity Services hands us an id_token; the backend verifies it and
  // either links it to an existing account (by google_sub or matching email) or
  // creates a new one. `tier` only matters the first time (new account) — see
  // GoogleAuthIn in API_CONTRACT.md.
  const loginWithGoogle = useCallback(async (idToken, tier) => {
    const r = await api('/auth/google', { method: 'POST', auth: false, body: { id_token: idToken, tier } });
    setToken(r.access_token);
    applyMe(r.user);
    setLoggedIn(true);
  }, [applyMe]);

  const updateProfile = useCallback(async ({ nickname, skill, password, avatarFile }) => {
    const body = {};
    if (nickname !== undefined) body.nickname = nickname;
    if (skill !== undefined) body.tier = skill;
    if (password) body.password = password;
    const me = await api('/me', { method: 'PATCH', body });
    applyMe(me);
    if (avatarFile) {
      const form = new FormData();
      form.append('file', avatarFile);
      applyMe(await api('/me/avatar', { method: 'PUT', form }));
    }
  }, [applyMe]);

  const fetchHome = useCallback(async () => {
    const h = await api('/me/home');
    applyMe(h.me);
    setUser((u) => ({ ...u, monthlyCooks: h.cooking_count_this_month, savedMoney: h.saved_amount_krw }));
    return {
      history: h.history.map((x) => ({
        id: `${x.battle_id}-${x.entry_id}`,
        battleId: x.battle_id,
        title: x.title,
        meta: `${x.week_label} · ${x.tier_label} 그룹`,
        result: x.status === 'void' ? '무효' : x.rank ? `${x.rank}등` : '참가',
        medal: x.rank === 1,
      })),
    };
  }, [applyMe]);

  const toggleSaved = useCallback(async (id, currentlySaved) => {
    setSavedIds((ids) => (currentlySaved ? ids.filter((x) => x !== id) : [id, ...ids]));
    try {
      await api(`/recipes/${id}/save`, { method: currentlySaved ? 'DELETE' : 'POST' });
    } catch {
      setSavedIds((ids) => (currentlySaved ? [id, ...ids] : ids.filter((x) => x !== id))); // roll back
    }
  }, []);

  const fetchRecipes = useCallback(async ({ q, filters: f, quick, sort }) => {
    const params = { ...filtersToParams(f), ...quickFilterParams(quick), q, sort: sort === 'popular' ? 'popular' : 'latest', limit: 50 };
    const page = await api(`/recipes${toQueryString(params)}`);
    return page.items;
  }, []);

  const fetchRecipeCount = useCallback(async ({ filters: f }) => {
    const page = await api(`/recipes${toQueryString({ ...filtersToParams(f), limit: 1 })}`);
    return page.total;
  }, []);

  const fetchRecipe = useCallback(async (id) => api(`/recipes/${id}`), []);

  const markViewed = useCallback((id) => setRecentIds((ids) => [id, ...ids.filter((x) => x !== id)].slice(0, 10)), []);

  const adaptReview = (r) => ({
    author: r.author.nickname,
    text: r.text,
    photoUrl: imageUrl(r.photo_url),
    rating: r.rating,
    difficultyLabel: r.difficulty_tag_label,
  });

  const fetchComments = useCallback(async (recipeId) => {
    const page = await api(`/recipes/${recipeId}/reviews`);
    const list = page.items.map(adaptReview);
    setComments((c) => ({ ...c, [recipeId]: list }));
    return list;
  }, []);

  // photoFile(선택)은 사진 파일 그대로, rating(1~5)/difficultyTag('easy'|'normal'|'hard')도 선택.
  const addComment = useCallback(async (recipeId, text, { photoFile, rating, difficultyTag } = {}) => {
    let photo_id;
    if (photoFile) {
      const form = new FormData();
      form.append('file', photoFile);
      photo_id = (await api('/photos', { method: 'POST', form })).photo_id;
    }
    const created = await api(`/recipes/${recipeId}/reviews`, {
      method: 'POST',
      body: { text, photo_id, rating, difficulty_tag: difficultyTag },
    });
    setComments((c) => ({ ...c, [recipeId]: [...(c[recipeId] ?? []), adaptReview(created)] }));
  }, []);

  const fetchSavedRecipes = useCallback(async () => {
    const page = await api('/me/saved-recipes?limit=50');
    setSavedIds(page.items.map((r) => r.id));
    return page.items;
  }, []);

  const fetchRecentRecipes = useCallback(async () => {
    const page = await api('/me/recent-recipes');
    setRecentIds(page.items.map((r) => r.id));
    return page.items;
  }, []);

  const fetchMyReviewCount = useCallback(async () => (await api('/me/reviews')).length, []);

  const fetchMyReviews = useCallback(async () => {
    const rows = await api('/me/reviews');
    return rows.map((r) => ({ recipeId: r.recipe_id, recipeName: r.recipe_name, text: r.text }));
  }, []);

  const fetchMyRecipes = useCallback(async () => (await api('/recipes?mine=true&limit=50')).items, []);

  // kind: 'daily' (그룹별, 기본값) | 'theme' (전체 공통). tier는 kind=theme이면 무시돼요.
  const fetchBattle = useCallback(async (tier, kind) => adaptBattle(await api(`/battles/current${toQueryString({ tier, kind })}`)), []);

  const fetchBattleHome = useCallback(async (tier) => adaptBattleHome(await api(`/battles/home${toQueryString({ tier })}`)), []);

  // Camera capture (각도별 dataURL 여러 장, ENTRY_MIN_PHOTOS 이상) -> 각각 업로드 -> 대결 참가.
  // `tier`/`kind` say which battle card the user tapped 참가하기 on (Battle.jsx
  // passes these through route state so this doesn't just default to daily/내 그룹).
  const submitEntry = useCallback(async ({ name, description, tier, kind }) => {
    const battle = await api(`/battles/current${toQueryString({ tier, kind })}`);
    const photoIds = [];
    for (const dataUrl of draftPhotos) {
      const form = new FormData();
      form.append('file', await dataUrlToBlob(dataUrl), 'entry.jpg');
      photoIds.push((await api('/photos', { method: 'POST', form })).photo_id);
    }
    const join = await api(`/battles/${battle.id}/entries`, {
      method: 'POST',
      body: { photo_ids: photoIds, dish_name: name, description },
    });
    setUser((u) => ({ ...u, points: join.points }));
    setSubmission({
      battleId: battle.id,
      entryId: join.entry.id,
      name: join.entry.dish_name,
      photo: imageUrl(join.entry.photo_url),
      photos: join.entry.photo_urls.map(imageUrl),
      submittedAt: new Date(join.entry.created_at).getTime(),
      pointsAwarded: join.points_awarded, // 참가(+10P), 첫 참가(+30P), 3주 연속(+20P)이 합쳐진 실제 값
    });
  }, [draftPhotos]);

  // 토글이에요 (누를 때마다 반전) — 서버가 새 상태를 돌려줘요.
  const toggleNotify = useCallback(async (entryId) => (await api(`/entries/${entryId}/notify`, { method: 'POST' })).notify_on_close, []);

  // Full EntryListOut, not just the array, so Vote.jsx can show the battle's own
  // title/participant count without a separate fetchBattle() call (voting can be
  // for a battle that isn't the "current" one anymore).
  const fetchEntries = useCallback(async (battleId) => {
    const list = await api(`/battles/${battleId}/entries`);
    if (list.my_vote_entry_id) setVotedEntryId(list.my_vote_entry_id);
    return {
      title: list.title,
      tierLabel: list.tier_label,
      participants: list.participants,
      canVote: list.can_vote,
      hasVoted: list.has_voted,
      hoursLeft: list.hours_left,
      items: list.items.map((e) => adaptEntry(e, user?.id)),
    };
  }, [user?.id]);

  const vote = useCallback(async (entryId) => {
    if (votedEntryId) return;
    setVotedEntryId(entryId); // optimistic; 1 vote per battle so this can't be undone anyway
    try {
      await api(`/entries/${entryId}/vote`, { method: 'POST' });
    } catch {
      setVotedEntryId(null);
    }
  }, [votedEntryId]);

  const fetchResult = useCallback(async (battleId) => adaptResult(await api(`/battles/${battleId}/result`)), []);

  // 우승자가 대결 결과 화면에서 자기 비법 레시피를 레시피 탭에 공유해요 (1인 1회).
  const shareRecipe = useCallback(async (entryId, body) => api(`/entries/${entryId}/recipe`, { method: 'POST', body }), []);

  const fetchShop = useCallback(async () => {
    const s = await api('/shop');
    setUser((u) => (u ? { ...u, points: s.points, level: s.level } : u));
    return s.items;
  }, []);

  const redeem = useCallback(async (itemId) => {
    const r = await api(`/shop/items/${itemId}/exchange`, { method: 'POST' });
    setUser((u) => ({ ...u, points: r.points }));
    return r;
  }, []);

  const value = useMemo(
    () => ({
      user, loggedIn, booting, online, setOnline,
      login, logout, signup, loginWithGoogle, checkNickname, checkUsername, updateProfile, fetchHome,
      savedIds, toggleSaved, fetchSavedRecipes, recentIds, fetchRecentRecipes, fetchMyReviewCount, fetchMyReviews, fetchMyRecipes,
      fetchRecipes, fetchRecipeCount, fetchRecipe,
      markViewed, comments, fetchComments, addComment,
      filters, setFilters, resetFilters: () => setFilters(EMPTY_FILTERS),
      draftPhotos, setDraftPhotos, submission, submitEntry,
      fetchBattle, fetchBattleHome, fetchEntries, votedEntryId, vote, fetchResult, shareRecipe, toggleNotify,
      fetchShop, redeem,
    }),
    [user, loggedIn, booting, online, login, logout, signup, loginWithGoogle, checkNickname, checkUsername, updateProfile, fetchHome,
      savedIds, toggleSaved, fetchSavedRecipes, recentIds, fetchRecentRecipes, fetchMyReviewCount, fetchMyReviews, fetchMyRecipes,
      fetchRecipes, fetchRecipeCount, fetchRecipe, markViewed, comments, fetchComments, addComment,
      filters, draftPhotos, submission, submitEntry, fetchBattle, fetchBattleHome, fetchEntries, votedEntryId, vote,
      fetchResult, shareRecipe, toggleNotify, fetchShop, redeem],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>');
  return ctx;
}
