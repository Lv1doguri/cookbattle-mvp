import { Screen, Header, TopBar } from '../components/Screen';
import Icon, { EggArt, EggBowlArt, EggRollArt } from '../components/Icon';
import { BATTLES, VOTE_ENTRIES } from '../data/mock';
import { useApp } from '../state/AppContext';

const ART = { egg: EggArt, eggBowl: EggBowlArt, eggRoll: EggRollArt };

export default function Vote() {
  const { user, submission, votedEntryId, vote } = useApp();
  const battle = BATTLES[user.skill];

  const entries = [...VOTE_ENTRIES];
  if (submission) {
    entries.splice(1, 0, {
      id: 'mine', name: submission.name, author: '나', hearts: 7, art: 'egg',
      bg: ['#EAD9BE', '#D9BE8E'], photo: submission.photo, mine: true,
    });
  }

  return (
    <Screen>
      <Header className="vote-hdr">
        <TopBar title="투표" back>
          <span className="vote-rule">1인 1표</span>
        </TopBar>
        <div className="vote-intro">
          <div className="vote-intro__title">{battle.topic} 대결</div>
          <div className="vote-intro__sub">
            출품작 {battle.participants + (submission ? 1 : 0)}개 ·{' '}
            {votedEntryId ? '투표를 마쳤어요' : '마음에 드는 한 접시를 골라주세요'}
          </div>
        </div>
      </Header>

      <div className="body">
        <div className="vote-grid">
          {entries.map((e) => {
            const Art = ART[e.art];
            const voted = votedEntryId === e.id;
            const hearts = e.hearts + (voted ? 1 : 0);
            return (
              <div key={e.id} className={`card vcard ${e.mine ? 'vcard--mine' : ''}`}>
                <div className="vcard__img" style={{ background: `linear-gradient(135deg, ${e.bg[0]}, ${e.bg[1]})` }}>
                  {e.photo ? <img src={e.photo} alt="" /> : <Art size={54} />}
                  {e.mine && <span className="vcard__mine">내 작품</span>}
                </div>
                <div className="vcard__name">{e.name}</div>
                <div className="vcard__by">
                  by {e.author} · <span className="hrt"><Icon name="heart" size={12} fill="currentColor" />{hearts}</span>
                </div>
                {e.mine ? (
                  <button type="button" className="vb off" disabled>투표 불가</button>
                ) : voted ? (
                  <button type="button" className="vb done" disabled><Icon name="check" size={14} strokeWidth={3} />투표 완료</button>
                ) : (
                  <button type="button" className={`vb ${votedEntryId ? 'off' : ''}`} disabled={!!votedEntryId} onClick={() => vote(e.id)}>
                    투표하기
                  </button>
                )}
              </div>
            );
          })}
        </div>
        <p className="note" style={{ margin: '16px 0 20px' }}>1인 1표 · 자기 작품에는 투표할 수 없어요</p>
      </div>
    </Screen>
  );
}
