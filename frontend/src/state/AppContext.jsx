import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { INITIAL_USER, TAKEN_NICKNAMES } from '../data/mock';

// Single client-side store for the MVP. Every action here is the place a real
// API call would go later (login, signup, submitEntry, vote, redeem, ...).
const AppContext = createContext(null);

const EMPTY_FILTERS = { category: [], budget: [], time: [], skill: [] };

export function AppProvider({ children }) {
  const [user, setUser] = useState(INITIAL_USER);
  const [loggedIn, setLoggedIn] = useState(false);
  const [savedIds, setSavedIds] = useState([]);
  const [recentIds, setRecentIds] = useState([]);
  const [comments, setComments] = useState({}); // recipeId -> [{ author, text }]
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [draftPhoto, setDraftPhoto] = useState(null); // dataURL from the in-app camera
  const [submission, setSubmission] = useState(null); // { name, description, photo, submittedAt }
  const [votedEntryId, setVotedEntryId] = useState(null);
  const [redemptions, setRedemptions] = useState([]);
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

  const login = useCallback((email) => {
    setUser((u) => ({ ...u, email: email || u.email }));
    setLoggedIn(true);
  }, []);

  const logout = useCallback(() => setLoggedIn(false), []);

  const isNicknameTaken = useCallback(
    (name) => TAKEN_NICKNAMES.includes(name.trim()) && name.trim() !== user.nickname,
    [user.nickname],
  );

  const signup = useCallback(({ nickname, skill }) => {
    setUser((u) => ({ ...u, nickname, skill }));
    setLoggedIn(true);
  }, []);

  const updateProfile = useCallback((patch) => setUser((u) => ({ ...u, ...patch })), []);

  const toggleSaved = useCallback(
    (id) => setSavedIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [id, ...ids])),
    [],
  );

  const markViewed = useCallback(
    (id) => setRecentIds((ids) => [id, ...ids.filter((x) => x !== id)].slice(0, 10)),
    [],
  );

  const addComment = useCallback(
    (recipeId, text) =>
      setComments((c) => ({ ...c, [recipeId]: [...(c[recipeId] ?? []), { author: user.nickname, text }] })),
    [user.nickname],
  );

  const submitEntry = useCallback(({ name, description }) => {
    setSubmission({ name, description, photo: draftPhoto, submittedAt: Date.now() });
    setUser((u) => ({ ...u, points: u.points + 1 }));
  }, [draftPhoto]);

  const vote = useCallback((entryId) => setVotedEntryId((v) => v ?? entryId), []);

  const redeem = useCallback(
    (item) => {
      if (user.points < item.price || user.level < item.minLevel) return false;
      setUser((u) => ({ ...u, points: u.points - item.price }));
      setRedemptions((r) => [{ itemId: item.id, at: Date.now() }, ...r]);
      return true;
    },
    [user.points, user.level],
  );

  const value = useMemo(
    () => ({
      user, loggedIn, login, logout, signup, isNicknameTaken, updateProfile,
      savedIds, toggleSaved, recentIds, markViewed,
      comments, addComment,
      filters, setFilters, resetFilters: () => setFilters(EMPTY_FILTERS),
      draftPhoto, setDraftPhoto, submission, submitEntry,
      votedEntryId, vote,
      redemptions, redeem,
      online, setOnline,
    }),
    [user, loggedIn, login, logout, signup, isNicknameTaken, updateProfile, savedIds, toggleSaved, recentIds,
      markViewed, comments, addComment, filters, draftPhoto, submission, submitEntry, votedEntryId, vote,
      redemptions, redeem, online],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>');
  return ctx;
}
