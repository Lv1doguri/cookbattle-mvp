import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Screen, Header, TopBar } from '../components/Screen';
import TabBar from '../components/TabBar';
import Icon from '../components/Icon';
import { Button, PointPill } from '../components/ui';
import { BATTLES, LAST_RESULT, SKILLS } from '../data/mock';
import { useApp } from '../state/AppContext';

export default function Battle() {
  const { user, submission } = useApp();
  const [group, setGroup] = useState(user.skill);
  const battle = BATTLES[group];
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
                {s.label}{s.id === user.skill && ' · 내 그룹'}
              </button>
            );
          })}
        </div>
      </Header>

      <div className="body">
        <div className="stack pad">
          <section className="hero battle-hero" role="tabpanel" aria-label={`${groupLabel} 대결`}>
            <svg className="battle-hero__art" width="84" height="84" viewBox="0 0 24 24" aria-hidden="true">
              <ellipse cx="12" cy="13" rx="8" ry="6.5" fill="#fff" />
              <circle cx="12.5" cy="12.5" r="3.4" fill="#D9B85C" />
            </svg>
            <span className="battle-hero__tag">{groupLabel} 대결 · 오늘의 주제</span>
            <div className="battle-hero__topic">{battle.topic}</div>
            <div className="battle-hero__sub">{battle.subtitle}</div>
            <div className="battle-hero__stats">
              <div className="battle-hero__stat">
                <div className="battle-hero__stat-label"><Icon name="clock" size={13} strokeWidth={2.4} />남은 기간</div>
                <div className="battle-hero__stat-value">{battle.daysLeft}일</div>
              </div>
              <div className="battle-hero__stat">
                <div className="battle-hero__stat-label"><Icon name="users" size={13} strokeWidth={2.4} />참가자</div>
                <div className="battle-hero__stat-value">{battle.participants + (mine && submission ? 1 : 0)}명</div>
              </div>
            </div>
          </section>

          {!mine ? (
            <p className="battle-note"><Icon name="lock" size={14} strokeWidth={2.4} />내 실력 그룹 대결에만 참가할 수 있어요</p>
          ) : submission ? (
            <Button to="/battle/done" variant="secondary"><Icon name="check" size={18} strokeWidth={2.6} />참가 완료 · 내 출품작 보기</Button>
          ) : (
            <Button to="/battle/camera">참가하기<span className="btn__tag">+1P</span></Button>
          )}
          <Button to="/battle/vote" variant="secondary">출품작 보고 투표하기</Button>

          <Link to="/battle/result" className="card last-result">
            <span className="last-result__ico"><Icon name="trophy" size={22} /></span>
            <span className="last-result__text">
              <span className="last-result__title">지난 대결 결과</span>
              <span className="last-result__sub">{LAST_RESULT.title} · 내 순위 {LAST_RESULT.myRank}등</span>
            </span>
            <Icon name="chevronRight" size={18} strokeWidth={2.4} color="#898989" />
          </Link>
        </div>
      </div>

      <TabBar />
    </Screen>
  );
}
