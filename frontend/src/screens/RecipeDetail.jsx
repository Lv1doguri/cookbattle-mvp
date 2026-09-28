import { useEffect, useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { Screen, IconButton } from '../components/Screen';
import Icon from '../components/Icon';
import { adaptRecipeDetail, toneFor } from '../api/adapt';
import { skillLabel, won } from '../data/mock';
import { useApp } from '../state/AppContext';

const DIFF_OPTIONS = [
  { id: 'easy', label: '쉬움 (원팬)' },
  { id: 'normal', label: '보통' },
  { id: 'hard', label: '귀찮음' },
];
const DIFF_LABEL = Object.fromEntries(DIFF_OPTIONS.map((o) => [o.id, o.label]));

export default function RecipeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toggleSaved, fetchRecipe, fetchComments, addComment } = useApp();
  const [text, setText] = useState('');
  const [recipe, setRecipe] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [list, setList] = useState([]);
  const [checked, setChecked] = useState({});
  const [reviewText, setReviewText] = useState('');
  const [reviewPhoto, setReviewPhoto] = useState(null); // { file, preview }
  const [reviewRating, setReviewRating] = useState(0);
  const [reviewDiff, setReviewDiff] = useState(null);
  const [reviewBusy, setReviewBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchRecipe(id)
      .then((r) => { if (alive) setRecipe(adaptRecipeDetail(r)); })
      .catch(() => { if (alive) setNotFound(true); });
    fetchComments(id).then((c) => { if (alive) setList(c); }).catch(() => {});
    return () => { alive = false; };
  }, [id, fetchRecipe, fetchComments]);

  if (notFound) return <Navigate to="/recipes" replace />;
  if (!recipe) return null;

  const saved = recipe.saved;
  const [a, b] = recipe.tone ?? toneFor(recipe.id);

  const submit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    const t = text.trim();
    setText('');
    try {
      await addComment(id, t);
      setList((c) => [...c, { author: '나', text: t }]);
    } catch {
      setText(t);
    }
  };

  const onPickReviewPhoto = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setReviewPhoto({ file, preview: URL.createObjectURL(file) });
  };

  const submitReview = async (e) => {
    e.preventDefault();
    if (!reviewText.trim() || reviewBusy) return;
    setReviewBusy(true);
    try {
      await addComment(id, reviewText.trim(), {
        photoFile: reviewPhoto?.file,
        rating: reviewRating || undefined,
        difficultyTag: reviewDiff || undefined,
      });
      setList((c) => [
        ...c,
        {
          author: '나', text: reviewText.trim(), rating: reviewRating || null,
          difficultyLabel: DIFF_LABEL[reviewDiff] ?? null, photoUrl: reviewPhoto?.preview ?? null,
        },
      ]);
      setReviewText(''); setReviewPhoto(null); setReviewRating(0); setReviewDiff(null);
    } finally {
      setReviewBusy(false);
    }
  };

  return (
    <Screen tone="plain">
      <div className="body detail-body">
        <div
          className="detail-photo"
          style={recipe.photoUrl ? { backgroundImage: `url(${recipe.photoUrl})`, backgroundSize: 'cover', backgroundPosition: 'center' }
            : { background: `linear-gradient(135deg, ${a} 0%, ${b} 60%, #C99A80 100%)` }}
        >
          {!recipe.photoUrl && <Icon name="bowl" size={96} strokeWidth={1.4} style={{ opacity: 0.9 }} />}
          {!recipe.photoUrl && <span className="detail-photo__cap">[요리 사진]</span>}
          <div className="detail-photo__bar">
            <IconButton label="뒤로" variant="photo" onClick={() => navigate(-1)}><Icon name="back" strokeWidth={2.2} /></IconButton>
            <IconButton
              label={saved ? '저장 취소' : '저장'} variant="photo"
              onClick={() => { toggleSaved(recipe.id, saved); setRecipe((r) => ({ ...r, saved: !r.saved })); }}
            >
              <Icon name="bookmark" size={20} strokeWidth={2.2} fill={saved ? 'currentColor' : 'none'} />
            </IconButton>
          </div>
        </div>

        <article className="detail-sheet">
          <span className="detail-by"><span className="detail-by__av">{recipe.author?.[0] ?? '요'}</span>{recipe.author} · {recipe.award}</span>
          <h1 className="detail-title">{recipe.name}</h1>
          <div className="detail-stats">
            <div className="stat stat--green"><span>예상 재료비</span><b>약 {won(recipe.cost)}원</b></div>
            <div className="stat stat--green"><span>조리 시간</span><b>{recipe.minutes}분</b></div>
            <div className="stat"><span>난이도</span><b>{skillLabel(recipe.skill)}</b></div>
          </div>

          {(recipe.valueScore || recipe.caloriesKcal || recipe.failSafetyLabel) && (
            <div className="detail-stats" style={{ marginTop: 8 }}>
              <div className="stat">
                <span>가성비 지수</span>
                <b>{recipe.valueScore ? `★ ${recipe.valueScore.toFixed(1)}` : '-'}</b>
              </div>
              <div className="stat">
                <span>칼로리 &amp; 양</span>
                <b>{recipe.caloriesKcal ? `${recipe.caloriesKcal}kcal` : '-'}</b>
              </div>
              <div className="stat"><span>실패 난이도</span><b>{recipe.failSafetyLabel ?? '-'}</b></div>
            </div>
          )}
          {recipe.portionLabel && <p className="muted" style={{ fontSize: 12, margin: '6px 2px 0' }}>{recipe.portionLabel}</p>}

          <section style={{ marginTop: 18 }}>
            <h2 className="sec sec--tight">자취생 장바구니 체크</h2>
            {recipe.ingredients.map(([n, q]) => {
              const on = !!checked[n];
              return (
                <label key={n} className="ing-check">
                  <input
                    type="checkbox" checked={on}
                    onChange={() => setChecked((c) => ({ ...c, [n]: !c[n] }))}
                  />
                  <span className={`ing-check__name${on ? ' done' : ''}`}>{n}</span>
                  <span className="ing-check__amt">{q}</span>
                </label>
              );
            })}
          </section>

          <section style={{ marginTop: 10 }}>
            <h2 className="sec sec--tight">조리 과정</h2>
            <ol className="steps">
              {recipe.steps.map((s, i) => (
                <li key={i} className="step2">
                  <span className="num">{i + 1}</span>
                  <span className="step2__body">
                    <span className="step2__head">
                      {s.minutes ? <span className="step2__time">{s.minutes}분</span> : null}
                    </span>
                    <span className="step2__text">{s.text}</span>
                  </span>
                </li>
              ))}
            </ol>
          </section>

          {recipe.chefTip && (
            <div className="tip-box">
              <Icon name="info" size={16} strokeWidth={2.4} style={{ flexShrink: 0, marginTop: 2 }} />
              <span><b>자취 마스터의 꿀팁</b><br />{recipe.chefTip}</span>
            </div>
          )}

          <section style={{ marginTop: 16 }}>
            <h2 className="sec sec--tight">인증샷 등록 &amp; 후기 작성</h2>
            <form onSubmit={submitReview} className="review-form">
              <label className="review-photo-tile">
                {reviewPhoto ? (
                  <img src={reviewPhoto.preview} alt="" className="review-photo-tile__img" />
                ) : (
                  <>
                    <Icon name="camera" size={26} strokeWidth={1.8} />
                    <span>사진 등록 (선택)</span>
                  </>
                )}
                <input type="file" accept="image/*" capture="environment" onChange={onPickReviewPhoto} hidden />
              </label>

              <p className="review-q">이 요리, 솔직히 어떠셨나요?</p>
              <div className="stars" role="radiogroup" aria-label="별점">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n} type="button" className="stars__btn" aria-label={`${n}점`}
                    onClick={() => setReviewRating(n)}
                  >
                    {n <= reviewRating ? '★' : '☆'}
                  </button>
                ))}
              </div>

              <div className="diff-chips">
                {DIFF_OPTIONS.map((o) => (
                  <button
                    key={o.id} type="button"
                    className={`chip ${reviewDiff === o.id ? 'on' : ''}`}
                    onClick={() => setReviewDiff((d) => (d === o.id ? null : o.id))}
                  >
                    {o.label}
                  </button>
                ))}
              </div>

              <textarea
                className="review-textarea" maxLength={500} placeholder="생생한 후기와 나만의 응용 비법을 남겨보세요"
                value={reviewText} onChange={(e) => setReviewText(e.target.value)}
              />
              <div className="review-form__foot">
                <span className="muted" style={{ fontSize: 12 }}>{reviewText.length}/500자</span>
                <Icon name="gift" size={14} strokeWidth={2} style={{ marginLeft: 'auto', marginRight: 4 }} />
                <span className="muted" style={{ fontSize: 12 }}>후기 등록 시 +1P (하루 최대 3P)</span>
              </div>
              <button type="submit" className="btn btn--primary" disabled={!reviewText.trim() || reviewBusy} style={{ marginTop: 10 }}>
                {reviewBusy ? '등록 중…' : '인증샷 등록하고 후기 남기기'}
              </button>
            </form>
          </section>

          <section style={{ marginTop: 14 }}>
            <h2 className="sec sec--tight">댓글 {list.length}</h2>
            {list.length === 0 ? (
              <p className="muted" style={{ fontSize: 13, margin: '4px 0 0' }}>첫 댓글을 남겨 보세요.</p>
            ) : (
              list.map((c, i) => (
                <div key={i} className="comment comment2">
                  {c.photoUrl && <img src={c.photoUrl} alt="" className="comment2__photo" />}
                  <div className="comment2__body">
                    <div className="comment2__head">
                      <b>{c.author}</b>
                      {c.rating ? <span className="comment2__stars">{'★'.repeat(c.rating)}{'☆'.repeat(5 - c.rating)}</span> : null}
                      {c.difficultyLabel && <span className="badge badge--neutral">{c.difficultyLabel}</span>}
                    </div>
                    <span>{c.text}</span>
                  </div>
                </div>
              ))
            )}
          </section>
        </article>
      </div>

      <form className="comment-bar" onSubmit={submit}>
        <input aria-label="댓글" placeholder="댓글을 입력하세요" value={text} onChange={(e) => setText(e.target.value)} />
        <button type="submit" disabled={!text.trim()}>등록</button>
      </form>
    </Screen>
  );
}
