import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { Screen } from '../components/Screen';
import Icon, { EggArt } from '../components/Icon';
import { Button, Coin } from '../components/ui';
import { useApp } from '../state/AppContext';

const CONFETTI = [
  { left: 12, top: 30, w: 10, h: 10, bg: '#D9B85C', r: 20 },
  { right: 16, top: 20, w: 8, h: 14, bg: '#F48E6E', r: -25 },
  { left: 30, bottom: 16, w: 12, h: 6, bg: '#9D9D9D', r: -15 },
  { right: 26, bottom: 26, w: 9, h: 9, bg: '#D9B85C', r: 0, round: true },
  { left: 78, top: 0, w: 6, h: 12, bg: '#9D9D9D', r: 35 },
];

function timeAgo(ts) {
  const m = Math.floor((Date.now() - ts) / 60000);
  return m < 1 ? '방금 전' : m < 60 ? `${m}분 전` : `${Math.floor(m / 60)}시간 전`;
}

export default function JoinDone() {
  const { submission, fetchBattle } = useApp();
  const [topic, setTopic] = useState('');

  useEffect(() => {
    fetchBattle().then((b) => setTopic(b.topic)).catch(() => {});
  }, [fetchBattle]);

  if (!submission) return <Navigate to="/battle" replace />;

  return (
    <Screen tone="soft">
      <div className="done-wrap">
        <div className="done-burst">
          {CONFETTI.map((c, i) => (
            <span
              key={i} className="dot"
              style={{
                left: c.left, right: c.right, top: c.top, bottom: c.bottom, width: c.w, height: c.h,
                background: c.bg, transform: `rotate(${c.r}deg)`, borderRadius: c.round ? 5 : 4,
              }}
            />
          ))}
          <span className="done-check"><Icon name="check" size={52} strokeWidth={2.6} /></span>
        </div>
        <h1 className="done-title">참가 완료!</h1>
        <span className="reward-pill"><Coin size={24} />+1P 적립</span>
        <p className="done-body">
          {topic} 대결에 출품했어요.<br />대결이 끝나면 결과를 알려드릴게요.
        </p>

        <div className="card entry-card">
          <span className="entry-card__thumb">
            {submission.photo ? <img src={submission.photo} alt="" /> : <EggArt size={30} />}
          </span>
          <span className="entry-card__text">
            <span className="entry-card__name">{submission.name}</span>
            <span className="entry-card__meta">by 나 · {timeAgo(submission.submittedAt)}</span>
          </span>
          <span className="badge">출품됨</span>
        </div>
      </div>

      <div className="done-actions">
        <Button to="/battle/vote">출품작 보고 투표하기</Button>
        <Link to="/battle" className="link-quiet">대결 홈으로</Link>
      </div>
    </Screen>
  );
}
