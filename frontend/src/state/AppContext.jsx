import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, dataUrlToBlob, getToken, imageUrl, setToken } from '../api/client';
import { adaptBattle, adaptEntry, adaptResult, adaptUser, filtersToParams, quickFilterParams, toQueryString } from '../api/adapt';

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
  const [draftPhoto, setDraftPhoto] = useState(null); // dataURL from the in-app camera
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

  const signup = useCallback(async ({ nickname, skill, password }) => {
    const r = await api('/auth/signup', { method: 'POST', auth: false, body: { nickname, password, tier: skill } });
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

  const fetchComments = useCallback(async (recipeId) => {
    const page = await api(`/recipes/${recipeId}/reviews`);
    const list = page.items.map((r) => ({ author: r.author.nickname, text: r.text }));
    setComments((c) => ({ ...c, [recipeId]: list }));
    return list;
  }, []);

  const addComment = useCallback(async (recipeId, text) => {
    await api(`/recipes/${recipeId}/reviews`, { method: 'POST', body: { text } });
    setComments((c) => ({ ...c, [recipeId]: [...(c[recipeId] ?? []), { author: user?.nickname, text }] }));
  }, [user?.nickname]);

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

  const fetchBattle = useCallback(async (tier) => adaptBattle(await api(`/battles/current${toQueryString({ tier })}`)), []);

  // Camera capture (a data: URL) -> uploaded photo -> a battle entry.
  const submitEntry = useCallback(async ({ name, description }) => {
    const battle = await api('/battles/current'); // defaults to my own group
    const form = new FormData();
    form.append('file', await dataUrlToBlob(draftPhoto), 'entry.jpg');
    const photo = await api('/photos', { method: 'POST', form });
    const join = await api(`/battles/${battle.id}/entries`, {
      method: 'POST',
      body: { photo_id: photo.photo_id, dish_name: name, description },
    });
    setUser((u) => ({ ...u, points: join.points }));
    setSubmission({
      battleId: battle.id,
      entryId: join.entry.id,
      name: join.entry.dish_name,
      photo: imageUrl(join.entry.photo_url),
      submittedAt: new Date(join.entry.created_at).getTime(),
    });
  }, [draftPhoto]);

  const fetchEntries = useCallback(async (battleId) => {
    const list = await api(`/battles/${battleId}/entries`);
    if (list.my_vote_entry_id) setVotedEntryId(list.my_vote_entry_id);
    return list.items.map((e) => adaptEntry(e, user?.id));
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
      login, logout, signup, checkNickname, updateProfile, fetchHome,
      savedIds, toggleSaved, fetchSavedRecipes, recentIds, fetchRecentRecipes, fetchMyReviewCount,
      fetchRecipes, fetchRecipeCount, fetchRecipe,
      markViewed, comments, fetchComments, addComment,
      filters, setFilters, resetFilters: () => setFilters(EMPTY_FILTERS),
      draftPhoto, setDraftPhoto, submission, submitEntry,
      fetchBattle, fetchEntries, votedEntryId, vote, fetchResult,
      fetchShop, redeem,
    }),
    [user, loggedIn, booting, online, login, logout, signup, checkNickname, updateProfile, fetchHome,
      savedIds, toggleSaved, fetchSavedRecipes, recentIds, fetchRecentRecipes, fetchMyReviewCount,
      fetchRecipes, fetchRecipeCount, fetchRecipe, markViewed, comments, fetchComments, addComment,
      filters, draftPhoto, submission, submitEntry, fetchBattle, fetchEntries, votedEntryId, vote,
      fetchResult, fetchShop, redeem],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>');
  return ctx;
}
