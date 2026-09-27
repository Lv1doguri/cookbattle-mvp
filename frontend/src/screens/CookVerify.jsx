import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Screen, Header, TopBar, BottomAction } from '../components/Screen';
import Icon, { EggArt } from '../components/Icon';
import { Button, Field } from '../components/ui';
import { BATTLES, skillLabel } from '../data/mock';
import { useApp } from '../state/AppContext';

export default function CookVerify() {
  const { user, draftPhoto, submission, submitEntry } = useApp();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [touched, setTouched] = useState(false);

  // One entry per battle
  if (submission) return <Navigate to="/battle/done" replace />;

  const nameError = touched && !name.trim() ? '요리명을 입력해 주세요' : '';

  const onSubmit = (e) => {
    e.preventDefault();
    setTouched(true);
    if (!name.trim()) return;
    submitEntry({ name: name.trim(), description: desc.trim() });
    navigate('/battle/done', { replace: true });
  };

  return (
    <Screen>
      <form className="scr-form" onSubmit={onSubmit} noValidate>
        <Header className="verify-hdr">
          <TopBar title="요리 인증" back="/battle" />
          <div className="verify-context">
            <EggArt size={18} yolk="#D9B85C" outline="#C2650F" />
            {BATTLES[user.skill].topic} 대결 · {skillLabel(user.skill)} 그룹
          </div>
        </Header>

        <div className="body">
          <div className="stack verify-fields">
            <div className="verify-photo">
              {draftPhoto ? (
                <img src={draftPhoto} alt="촬영한 요리 사진" />
              ) : (
                <div className="verify-photo__ph"><Icon name="bowl" size={60} strokeWidth={1.4} /></div>
              )}
              {draftPhoto && <span className="verify-photo__ok"><Icon name="check" size={13} strokeWidth={2.4} />촬영 완료</span>}
              <Link to="/battle/camera" className="verify-photo__retake"><Icon name="camera" size={14} strokeWidth={2.2} />다시 촬영</Link>
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
          <Button type="submit">제출</Button>
        </BottomAction>
      </form>
    </Screen>
  );
}
