import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Screen, Header, TopBar } from '../components/Screen';
import TabBar from '../components/TabBar';
import Icon from '../components/Icon';
import { Avatar, FoodThumb, Badge } from '../components/ui';
import { adaptRecipeCard } from '../api/adapt';
import { skillLabel, won } from '../data/mock';
import { useApp } from '../state/AppContext';

export default function Menu() {
  const { user, fetchSavedRecipes, fetchRecentRecipes, fetchMyReviewCount, logout } = useApp();
  const navigate = useNavigate();
  const [saved, setSaved] = useState(null);
  const [recentCount, setRecentCount] = useState(null);
  const [firstRecentId, setFirstRecentId] = useState(null);
  const [reviewCount, setReviewCount] = useState(null);

  useEffect(() => {
    fetchSavedRecipes().then((items) => setSaved(items.map(adaptRecipeCard))).catch(() => setSaved([]));
    fetchRecentRecipes().then((items) => { setRecentCount(items.length); setFirstRecentId(items[0]?.id ?? null); }).catch(() => setRecentCount(0));
    fetchMyReviewCount().then(setReviewCount).catch(() => setReviewCount(0));
  }, [fetchSavedRecipes, fetchRecentRecipes, fetchMyReviewCount]);

  if (!user) return null;

  const rows = [
    { icon: 'bookmark', label: '저장한 레시피', count: saved ? `${saved.length}개` : null, to: '#saved' },
    { icon: 'history', label: '최근 본 레시피', count: recentCount ? `${recentCount}개` : null, to: firstRecentId ? `/recipes/${firstRecentId}` : '/recipes' },
    { icon: 'comment', label: '내가 쓴 후기', count: reviewCount === null ? null : `${reviewCount}개`, to: '/recipes' },
    { icon: 'bell', label: '알림 설정', to: '/menu' },
    { icon: 'play', label: '튜토리얼 다시 보기', to: '/onboarding' },
  ];

  return (
    <Screen>
      <Header className="menu-hdr">
        <TopBar title="메뉴" brand />
        <Link to="/profile/edit" className="card profile-card">
          <Avatar name={user.nickname} src={user.avatar} size={48} />
          <span className="profile-card__text">
            <span className="profile-card__name">{user.nickname}<Badge>Lv.{user.level}</Badge></span>
            <span className="profile-card__sub">{skillLabel(user.skill)} 대결 그룹 · {won(user.points)}P</span>
          </span>
          <Icon name="chevronRight" size={18} strokeWidth={2.4} color="#898989" />
        </Link>
      </Header>

      <div className="body">
        <div className="stack pad">
          <nav className="card menu-list" aria-label="메뉴">
            {rows.map((r) =>
              r.to.startsWith('#') ? (
                <a key={r.label} className="row" href={r.to} onClick={(e) => { e.preventDefault(); document.getElementById('saved')?.scrollIntoView({ behavior: 'smooth' }); }}>
                  <span className="ico ico--sm"><Icon name={r.icon} size={20} /></span>
                  <span className="row__label">{r.label}</span>
                  {r.count && <span className="cnt">{r.count}</span>}
                  <Icon name="chevronRight" size={16} strokeWidth={2.4} color="#A3AA9C" />
                </a>
              ) : (
                <Link key={r.label} className="row" to={r.to}>
                  <span className="ico ico--sm"><Icon name={r.icon} size={20} /></span>
                  <span className="row__label">{r.label}</span>
                  {r.count && <span className="cnt">{r.count}</span>}
                  <Icon name="chevronRight" size={16} strokeWidth={2.4} color="#A3AA9C" />
                </Link>
              ),
            )}
          </nav>

          <section id="saved" className="card saved">
            <h2 className="saved__title">저장한 레시피</h2>
            {saved === null ? (
              <p className="muted">불러오는 중…</p>
            ) : saved.length === 0 ? (
              <div className="saved__empty">
                <span className="saved__empty-ico"><Icon name="bookmark" size={26} /></span>
                <p>아직 저장한 레시피가 없어요</p>
                <Link to="/recipes" className="btn btn--primary btn--sm">레시피 둘러보기</Link>
              </div>
            ) : (
              <div className="saved__list">
                {saved.map((r) => (
                  <Link key={r.id} to={`/recipes/${r.id}`} className="saved__item">
                    <FoodThumb tone={r.tone} size={64} iconSize={28} style={{ borderRadius: 16 }} />
                    <span>{r.name}</span>
                  </Link>
                ))}
              </div>
            )}
          </section>

          <button type="button" className="logout" onClick={() => { logout(); navigate('/', { replace: true }); }}>로그아웃</button>
        </div>
      </div>

      <TabBar />
    </Screen>
  );
}
