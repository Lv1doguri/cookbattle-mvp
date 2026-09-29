import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Screen, Header, TopBar, IconButton } from '../components/Screen';
import TabBar from '../components/TabBar';
import Icon from '../components/Icon';
import { Avatar, Badge, Button, ProgressBar } from '../components/ui';
import { skillLabel, won } from '../data/mock';
import { useApp } from '../state/AppContext';
import useCountdown from '../hooks/useCountdown';
import logo from '../assets/logo.png';

// 오늘의 대결 주제(테마)별 홈 배너 문구. 테마 자체는 실제 서버 값이고, 이 문구는 순수 카피예요.
const THEME_HOOK = {
  '밥 요리': { emoji: '🍚', title: '든든한 집밥의 정석!', sub: '자취방 냉장고 속 재료로 승부하세요' },
  '면 요리': { emoji: '🍝', title: '면치기의 신들이 모였다!', sub: '오늘은 면 요리 실력을 증명할 시간' },
  '5천원 이하': { emoji: '💸', title: '자취생 가성비 끝판왕!', sub: '5,000원으로 만드는 기적의 한 끼' },
  '계란 요리': { emoji: '🥚', title: '계란 하나로 승부한다!', sub: '냉장고 속 계란을 꺼내보세요' },
  '라면': { emoji: '🥇', title: '자취 라면의 대변신!', sub: '집에 있는 라면으로 최고급 요리를 만들어라!' },
  '고기 요리': { emoji: '🍖', title: '오늘은 육식파의 날!', sub: '자취방 불맛을 제대로 보여주세요' },
  '건강한 요리': { emoji: '🥗', title: '자취생 헬스밥상 챌린지!', sub: '건강까지 챙기는 슬기로운 자취생활' },
  '디저트': { emoji: '🍰', title: '달콤한 자취 디저트 타임!', sub: '후식까지 완벽하게 마무리하세요' },
};

function TodayBanner() {
  const { fetchBattle } = useApp();
  const [battle, setBattle] = useState(null);

  useEffect(() => {
    let alive = true;
    fetchBattle().then((b) => { if (alive) setBattle(b); }).catch(() => {});
    return () => { alive = false; };
  }, [fetchBattle]);

  const countdown = useCountdown(battle?.secondsLeft);
  if (!battle) return null;
  const hook = THEME_HOOK[battle.topic] ?? { emoji: '🔥', title: `오늘의 대결: ${battle.topic}`, sub: battle.subtitle };
  const joinable = battle.canJoin && !battle.hasJoined;
  const to = battle.hasJoined || !joinable ? '/battle' : { pathname: '/battle/camera' };
  const ctaText = battle.hasJoined ? '내 출품작 보기' : joinable ? '지금 출품하기' : '대결 현황 보기';

  return (
    <Link to={to} state={joinable ? { kind: 'daily', tier: battle.tier } : undefined} className="today-banner">
      <div className="today-banner__head">
        <span className="today-banner__tag">오늘의 데일리 매치</span>
        {battle.isOpen && <span className="today-banner__timer"><Icon name="clock" size={11} strokeWidth={2.8} />종료까지 {countdown}</span>}
      </div>
      <div className="today-banner__title">{hook.emoji} {hook.title}</div>
      <p className="today-banner__sub">{hook.sub}</p>
      <div className="today-banner__foot">
        <span>참가자 {battle.participants}명</span>
        <span className="today-banner__cta">
          {ctaText}
          <Icon name="chevronRight" size={14} strokeWidth={2.8} />
        </span>
      </div>
    </Link>
  );
}

export default function Home() {
  const { user, submission, fetchHome } = useApp();
  const [history, setHistory] = useState(null);

  useEffect(() => {
    let alive = true;
    fetchHome().then((h) => { if (alive) setHistory(h.history); }).catch(() => { if (alive) setHistory([]); });
    return () => { alive = false; };
  }, [fetchHome]);

  if (!user) return null;

  return (
    <Screen>
      <Header className="home-hdr">
        <TopBar title="자취 요리왕" brand logo={logo}>
          <IconButton label="알림" to="/home" dot><Icon name="bell" size={22} /></IconButton>
        </TopBar>

        <section className="hero home-hero" aria-label="내 레벨과 포인트">
          <div className="home-hero__row">
            <Avatar name={user.nickname} src={user.avatar} size={48} className="av--glass" />
            <div className="home-hero__who">
              <div className="home-hero__name">
                {user.nickname}<Badge tone="white">Lv.{user.level}</Badge>
              </div>
              <div className="home-hero__group">{skillLabel(user.skill)} 대결 그룹</div>
            </div>
            <div className="home-hero__pts">
              <div className="home-hero__pts-label">보유 포인트</div>
              <div className="home-hero__pts-value">{won(user.points)}P</div>
            </div>
          </div>
          <div style={{ marginTop: 18 }}><ProgressBar value={user.levelProgress} /></div>
          <div className="home-hero__next">
            <span>다음 레벨까지 {user.pointsToNextLevel}P</span>
            <span style={{ fontWeight: 700 }}>Lv.{user.level + 1}</span>
          </div>
        </section>
      </Header>

      <div className="body">
        <div className="stack pad">
          <TodayBanner />

          <div className="home-stats">
            <div className="card home-stat">
              <span className="ico" style={{ background: 'var(--surface-3)', color: 'var(--brand-ink)' }}><Icon name="tabRecipe" size={22} /></span>
              <div className="home-stat__label">이번 달 요리</div>
              <div className="home-stat__value">{user.monthlyCooks}회</div>
            </div>
            <div className="card home-stat">
              <span className="ico" style={{ background: 'var(--surface-2)', color: 'var(--brand-ink)' }}><Icon name="wallet" size={22} /></span>
              <div className="home-stat__label">절약한 식비</div>
              <div className="home-stat__value">{won(user.savedMoney)}원</div>
            </div>
          </div>

          <section className="card history">
            <div className="history__head">
              <h2>참가 이력</h2>
              <Link to="/battle" className="history__more">대결 보기 ›</Link>
            </div>
            {submission && (
              <div className="history__row">
                <span className="ico ico--round" style={{ background: '#EFE9D2', color: '#8A6A38' }}><Icon name="egg" size={20} /></span>
                <div className="history__text">
                  <div className="history__title">{submission.name}</div>
                  <div className="history__meta">진행 중 · {skillLabel(user.skill)} 그룹</div>
                </div>
                <Badge tone="neutral" className="badge--lg">출품됨</Badge>
              </div>
            )}
            {history === null ? (
              <p className="muted" style={{ padding: '10px 0' }}>불러오는 중…</p>
            ) : history.length === 0 && !submission ? (
              <p className="muted" style={{ padding: '10px 0' }}>아직 참가한 대결이 없어요</p>
            ) : (
              history.map((h) => (
                <div key={h.id} className="history__row">
                  <span className="ico ico--round" style={{ background: '#EFE9D2', color: '#8A6A38' }}><Icon name="egg" size={20} /></span>
                  <div className="history__text">
                    <div className="history__title">{h.title}</div>
                    <div className="history__meta">{h.meta}</div>
                  </div>
                  <Badge tone={h.medal ? 'gold' : 'neutral'} className="badge--lg">{h.result}</Badge>
                </div>
              ))
            )}
          </section>

          <Button to="/profile/edit" variant="secondary"><Icon name="edit" size={18} />정보 수정</Button>
        </div>
      </div>

      <TabBar />
    </Screen>
  );
}
