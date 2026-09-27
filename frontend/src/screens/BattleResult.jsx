import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Screen, TopBar, BottomAction } from '../components/Screen';
import Icon, { CrownArt } from '../components/Icon';
import { Button, Coin } from '../components/ui';
import { useApp } from '../state/AppContext';

const PODIUM = {
  1: { h: 100, av: 54, bar: 'var(--brand-grad-v)', ink: '#fff', avBg: 'linear-gradient(135deg, #DCC181, #C1A052)', avInk: '#6B5320' },
  2: { h: 70, av: 44, bar: 'linear-gradient(180deg, #FFFFFF, #EDEDED)', ink: '#4E4E4E' },
  3: { h: 52, av: 40, bar: 'linear-gradient(180deg, #FFFFFF, #EDEDED)', ink: '#4E4E4E', avBg: 'linear-gradient(135deg, #F7B89E, #D9684A)' },
};

export default function BattleResult() {
  const { fetchResult } = useApp();
  const [params] = useSearchParams();
  const battleId = params.get('battle');
  const [r, setR] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!battleId) return setError('아직 마감된 대결 결과가 없어요');
    fetchResult(battleId).then(setR).catch((e) => setError(e.message));
  }, [battleId, fetchResult]);

  if (error) {
    return (
      <Screen>
        <TopBar title="대결 결과" back="/battle" />
        <div className="body pad"><p className="muted" style={{ padding: '24px 0' }}>{error}</p></div>
      </Screen>
    );
  }
  if (!r) return null;

  const nameOf = (p) => (p.me ? `나 (${p.name})` : p.name);

  if (r.isVoid) {
    return (
      <Screen>
        <TopBar title="대결 결과" back="/battle" />
        <div className="body pad">
          <p className="result-meta">{r.title} · {r.group} · 참가자 {r.participants}명</p>
          <div className="card" style={{ marginTop: 12 }}>
            <p>대결이 무효 처리됐어요.</p>
            <p className="muted">참가자가 3명 미만이라 순위를 매기지 않아요. 참가 포인트는 그대로 지급됐어요.</p>
          </div>
        </div>
        <BottomAction className="bottom-action--tight"><Button to="/battle">확인</Button></BottomAction>
      </Screen>
    );
  }

  const top3 = [2, 1, 3].map((rank) => r.ranking.find((p) => p.rank === rank)).filter(Boolean);

  return (
    <Screen>
      <div className="result-hdr">
        <TopBar title="대결 결과" back="/battle" />
        <p className="result-meta">{r.title} · {r.group} · 참가자 {r.participants}명</p>
        <div className="podium">
          {top3.map((p) => {
            const s = PODIUM[p.rank];
            return (
              <div key={p.rank} className="pod">
                {p.rank === 1 && <CrownArt />}
                <span className="pav" style={{ width: s.av, height: s.av, fontSize: Math.round(s.av * 0.36), background: s.avBg, color: s.avInk }}>
                  {nameOf(p)[0]}
                </span>
                <span className="pod__name">{nameOf(p)}</span>
                <div className="bar" style={{ height: s.h, background: s.bar, color: s.ink }}>{p.rank}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="body">
        <div className="stack pad" style={{ gap: 10 }}>
          {r.joined && (
            <div className="card my-rank">
              <span className="my-rank__text">
                <span className="my-rank__label">내 순위</span>
                <span className="my-rank__value">{r.myRank}등</span>
              </span>
              <span className="my-rank__reward"><Coin />+{r.reward}P</span>
            </div>
          )}

          {r.levelUp && (
            <Link to="/shop" className="levelup">
              <span className="levelup__ico"><Icon name="arrowUp" size={20} strokeWidth={2.4} /></span>
              <span className="levelup__text">
                <span className="levelup__title">레벨 업! Lv.{r.levelUp.from} → Lv.{r.levelUp.to}</span>
                <span className="levelup__sub">상점에서 새 기프티콘이 열렸어요</span>
              </span>
              <Icon name="chevronRight" size={18} strokeWidth={2.4} color="#fff" />
            </Link>
          )}

          <section className="card ranking">
            <div className="ranking__head"><h2>TOP 10</h2><span>투표 수 기준</span></div>
            {r.ranking.map((p) => (
              <div key={p.rank} className={`lr ${p.me ? 'lr--me' : ''}`}>
                <span className="rk" style={p.rank === 1 ? { color: '#C98A00' } : undefined}>{p.rank}</span>
                <span className={`sav ${p.me ? 'sav--me' : ''} ${p.rank === 1 ? 'sav--gold' : ''}`}>{nameOf(p)[0]}</span>
                <span className="lr__who">
                  <span className="lr__name">{nameOf(p)}</span>
                  {p.sharedRecipe && <span className="lr__tag">레시피 공유</span>}
                  {p.note && <span className="lr__note">{p.note}</span>}
                </span>
                <b>{p.votes}표</b>
              </div>
            ))}
          </section>
        </div>
      </div>

      <BottomAction className="bottom-action--tight">
        <Button to="/battle">확인</Button>
      </BottomAction>
    </Screen>
  );
}
