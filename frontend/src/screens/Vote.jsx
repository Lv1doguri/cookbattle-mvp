import { useEffect, useState } from 'react';
import { Screen, Header, TopBar } from '../components/Screen';
import Icon, { EggArt } from '../components/Icon';
import { useApp } from '../state/AppContext';

export default function Vote() {
  const { submission, votedEntryId, vote, fetchBattle, fetchEntries } = useApp();
  const [topic, setTopic] = useState('');
  const [entries, setEntries] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const battle = await fetchBattle();
      if (!alive) return;
      setTopic(battle.topic);
      const items = await fetchEntries(battle.id);
      if (alive) setEntries(items);
    })().catch(() => { if (alive) setEntries([]); });
    return () => { alive = false; };
  }, [fetchBattle, fetchEntries, submission]);

  const onVote = async (id) => {
    setEntries((es) => es.map((e) => (e.id === id ? { ...e, hearts: e.hearts + 1 } : e)));
    await vote(id);
  };

  return (
    <Screen>
      <Header className="vote-hdr">
        <TopBar title="투표" back>
          <span className="vote-rule">1인 1표</span>
        </TopBar>
        <div className="vote-intro">
          <div className="vote-intro__title">{topic} 대결</div>
          <div className="vote-intro__sub">
            {entries ? `출품작 ${entries.length}개 · ` : ''}
            {votedEntryId ? '투표를 마쳤어요' : '마음에 드는 한 접시를 골라주세요'}
          </div>
        </div>
      </Header>

      <div className="body">
        <div className="vote-grid">
          {entries === null && <p className="muted" style={{ padding: '16px' }}>불러오는 중…</p>}
          {entries?.map((e) => (
            <div key={e.id} className={`card vcard ${e.mine ? 'vcard--mine' : ''}`}>
              <div className="vcard__img" style={{ background: 'linear-gradient(135deg, #EAD9BE, #D9BE8E)' }}>
                {e.photoUrl ? <img src={e.photoUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <EggArt size={54} />}
                {e.mine && <span className="vcard__mine">내 작품</span>}
              </div>
              <div className="vcard__name">{e.name}</div>
              <div className="vcard__by">
                by {e.author} · <span className="hrt"><Icon name="heart" size={12} fill="currentColor" />{e.hearts}</span>
              </div>
              {e.mine ? (
                <button type="button" className="vb off" disabled>투표 불가</button>
              ) : e.voted ? (
                <button type="button" className="vb done" disabled><Icon name="check" size={14} strokeWidth={3} />투표 완료</button>
              ) : (
                <button type="button" className={`vb ${votedEntryId ? 'off' : ''}`} disabled={!!votedEntryId} onClick={() => onVote(e.id)}>
                  투표하기
                </button>
              )}
            </div>
          ))}
        </div>
        <p className="note" style={{ margin: '16px 0 20px' }}>1인 1표 · 자기 작품에는 투표할 수 없어요</p>
      </div>
    </Screen>
  );
}
