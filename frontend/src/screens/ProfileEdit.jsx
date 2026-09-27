import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Screen, Header, TopBar, BottomAction } from '../components/Screen';
import Icon from '../components/Icon';
import { Button, Field, Segmented } from '../components/ui';
import { SKILLS } from '../data/mock';
import { useApp } from '../state/AppContext';

export default function ProfileEdit() {
  const { user, updateProfile, isNicknameTaken } = useApp();
  const navigate = useNavigate();
  const fileRef = useRef(null);
  const [nickname, setNickname] = useState(user.nickname);
  const [password, setPassword] = useState('');
  const [skill, setSkill] = useState(user.skill);
  const [avatar, setAvatar] = useState(user.avatar ?? null);

  const nickError = !nickname.trim() ? '닉네임을 입력해 주세요' : isNicknameTaken(nickname) ? '이미 사용 중인 닉네임입니다' : '';
  const pwError = password && password.length < 8 ? '비밀번호는 8자 이상이에요' : '';

  const onPhoto = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setAvatar(reader.result);
    reader.readAsDataURL(file);
  };

  const onSave = (e) => {
    e.preventDefault();
    if (nickError || pwError) return;
    updateProfile({ nickname: nickname.trim(), skill, avatar });
    navigate('/home');
  };

  return (
    <Screen>
      <form className="scr-form" onSubmit={onSave} noValidate>
        <Header className="pe-hdr">
          <TopBar title="정보 수정" back="/home" />
          <div className="pe-avatar">
            <div className="pe-avatar__wrap">
              <span className="pe-avatar__img">
                {avatar ? <img src={avatar} alt="" /> : nickname[0] ?? '?'}
              </span>
              <button type="button" className="pe-avatar__btn" aria-label="사진 변경" onClick={() => fileRef.current?.click()}>
                <Icon name="camera" size={18} strokeWidth={2.2} />
              </button>
              <input ref={fileRef} type="file" accept="image/*" hidden onChange={onPhoto} />
            </div>
            <button type="button" className="pe-avatar__link" onClick={() => fileRef.current?.click()}>사진 변경</button>
          </div>
        </Header>

        <div className="body">
          <div className="stack pe-fields">
            <Field id="pe-nick" label="닉네임" maxLength={12} value={nickname} onChange={(e) => setNickname(e.target.value)} error={nickError} />
            <Field id="pe-email" label="이메일" value={user.email} disabled />
            <Field
              id="pe-pw" label="비밀번호" type="password" autoComplete="new-password" placeholder="바꿀 때만 입력하세요"
              value={password} onChange={(e) => setPassword(e.target.value)} error={pwError}
            />
            <div>
              <span className="lbl" id="pe-skill">요리 실력</span>
              <Segmented label="요리 실력" options={SKILLS} value={skill} onChange={setSkill} />
              <p className="field-msg"><Icon name="info" size={14} strokeWidth={2.2} />바꾼 실력은 다음 대결부터 적용돼요</p>
            </div>
          </div>
        </div>

        <BottomAction>
          <Button type="submit" disabled={!!nickError || !!pwError}>저장</Button>
        </BottomAction>
      </form>
    </Screen>
  );
}
