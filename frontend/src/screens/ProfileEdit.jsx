import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Screen, Header, TopBar, BottomAction } from '../components/Screen';
import Icon from '../components/Icon';
import { Button, Field, Segmented } from '../components/ui';
import { SKILLS } from '../data/mock';
import { useApp } from '../state/AppContext';

export default function ProfileEdit() {
  const { user, updateProfile, checkNickname } = useApp();
  const navigate = useNavigate();
  const fileRef = useRef(null);
  const checkSeq = useRef(0);
  const [nickname, setNickname] = useState(user?.nickname ?? '');
  const [password, setPassword] = useState('');
  const [skill, setSkill] = useState(user?.skill);
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState(user?.avatar ?? null);
  const [nickTaken, setNickTaken] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [saveError, setSaveError] = useState('');

  useEffect(() => {
    const seq = ++checkSeq.current;
    if (!user || nickname.trim() === user.nickname || nickname.trim().length < 2) return setNickTaken(false);
    const t = setTimeout(async () => {
      try {
        const taken = await checkNickname(nickname);
        if (seq === checkSeq.current) setNickTaken(taken);
      } catch {
        /* re-validated on save */
      }
    }, 300);
    return () => clearTimeout(t);
  }, [nickname, user, checkNickname]);

  if (!user) return null;

  const nickError = !nickname.trim() ? '닉네임을 입력해 주세요' : nickTaken ? '이미 등록된 아이디입니다' : '';
  const pwError = password && password.length < 8 ? '비밀번호는 8자 이상이에요' : '';

  const onPhoto = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarFile(file);
    const reader = new FileReader();
    reader.onload = () => setAvatarPreview(reader.result);
    reader.readAsDataURL(file);
  };

  const onSave = async (e) => {
    e.preventDefault();
    setSaveError('');
    if (nickError || pwError) return;
    setSubmitting(true);
    try {
      await updateProfile({
        nickname: nickname.trim() !== user.nickname ? nickname.trim() : undefined,
        skill: skill !== user.skill ? skill : undefined,
        password: password || undefined,
        avatarFile,
      });
      navigate('/home');
    } catch (err) {
      if (err.code === 'nickname_taken') setNickTaken(true);
      else setSaveError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <form className="scr-form" onSubmit={onSave} noValidate>
        <Header className="pe-hdr">
          <TopBar title="정보 수정" back="/home" />
          <div className="pe-avatar">
            <div className="pe-avatar__wrap">
              <span className="pe-avatar__img">
                {avatarPreview ? <img src={avatarPreview} alt="" /> : nickname[0] ?? '?'}
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
            <Field id="pe-email" label="이메일" value={user.email || '(등록 안 함)'} disabled />
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
          {saveError && <p className="field-msg" style={{ color: 'var(--danger, #d64545)' }}>{saveError}</p>}
          <Button type="submit" disabled={!!nickError || !!pwError || submitting}>{submitting ? '저장 중…' : '저장'}</Button>
        </BottomAction>
      </form>
    </Screen>
  );
}
