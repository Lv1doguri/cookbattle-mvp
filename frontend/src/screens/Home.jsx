import { Link } from 'react-router-dom';
import { Screen, Header, TopBar, IconButton } from '../components/Screen';
import TabBar from '../components/TabBar';
import Icon from '../components/Icon';
import { Avatar, Badge, Button, ProgressBar } from '../components/ui';
import { BATTLE_HISTORY, skillLabel, won } from '../data/mock';
import { useApp } from '../state/AppContext';

export default function Home() {
  const { user, submission } = useApp();

  return (
    <Screen>
      <Header className="home-hdr">
        <TopBar title="요리왕" brand>
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
          <div className="home-stats">
            <div className="card home-stat">
              <span className="ico" style={{ background: '#EFE6D8', color: '#8A6A42' }}><Icon name="tabRecipe" size={22} /></span>
              <div className="home-stat__label">이번 달 요리</div>
              <div className="home-stat__value">{user.monthlyCooks}회</div>
            </div>
            <div className="card home-stat">
              <span className="ico" style={{ background: '#ECECEA', color: '#A85814' }}><Icon name="wallet" size={22} /></span>
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
            {BATTLE_HISTORY.map((h) => (
              <div key={h.id} className="history__row">
                <span className="ico ico--round" style={{ background: h.tint, color: h.ink }}><Icon name={h.icon} size={20} /></span>
                <div className="history__text">
                  <div className="history__title">{h.title}</div>
                  <div className="history__meta">{h.meta}</div>
                </div>
                <Badge tone={h.medal ? 'gold' : 'neutral'} className="badge--lg">{h.result}</Badge>
              </div>
            ))}
          </section>

          <Button to="/profile/edit" variant="secondary"><Icon name="edit" size={18} />정보 수정</Button>
        </div>
      </div>

      <TabBar />
    </Screen>
  );
}
