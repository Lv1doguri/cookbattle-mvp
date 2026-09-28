import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Screen, Header, TopBar } from '../components/Screen';
import TabBar from '../components/TabBar';
import Icon, { EggArt } from '../components/Icon';
import { PointPill } from '../components/ui';
import { SKILLS } from '../data/mock';
import { useApp } from '../state/AppContext';
import useCountdown from '../hooks/useCountdown';

const TIER_NICK = { beginner: '새싹', intermediate: '자취러', advanced: '고든자취' };

// 참가하기 CTA는 대결(daily/theme)마다 상태가 달라요: 내 제출물이 이번 세션에 있으면
// 결과 화면으로, 서버가 이미 참가했다고 하면 정적 표시, 아니면 참가 가능 여부를 보여줘요.
function joinState(battle, submission) {
  if (submission?.battleId === battle.id) return 'mine';
  if (battle.hasJoined) return 'joined';
  if (battle.canJoin) return 'can-join';
  return 'closed';
}

function BattleCard({ battle, tone, tag, art, submission }) {
  const state = joinState(battle, submission);
  const countdown = useCountdown(battle.secondsLeft);
  return (
    <section className={`bcard bcard--${tone}`} aria-label={`${tag} · ${battle.topic}`}>
      <div className="bcard__head">
        <span className="bcard__tag">{tag}</span>
        {battle.isOpen && <span className="bcard__timer"><Icon name="clock" size={11} strokeWidth={2.8} />종료까지 {countdown}</span>}
      </div>
      <span className="bcard__art">{art}</span>
      <div className="bcard__title">{battle.topic}</div>
      <div className="bcard__sub">{battle.subtitle}</div>
      <div className="bcard__meta">
        {/* 일일 대결은 창이 최대 24시간이라 위 정밀 카운트다운(종료까지 HH:MM:SS)과 겹치므로 생략,
            테마 대결(3일 창)에서만 대략적인 "n일 남음"을 같이 보여줘요. */}
        {tone !== 'daily' && (
          <span className="bcard__dday"><Icon name="clock" size={12} strokeWidth={2.6} />{battle.daysLeft}일 남음</span>
        )}
        <span>참가자 {battle.participants}명</span>
      </div>
      {state === 'mine' && (
        <Link to="/battle/done" className="bcard__cta"><Icon name="check" size={16} strokeWidth={2.8} />참가 완료 · 내 출품작 보기</Link>
      )}
      {state === 'joined' && (
        <span className="bcard__cta" aria-disabled="true"><Icon name="check" size={16} strokeWidth={2.8} />참가 완료</span>
      )}
      {state === 'can-join' && (
        <Link to="/battle/camera" state={{ kind: battle.kind, tier: battle.tier }} className="bcard__cta">
          내 요리 출품하고 투표받기<span className="btn__tag">+3P</span>
        </Link>
      )}
      {state === 'closed' && (
        <span className="bcard__cta" aria-disabled="true">참가 마감</span>
      )}
    </section>
  );
}

// "실시간 랭킹" 미리보기 — 실제 투표 중인 대결의 현재 1·2위를 보여줘요(새 투표 방식이 아니라
// 기존 다자간 투표 화면의 상위 두 개를 미리 보여주는 용도). 숫자는 전부 실데이터예요.
function TopVsPreview({ battleId, hasVoted }) {
  const { fetchEntries } = useApp();
  const [entries, setEntries] = useState(null);

  useEffect(() => {
    let alive = true;
    fetchEntries(battleId).then((l) => { if (alive) setEntries(l.items); }).catch(() => {});
    return () => { alive = false; };
  }, [battleId, fetchEntries]);

  if (!entries || entries.length < 2) return null;
  const ranked = [...entries].sort((a, b) => b.hearts - a.hearts);
  const [first, second] = ranked;
  const total = ranked.reduce((sum, e) => sum + e.hearts, 0);
  const pct = (e) => (total > 0 ? Math.round((e.hearts / total) * 100) : 0);

  return (
    <Link to={`/battle/vote?battle=${battleId}`} className="vs-preview" style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
      <div className="vs-preview__head">
        <span className="vs-preview__title"><Icon name="trophy" size={15} strokeWidth={2.2} color="var(--brand-ink)" />실시간 랭킹 1·2위</span>
        <span className="vs-preview__total">참가작 {entries.length}개 · 총 {total}표</span>
      </div>
      <div className="vs-row">
        <span className="vs-item">
          <span className="vs-item__img">{first.photoUrl ? <img src={first.photoUrl} alt="" /> : <EggArt size={30} />}</span>
          <span className="vs-item__name">{first.name}</span>
          <span className="vs-item__votes">{first.hearts}표 ({pct(first)}%)</span>
        </span>
        <span className="vs-divider">VS</span>
        <span className="vs-item">
          <span className="vs-item__img">{second.photoUrl ? <img src={second.photoUrl} alt="" /> : <EggArt size={30} />}</span>
          <span className="vs-item__name">{second.name}</span>
          <span className="vs-item__votes">{second.hearts}표 ({pct(second)}%)</span>
        </span>
      </div>
      <div className="vs-preview__bar">
        <span style={{ width: `${pct(first)}%` }} />
        <span style={{ width: `${pct(second)}%` }} />
      </div>
      <span className="vs-preview__cta">{hasVoted ? '전체 순위 보기' : '지금 투표하러 가기 +1P'}</span>
    </Link>
  );
}

export default function Battle() {
  const { user, submission, fetchBattleHome } = useApp();
  const [group, setGroup] = useState(user?.skill);
  const [home, setHome] = useState(null);

  useEffect(() => {
    if (!group) return;
    let alive = true;
    setHome(null);
    fetchBattleHome(group).then((h) => { if (alive) setHome(h); }).catch(() => {});
    return () => { alive = false; };
  }, [group, fetchBattleHome]);

  if (!user) return null;
  const mine = group === user.skill;
  const groupLabel = SKILLS.find((s) => s.id === group).label;

  return (
    <Screen>
      <Header className="battle-hdr">
        <TopBar title="대결" brand>
          <PointPill points={user.points} to="/shop" />
        </TopBar>
        <div className="group-tabs" role="tablist" aria-label="대결 그룹">
          {SKILLS.map((s) => {
            const on = group === s.id;
            return (
              <button
                key={s.id} type="button" role="tab" aria-selected={on}
                className={`gseg ${on ? 'on' : ''}`} onClick={() => setGroup(s.id)}
              >
                <span className="sico" style={on ? { background: 'var(--brand-grad)', color: '#fff' } : { background: s.tint, color: s.ink }}>
                  <Icon name={s.icon} size={20} />
                </span>
                {s.label}
                <span className="gseg__sub">{TIER_NICK[s.id]}{s.id === user.skill ? ' · 내 그룹' : ''}</span>
              </button>
            );
          })}
        </div>
      </Header>

      <div className="body">
        <div className="stack pad">
          {!home ? (
            <p className="muted" style={{ padding: '16px 0' }}>불러오는 중…</p>
          ) : (
            <>
              <BattleCard
                battle={home.theme} tone="theme" tag="테마 대결" submission={submission}
                art={<Icon name="trophy" size={72} strokeWidth={1.4} color="#fff" />}
              />

              {!mine ? (
                <p className="battle-note"><Icon name="lock" size={14} strokeWidth={2.4} />내 실력 그룹 대결에만 참가할 수 있어요</p>
              ) : (
                <BattleCard
                  battle={home.daily} tone="daily" tag={`오늘의 대결 · ${groupLabel} ${TIER_NICK[group]}`} submission={submission}
                  art={<EggArt size={72} />}
                />
              )}

              {home.voting && (
                <>
                  <Link to={`/battle/vote?battle=${home.voting.battleId}`} className="pastcard">
                    <div className="pastcard__row">
                      <span className="pastcard__ico"><Icon name="trophy" size={22} /></span>
                      <span className="pastcard__text">
                        <span className="pastcard__title">지난 대회 투표하기</span>
                        <span className="pastcard__sub">
                          {home.voting.title} · 종료 후 24시간 동안 투표 가능
                        </span>
                      </span>
                      <Icon name="chevronRight" size={18} strokeWidth={2.4} color="var(--ink-6)" />
                    </div>
                    <div className="pastcard__bonuses">
                      <span className="bonus"><Icon name="clock" size={12} strokeWidth={2.6} />투표 마감까지 {home.voting.hoursLeft}시간</span>
                      <span className="bonus">{home.voting.hasVoted ? '투표 완료' : '투표 참여 시 +1P'}</span>
                    </div>
                  </Link>
                  <TopVsPreview battleId={home.voting.battleId} hasVoted={home.voting.hasVoted} />
                </>
              )}

              {home.daily.lastResult && (
                <Link to={`/battle/result?battle=${home.daily.lastResult.battle_id}`} className="card last-result">
                  <span className="last-result__ico"><Icon name="trophy" size={22} /></span>
                  <span className="last-result__text">
                    <span className="last-result__title">지난 대결 결과</span>
                    <span className="last-result__sub">
                      {home.daily.lastResult.title} · {home.daily.lastResult.status === 'void' ? '무효' : home.daily.lastResult.my_rank ? `내 순위 ${home.daily.lastResult.my_rank}등` : '참가 안 함'}
                    </span>
                  </span>
                  <Icon name="chevronRight" size={18} strokeWidth={2.4} color="var(--ink-6)" />
                </Link>
              )}
            </>
          )}
        </div>
      </div>

      <TabBar />
    </Screen>
  );
}
