import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Screen, TopBar, BottomAction } from '../components/Screen';
import Icon, { CrownArt, EggArt } from '../components/Icon';
import { Button, Coin, PointPill } from '../components/ui';
import { useApp } from '../state/AppContext';

const PODIUM = {
  1: { h: 100, av: 54, bar: 'var(--brand-grad-v)', ink: '#fff', avBg: 'linear-gradient(135deg, #DCC181, #C1A052)', avInk: '#6B5320' },
  2: { h: 70, av: 44, bar: 'linear-gradient(180deg, #FFFFFF, var(--surface-3))', ink: 'var(--ink-3)' },
  3: { h: 52, av: 40, bar: 'linear-gradient(180deg, #FFFFFF, var(--surface-3))', ink: 'var(--ink-3)', avBg: 'linear-gradient(135deg, #F7B89E, #D9684A)' },
};

const CATEGORIES = [
  ['rice', '밥'], ['noodle', '면'], ['pasta', '파스타'], ['meat', '고기'],
  ['soup', '국·찌개'], ['side', '반찬'], ['healthy', '건강식'], ['dessert', '디저트'],
];
const DIFFICULTIES = [['beginner', '초급'], ['intermediate', '중급'], ['advanced', '상급']];
const TOOLS = [
  ['microwave', '전자레인지만'], ['pan', '프라이팬 하나'], ['airfryer', '에어프라이어'], ['rice_cooker', '밥솥'],
];

// 1위가 결과 화면에서 자기 비법 레시피를 레시피 탭에 공유하는 폼 (백엔드엔 이미 있던 기능인데
// 프론트에 폼이 없어서 못 쓰고 있었어요 — 2026-09-28에 새로 만듦).
function ShareRecipeSheet({ entryId, dishName, onClose, onShared }) {
  const { shareRecipe } = useApp();
  const [category, setCategory] = useState('rice');
  const [price, setPrice] = useState('');
  const [minutes, setMinutes] = useState('');
  const [difficulty, setDifficulty] = useState('beginner');
  const [tools, setTools] = useState([]);
  const [ingredients, setIngredients] = useState([{ name: '', amount: '' }]);
  const [steps, setSteps] = useState(['']);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const toggleTool = (t) => setTools((ts) => (ts.includes(t) ? ts.filter((x) => x !== t) : [...ts, t]));
  const setIngredient = (i, key, value) => setIngredients((rows) => rows.map((r, idx) => (idx === i ? { ...r, [key]: value } : r)));
  const setStep = (i, value) => setSteps((rows) => rows.map((r, idx) => (idx === i ? value : r)));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const cleanIngredients = ingredients.map((r) => ({ name: r.name.trim(), amount: r.amount.trim() || undefined })).filter((r) => r.name);
    const cleanSteps = steps.map((s) => s.trim()).filter(Boolean).map((text) => ({ text }));
    if (!price || !minutes || cleanIngredients.length === 0 || cleanSteps.length === 0) {
      setError('재료비·시간·재료·조리 순서를 모두 입력해 주세요');
      return;
    }
    setSubmitting(true);
    try {
      await shareRecipe(entryId, {
        category, price: Number(price), minutes: Number(minutes), difficulty, tools,
        ingredients: cleanIngredients, steps: cleanSteps,
      });
      onShared();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <form className="sheet sheet--form" onSubmit={onSubmit} role="dialog" aria-modal="true" aria-label="비법 레시피 공유">
        <span className="sheet__grip" />
        <h2 className="sheet__title" style={{ marginTop: 14 }}>비법 레시피 공유하기</h2>
        <p className="sheet__sub">'{dishName}'을 레시피 탭에 올려요</p>

        <div className="share-form">
          <label className="share-form__row">
            <span>카테고리</span>
            <select value={category} onChange={(e) => setCategory(e.target.value)} className="field field--soft">
              {CATEGORIES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
            </select>
          </label>
          <div className="share-form__grid2">
            <label className="share-form__row">
              <span>재료비(원)</span>
              <input type="number" min="0" inputMode="numeric" className="field field--soft" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="3500" />
            </label>
            <label className="share-form__row">
              <span>조리 시간(분)</span>
              <input type="number" min="1" inputMode="numeric" className="field field--soft" value={minutes} onChange={(e) => setMinutes(e.target.value)} placeholder="15" />
            </label>
          </div>
          <label className="share-form__row">
            <span>난이도</span>
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="field field--soft">
              {DIFFICULTIES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
            </select>
          </label>

          <div className="share-form__row">
            <span>필요한 도구 (선택)</span>
            <div className="share-form__chips">
              {TOOLS.map(([id, label]) => (
                <button key={id} type="button" className={`chip ${tools.includes(id) ? 'on' : ''}`} onClick={() => toggleTool(id)}>{label}</button>
              ))}
            </div>
          </div>

          <div className="share-form__row">
            <span>재료</span>
            {ingredients.map((row, i) => (
              <div key={i} className="share-form__grid2" style={{ marginTop: i ? 6 : 0 }}>
                <input className="field field--soft" placeholder="재료명" value={row.name} onChange={(e) => setIngredient(i, 'name', e.target.value)} />
                <input className="field field--soft" placeholder="양 (선택)" value={row.amount} onChange={(e) => setIngredient(i, 'amount', e.target.value)} />
              </div>
            ))}
            <button type="button" className="share-form__add" onClick={() => setIngredients((r) => [...r, { name: '', amount: '' }])}>
              <Icon name="check" size={13} strokeWidth={3} />재료 추가
            </button>
          </div>

          <div className="share-form__row">
            <span>조리 순서</span>
            {steps.map((s, i) => (
              <div key={i} className="share-form__step">
                <span className="num">{i + 1}</span>
                <input className="field field--soft" placeholder={`${i + 1}단계`} value={s} onChange={(e) => setStep(i, e.target.value)} />
              </div>
            ))}
            <button type="button" className="share-form__add" onClick={() => setSteps((r) => [...r, ''])}>
              <Icon name="check" size={13} strokeWidth={3} />단계 추가
            </button>
          </div>
        </div>

        {error && <p className="field-msg field-msg--error" style={{ alignSelf: 'flex-start' }}><Icon name="alert" size={16} strokeWidth={2.2} />{error}</p>}
        <div className="sheet__actions" style={{ width: '100%' }}>
          <Button type="button" variant="muted" onClick={onClose}>취소</Button>
          <Button type="submit" disabled={submitting}>{submitting ? '공유 중…' : '공유하기'}</Button>
        </div>
      </form>
    </>
  );
}

export default function BattleResult() {
  const { user, fetchResult } = useApp();
  const [params] = useSearchParams();
  const battleId = params.get('battle');
  const [r, setR] = useState(null);
  const [error, setError] = useState('');
  const [sharing, setSharing] = useState(null); // { entryId, dishName } | null

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
  const winner = r.ranking.find((p) => p.rank === 1);
  const rest = r.ranking.filter((p) => p.rank > 3);

  return (
    <Screen>
      <div className="result-hdr2">
        <div className="result-hdr2__top">
          <TopBar title="대결 결과" back="/battle" />
          {user && <PointPill points={user.points} to="/shop" />}
        </div>
        <span className="result-hdr2__badge"><Icon name="trophy" size={12} strokeWidth={2.6} />명예의 전당</span>
        <p className="result-meta" style={{ color: '#fff', opacity: .95 }}>{r.title} · {r.group} · 참가자 {r.participants}명</p>
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

          {winner && (
            <div className="card wcard">
              <span className="wcard__badge"><Icon name="trophy" size={12} strokeWidth={2.8} />GRAND CHAMPION</span>
              <div className="wcard__img">
                {winner.photoUrl ? <img src={winner.photoUrl} alt="" /> : <EggArt size={54} />}
              </div>
              <div className="wcard__name">{winner.dishName}</div>
              <div className="wcard__by">by {nameOf(winner)} · <b>{winner.votes}표</b> · <span className="hrt">+{winner.rankPoints}P</span></div>
              {r.sharedRecipeId ? (
                <Link to={`/recipes/${r.sharedRecipeId}`} className="btn btn--secondary" style={{ marginTop: 12 }}>
                  <Icon name="tabRecipe" size={16} strokeWidth={2} style={{ marginRight: 6 }} />공유된 비법 레시피 보기
                </Link>
              ) : winner.canShareRecipe ? (
                <button type="button" className="btn btn--primary" style={{ marginTop: 12 }} onClick={() => setSharing({ entryId: winner.entryId, dishName: winner.dishName })}>
                  <Icon name="tabRecipe" size={16} strokeWidth={2} style={{ marginRight: 6 }} />비법 레시피 공유하기
                </button>
              ) : null}
            </div>
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
                <span className="lr__votes"><b>{p.votes}표</b><small>+{p.rankPoints}P</small></span>
              </div>
            ))}
            {rest.length === 0 && r.ranking.length < r.participants && (
              <p className="muted" style={{ fontSize: 12, margin: '8px 0 0' }}>나머지 참가자도 전부 참가 포인트를 받았어요</p>
            )}
          </section>
        </div>
      </div>

      <BottomAction className="bottom-action--tight">
        <Button to="/battle">확인</Button>
      </BottomAction>

      {sharing && (
        <ShareRecipeSheet
          entryId={sharing.entryId}
          dishName={sharing.dishName}
          onClose={() => setSharing(null)}
          onShared={() => { setSharing(null); fetchResult(battleId).then(setR); }}
        />
      )}
    </Screen>
  );
}
