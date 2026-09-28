import { useEffect, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Screen, Header, TopBar, BottomAction } from '../components/Screen';
import Icon, { EggArt } from '../components/Icon';
import { Button, Field } from '../components/ui';
import { skillLabel } from '../data/mock';
import { useApp } from '../state/AppContext';

export default function CookVerify() {
  const { user, draftPhotos, submission, submitEntry, fetchBattle } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const { kind, tier } = location.state || {};
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [touched, setTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState('');
  const [topic, setTopic] = useState('');

  useEffect(() => {
    fetchBattle(tier, kind).then((b) => setTopic(b.topic)).catch(() => {});
  }, [fetchBattle, tier, kind]);

  // One entry per battle
  if (submission) return <Navigate to="/battle/done" replace />;

  const nameError = touched && !name.trim() ? '요리명을 입력해 주세요' : '';

  const onSubmit = async (e) => {
    e.preventDefault();
    setTouched(true);
    setServerError('');
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      await submitEntry({ name: name.trim(), description: desc.trim(), tier, kind });
      navigate('/battle/done', { replace: true });
    } catch (err) {
      setServerError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <form className="scr-form" onSubmit={onSubmit} noValidate>
        <Header className="verify-hdr">
          <TopBar title="요리 인증" back="/battle" />
          <div className="verify-context">
            <EggArt size={18} yolk="#FFD54F" outline="var(--brand-ink)" />
            {topic} 대결 · {kind === 'theme' ? '테마 대결' : `${skillLabel(tier || user.skill)} 그룹`}
          </div>
        </Header>

        <div className="body">
          <div className="stack verify-fields">
            <div className="verify-photo">
              {draftPhotos.length > 0 ? (
                <div className="verify-photo-grid">
                  {draftPhotos.map((p, i) => <img key={i} src={p} alt={`인증샷 ${i + 1}`} />)}
                </div>
              ) : (
                <div className="verify-photo__ph"><Icon name="bowl" size={60} strokeWidth={1.4} /></div>
              )}
              {draftPhotos.length > 0 && (
                <span className="verify-photo__ok"><Icon name="check" size={13} strokeWidth={2.4} />인증샷 {draftPhotos.length}장 촬영 완료</span>
              )}
              <Link to="/battle/camera" state={{ kind, tier }} className="verify-photo__retake"><Icon name="camera" size={14} strokeWidth={2.2} />다시 촬영</Link>
            </div>

            <Field
              id="cv-name" label="요리명" maxLength={30} placeholder="예) 치즈 스크램블 에그"
              value={name} onChange={(e) => setName(e.target.value)} error={nameError}
            />
            <Field
              id="cv-desc" label="설명" multiline maxLength={200}
              placeholder="어떻게 만들었는지 짧게 적어 주세요"
              value={desc} onChange={(e) => setDesc(e.target.value)}
              hint="한 대결에는 한 번만 참가할 수 있어요"
            />
          </div>
        </div>

        <BottomAction>
          {serverError && <p className="field-msg" style={{ color: 'var(--danger, #d64545)' }}>{serverError}</p>}
          <Button type="submit" disabled={submitting}>{submitting ? '제출 중…' : '제출'}</Button>
        </BottomAction>
      </form>
    </Screen>
  );
}
