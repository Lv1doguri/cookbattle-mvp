import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Screen, Header, TopBar } from '../components/Screen';
import TabBar from '../components/TabBar';
import Icon from '../components/Icon';
import { Avatar, Coin, FoodThumb } from '../components/ui';
import { adaptRecipeCard } from '../api/adapt';
import { skillLabel, won } from '../data/mock';
import { useApp } from '../state/AppContext';

const STREAK_CYCLE = 3; // 백엔드 STREAK_WEEKS와 동일 (3주 연속마다 보너스)

export default function Menu() {
  const {
    user, fetchSavedRecipes, fetchRecentRecipes, fetchMyReviewCount, fetchMyReviews, fetchMyRecipes, logout,
  } = useApp();
  const navigate = useNavigate();
  const [saved, setSaved] = useState(null);
  const [recentCount, setRecentCount] = useState(null);
  const [firstRecentId, setFirstRecentId] = useState(null);
  const [reviewCount, setReviewCount] = useState(null);
  const [reviews, setReviews] = useState(null);
  const [myRecipes, setMyRecipes] = useState(null);
  const [tab, setTab] = useState('dishes');
  const [notifyOn, setNotifyOn] = useState(true);

  useEffect(() => {
    fetchSavedRecipes().then((items) => setSaved(items.map(adaptRecipeCard))).catch(() => setSaved([]));
    fetchRecentRecipes().then((items) => { setRecentCount(items.length); setFirstRecentId(items[0]?.id ?? null); }).catch(() => setRecentCount(0));
    fetchMyReviewCount().then(setReviewCount).catch(() => setReviewCount(0));
    fetchMyReviews().then(setReviews).catch(() => setReviews([]));
    fetchMyRecipes().then((items) => setMyRecipes(items.map(adaptRecipeCard))).catch(() => setMyRecipes([]));
  }, [fetchSavedRecipes, fetchRecentRecipes, fetchMyReviewCount, fetchMyReviews, fetchMyRecipes]);

  if (!user) return null;

  const rows = [
    { icon: 'history', label: '최근 본 레시피', count: recentCount ? `${recentCount}개` : null, to: firstRecentId ? `/recipes/${firstRecentId}` : '/recipes' },
    { icon: 'bell', label: '배틀 알림 및 마감 알림', toggle: true },
    { icon: 'store', label: '자취쿡 고객센터 & 공지사항', inert: true },
    { icon: 'play', label: '튜토리얼 다시 보기', to: '/onboarding' },
  ];

  const streakDotsOn = user.streakWeeks ? ((user.streakWeeks - 1) % STREAK_CYCLE) + 1 : 0;

  return (
    <Screen>
      <Header className="menu-hdr">
        <TopBar title="마이페이지" brand />
      </Header>

      <div className="body">
        <div className="stack pad">
          <Link to="/profile/edit" className="card profile-card2">
            <Avatar name={user.nickname} src={user.avatar} size={64} />
            <div className="profile-card2__body">
              <div className="profile-card2__row">
                <h2>{user.nickname}</h2>
                <span className="edit-pill">수정<Icon name="chevronRight" size={13} strokeWidth={2.4} /></span>
              </div>
              <span className="tier-pill">{skillLabel(user.skill)} · Lv.{user.level}</span>
            </div>
          </Link>

          <div className="card bento4">
            <div><span>저장 레시피</span><b>{saved ? saved.length : '-'}</b></div>
            <div><span>작성 후기</span><b>{reviewCount ?? '-'}</b></div>
            <div><span>출품 레시피</span><b>{myRecipes ? myRecipes.length : '-'}</b></div>
            <div><span>레벨</span><b>Lv.{user.level}</b></div>
          </div>

          <div className="card wallet-card">
            <div className="wallet-card__head"><Icon name="wallet" size={16} strokeWidth={2} />자취 포인트 &amp; 지갑</div>
            <div className="wallet-card__amount"><Coin size={26} />{won(user.points)}<small>P</small></div>
            <div className="wallet-card__actions">
              <Link to="/shop" className="btn btn--primary btn--sm">포인트 교환소 가기</Link>
              <button type="button" className="btn btn--muted btn--sm" disabled title="다음 업데이트에서 준비 중이에요">적립/사용 내역</button>
            </div>
          </div>

          <div className="card streak-card">
            <div className="streak-card__head">
              <span>🔥 배틀 참가 스트릭</span>
              <span>{user.streakWeeks ? `${user.streakWeeks}주 연속 참가 중!` : '이번 주부터 시작해보세요'}</span>
            </div>
            <div className="streak-dots">
              {Array.from({ length: STREAK_CYCLE }, (_, i) => (
                <span key={i} className={`streak-dot${i < streakDotsOn ? ' on' : ''}`}>{i + 1}</span>
              ))}
            </div>
          </div>

          <div className="seg2" role="tablist" aria-label="내 활동">
            <button type="button" className={tab === 'dishes' ? 'on' : ''} onClick={() => setTab('dishes')}>출품 레시피 ({myRecipes?.length ?? 0})</button>
            <button type="button" className={tab === 'saved' ? 'on' : ''} onClick={() => setTab('saved')}>스크랩 ({saved?.length ?? 0})</button>
            <button type="button" className={tab === 'reviews' ? 'on' : ''} onClick={() => setTab('reviews')}>리얼 후기 ({reviews?.length ?? 0})</button>
          </div>

          {tab === 'dishes' && (
            myRecipes === null ? <p className="muted" style={{ margin: '12px 16px' }}>불러오는 중…</p>
              : myRecipes.length === 0 ? (
                <p className="muted" style={{ margin: '12px 16px' }}>아직 대결에서 우승한 레시피가 없어요. 배틀에서 1등하면 여기 자동으로 올라와요!</p>
              ) : (
                <div className="dish-list">
                  {myRecipes.map((r) => (
                    <Link key={r.id} to={`/recipes/${r.id}`} className="dish-row">
                      <FoodThumb tone={r.tone} size={56} iconSize={24} photo={r.photoUrl} style={{ borderRadius: 14 }} />
                      <span className="dish-row__body">
                        <span className="dish-row__name">{r.name}</span>
                        <span className="dish-row__meta">{r.award || '내 출품작'}</span>
                      </span>
                    </Link>
                  ))}
                </div>
              )
          )}

          {tab === 'saved' && (
            saved === null ? <p className="muted" style={{ margin: '12px 16px' }}>불러오는 중…</p>
              : saved.length === 0 ? (
                <div className="saved__empty" style={{ margin: '12px 16px' }}>
                  <span className="saved__empty-ico"><Icon name="bookmark" size={26} /></span>
                  <p>아직 저장한 레시피가 없어요</p>
                  <Link to="/recipes" className="btn btn--primary btn--sm">레시피 둘러보기</Link>
                </div>
              ) : (
                <div className="dish-list">
                  {saved.map((r) => (
                    <Link key={r.id} to={`/recipes/${r.id}`} className="dish-row">
                      <FoodThumb tone={r.tone} size={56} iconSize={24} photo={r.photoUrl} style={{ borderRadius: 14 }} />
                      <span className="dish-row__body">
                        <span className="dish-row__name">{r.name}</span>
                        <span className="dish-row__meta">{r.category}</span>
                      </span>
                    </Link>
                  ))}
                </div>
              )
          )}

          {tab === 'reviews' && (
            reviews === null ? <p className="muted" style={{ margin: '12px 16px' }}>불러오는 중…</p>
              : reviews.length === 0 ? (
                <p className="muted" style={{ margin: '12px 16px' }}>아직 남긴 후기가 없어요.</p>
              ) : (
                <div className="stack" style={{ marginTop: 4 }}>
                  {reviews.map((r, i) => (
                    <Link key={i} to={`/recipes/${r.recipeId}`} className="review-row" style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
                      <b>{r.recipeName}</b>
                      <p>{r.text}</p>
                    </Link>
                  ))}
                </div>
              )
          )}

          <h3 className="sec" style={{ margin: '20px 16px 2px', fontSize: 14, color: 'var(--ink-4)' }}>자취러 편의 도구함 &amp; 설정</h3>
          <nav className="card menu-list" aria-label="설정">
            {rows.map((r) =>
              r.toggle ? (
                <div key={r.label} className="row row--inert">
                  <span className="ico ico--sm"><Icon name={r.icon} size={20} /></span>
                  <span className="row__label">{r.label}</span>
                  <span
                    className={`toggle2${notifyOn ? ' on' : ''}`} role="switch" aria-checked={notifyOn}
                    onClick={() => setNotifyOn((v) => !v)}
                  />
                </div>
              ) : r.inert ? (
                <div key={r.label} className="row row--inert">
                  <span className="ico ico--sm"><Icon name={r.icon} size={20} /></span>
                  <span className="row__label">{r.label}</span>
                  <Icon name="chevronRight" size={16} strokeWidth={2.4} color="#A3AA9C" />
                </div>
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

          <button type="button" className="logout" onClick={() => { logout(); navigate('/', { replace: true }); }}>로그아웃</button>
        </div>
      </div>

      <TabBar />
    </Screen>
  );
}
