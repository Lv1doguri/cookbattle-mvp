import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Screen, Header, TopBar } from '../components/Screen';
import Icon, { EggArt } from '../components/Icon';
import { useApp } from '../state/AppContext';

function VoteButton({ entry, votedEntryId, onVote, size }) {
  if (entry.mine) return <button type="button" className={`vb off ${size ? `vb--${size}` : ''}`} disabled>투표 불가</button>;
  if (entry.voted) {
    return (
      <button type="button" className={`vb done ${size ? `vb--${size}` : ''}`} disabled>
        <Icon name="check" size={14} strokeWidth={3} />투표 완료
      </button>
    );
  }
  return (
    <button
      type="button" className={`vb ${votedEntryId ? 'off' : ''} ${size ? `vb--${size}` : ''}`}
      disabled={!!votedEntryId} onClick={() => onVote(entry.id)}
    >
      투표하기 +1P
    </button>
  );
}

export default function Vote() {
  const { votedEntryId, vote, fetchEntries } = useApp();
  const [params] = useSearchParams();
  const battleId = params.get('battle');
  const [list, setList] = useState(null); // { title, participants, hoursLeft, items } | 'error'

  useEffect(() => {
    if (!battleId) return setList('error');
    let alive = true;
    setList(null);
    fetchEntries(battleId).then((l) => { if (alive) setList(l); }).catch(() => { if (alive) setList('error'); });
    return () => { alive = false; };
  }, [battleId, fetchEntries]);

  const entries = list && list !== 'error' ? list.items : null;
  // 실시간 순위 — 표를 넣을 때마다 이 정렬도 같이 바뀌어요.
  const ranked = entries ? [...entries].sort((a, b) => b.hearts - a.hearts) : null;
  const totalVotes = ranked ? ranked.reduce((sum, e) => sum + e.hearts, 0) : 0;
  const top3 = ranked?.slice(0, 3) ?? [];
  const rest = ranked?.slice(3) ?? [];
  const pct = (e) => (totalVotes > 0 ? Math.round((e.hearts / totalVotes) * 100) : 0);

  const onVote = async (id) => {
    setList((l) => ({ ...l, items: l.items.map((e) => (e.id === id ? { ...e, hearts: e.hearts + 1 } : e)) }));
    await vote(id);
  };

  return (
    <Screen>
      <Header className="vote-hdr">
        <TopBar title="투표" back="/battle">
          <span className="vote-rule">1인 1표</span>
        </TopBar>
        <div className="vote-intro">
          <div className="vote-intro__title">{list && list !== 'error' ? list.title : '대결'}</div>
          <div className="vote-intro__sub">
            {entries ? `출품작 ${entries.length}개 · ` : ''}
            {votedEntryId ? '투표를 마쳤어요' : '마음에 드는 한 접시를 골라주세요'}
          </div>
          {list && list !== 'error' && (
            <div className="vote-badges">
              {list.hoursLeft != null && (
                <span className="vote-badge"><Icon name="clock" size={12} strokeWidth={2.6} />투표 마감까지 {list.hoursLeft}시간</span>
              )}
              <span className="vote-badge">총 {totalVotes}표 집계 중</span>
            </div>
          )}
        </div>
      </Header>

      <div className="body">
        {list === null && <p className="muted" style={{ padding: '16px' }}>불러오는 중…</p>}
        {list === 'error' && <p className="muted" style={{ padding: '16px' }}>투표할 대결을 찾을 수 없어요</p>}

        {top3.length > 0 && (
          <section className="pad" style={{ paddingBottom: 4 }}>
            <h2 className="sec sec--tight">
              <Icon name="trophy" size={16} strokeWidth={2.2} style={{ marginRight: 4, verticalAlign: -3 }} />
              실시간 명예의 전당 TOP{top3.length}
            </h2>

            <div className={`card vtop1 ${top3[0].mine ? 'vcard--mine' : ''}`}>
              <span className="vtop1__rank">1위</span>
              <div className="vtop1__img">
                {top3[0].photoUrl ? <img src={top3[0].photoUrl} alt="" /> : <EggArt size={54} />}
                {top3[0].mine && <span className="vcard__mine">내 작품</span>}
              </div>
              <div className="vtop1__name">{top3[0].name}</div>
              <div className="vtop1__by">
                by {top3[0].author} · <span className="hrt"><Icon name="heart" size={12} fill="currentColor" />{top3[0].hearts}표 ({pct(top3[0])}%)</span>
              </div>
              <div className="pbar"><div className="pbar__fill" style={{ width: `${pct(top3[0])}%` }} /></div>
              <VoteButton entry={top3[0]} votedEntryId={votedEntryId} onVote={onVote} />
            </div>

            {top3.length > 1 && (
              <div className="vote-grid" style={{ padding: '12px 0 0' }}>
                {top3.slice(1).map((e, i) => (
                  <div key={e.id} className={`card vcard ${e.mine ? 'vcard--mine' : ''}`}>
                    <span className="vcard__rank">{i + 2}위</span>
                    <div className="vcard__img">
                      {e.photoUrl ? <img src={e.photoUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <EggArt size={54} />}
                      {e.mine && <span className="vcard__mine">내 작품</span>}
                    </div>
                    <div className="vcard__name">{e.name}</div>
                    <div className="vcard__by">
                      by {e.author} · <span className="hrt"><Icon name="heart" size={12} fill="currentColor" />{e.hearts}</span>
                    </div>
                    <VoteButton entry={e} votedEntryId={votedEntryId} onVote={onVote} />
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {rest.length > 0 && (
          <section className="pad">
            <h2 className="sec sec--tight">실시간 참가작 순위</h2>
            <div className="vlist">
              {rest.map((e, i) => (
                <div key={e.id} className={`vrow ${e.mine ? 'vrow--mine' : ''}`}>
                  <span className="vrow__rank">{i + 4}</span>
                  <div className="vrow__img">
                    {e.photoUrl ? <img src={e.photoUrl} alt="" /> : <EggArt size={28} />}
                  </div>
                  <span className="vrow__body">
                    <span className="vrow__name">{e.name}</span>
                    <span className="vrow__by">by {e.author} · <span className="hrt"><Icon name="heart" size={11} fill="currentColor" />{e.hearts}표</span></span>
                  </span>
                  <VoteButton entry={e} votedEntryId={votedEntryId} onVote={onVote} size="sm" />
                </div>
              ))}
            </div>
          </section>
        )}

        {entries && (
          <p className="note" style={{ margin: '4px 0 20px', padding: '0 16px' }}>1인 1표 · 자기 작품에는 투표할 수 없어요</p>
        )}
      </div>
    </Screen>
  );
}
