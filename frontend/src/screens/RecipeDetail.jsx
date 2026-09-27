import { useEffect, useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { Screen, IconButton } from '../components/Screen';
import Icon from '../components/Icon';
import { adaptRecipeDetail, toneFor } from '../api/adapt';
import { skillLabel, won } from '../data/mock';
import { useApp } from '../state/AppContext';

export default function RecipeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toggleSaved, fetchRecipe, fetchComments, addComment } = useApp();
  const [text, setText] = useState('');
  const [recipe, setRecipe] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [list, setList] = useState([]);

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
            <div className="stat"><span>예상 재료비</span><b>약 {won(recipe.cost)}원</b></div>
            <div className="stat"><span>조리 시간</span><b>{recipe.minutes}분</b></div>
            <div className="stat"><span>난이도</span><b>{skillLabel(recipe.skill)}</b></div>
          </div>

          <section style={{ marginTop: 18 }}>
            <h2 className="sec sec--tight">재료</h2>
            {recipe.ingredients.map(([n, q]) => (
              <div key={n} className="ing"><span>{n}</span><span>{q}</span></div>
            ))}
          </section>

          <section style={{ marginTop: 10 }}>
            <h2 className="sec sec--tight">조리 과정</h2>
            <ol className="steps">
              {recipe.steps.map((s, i) => (
                <li key={i} className="step"><span className="num">{i + 1}</span>{s}</li>
              ))}
            </ol>
          </section>

          <section style={{ marginTop: 14 }}>
            <h2 className="sec sec--tight">댓글 {list.length}</h2>
            {list.length === 0 ? (
              <p className="muted" style={{ fontSize: 13, margin: '4px 0 0' }}>첫 댓글을 남겨 보세요.</p>
            ) : (
              list.map((c, i) => (
                <div key={i} className="comment"><b>{c.author}</b>{c.text}</div>
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
