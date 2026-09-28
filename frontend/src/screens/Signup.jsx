import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Screen, Header, TopBar, BottomAction } from '../components/Screen';
import { Button, Field } from '../components/ui';
import Icon from '../components/Icon';
import GoogleLoginButton from '../components/GoogleLoginButton';
import SocialLoginRow from '../components/SocialLoginRow';
import { SKILLS } from '../data/mock';
import { useApp } from '../state/AppContext';

// 아주 단순한 클라이언트 전용 강도 표시(서버로 보내지 않아요, 그냥 입력 도움용).
function pwStrength(pw) {
  if (pw.length < 8) return 0;
  let score = 1;
  if (/[0-9]/.test(pw) && /[a-zA-Z]/.test(pw)) score++;
  if (pw.length >= 12) score++;
  return Math.min(score, 3);
}

export default function Signup() {
  const { signup, loginWithGoogle, checkNickname, checkUsername } = useApp();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [pwConfirm, setPwConfirm] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [showPwConfirm, setShowPwConfirm] = useState(false);
  const [skill, setSkill] = useState('intermediate');
  const [touched, setTouched] = useState(false);
  const [usernameTaken, setUsernameTaken] = useState(false);
  const [nickTaken, setNickTaken] = useState(false);
  const [termsService, setTermsService] = useState(false);
  const [termsPrivacy, setTermsPrivacy] = useState(false);
  const [termsMarketing, setTermsMarketing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState('');
  const userCheckSeq = useRef(0);
  const nickCheckSeq = useRef(0);
  const termsAll = termsService && termsPrivacy && termsMarketing;

  const onGoogleCredential = async (idToken) => {
    setServerError('');
    try {
      await loginWithGoogle(idToken, skill);
      navigate('/onboarding', { replace: true });
    } catch (err) {
      setServerError(err.message);
    }
  };

  useEffect(() => {
    const seq = ++userCheckSeq.current;
    if (username.trim().length < 4) return setUsernameTaken(false);
    const t = setTimeout(async () => {
      try {
        const taken = await checkUsername(username);
        if (seq === userCheckSeq.current) setUsernameTaken(taken);
      } catch {
        /* validated again on submit */
      }
    }, 300);
    return () => clearTimeout(t);
  }, [username, checkUsername]);

  useEffect(() => {
    const seq = ++nickCheckSeq.current;
    if (nickname.trim().length < 2) return setNickTaken(false);
    const t = setTimeout(async () => {
      try {
        const taken = await checkNickname(nickname);
        if (seq === nickCheckSeq.current) setNickTaken(taken);
      } catch {
        /* validated again on submit */
      }
    }, 300);
    return () => clearTimeout(t);
  }, [nickname, checkNickname]);

  const userError =
    touched && username.trim().length < 4 ? '아이디는 4자 이상이에요'
      : usernameTaken ? '이미 등록된 아이디입니다'
        : '';
  const nickError =
    touched && nickname.trim().length === 0 ? '닉네임을 입력해 주세요'
      : nickTaken ? '이미 사용 중인 닉네임입니다'
        : '';
  const pwError = touched && password.length < 8 ? '비밀번호는 8자 이상이에요' : '';
  const pwConfirmError = touched && pwConfirm !== password ? '비밀번호가 일치하지 않아요' : '';
  const strength = pwStrength(password);
  const termsError = touched && !(termsService && termsPrivacy) ? '필수 약관에 동의해 주세요' : '';

  const onSubmit = async (e) => {
    e.preventDefault();
    setTouched(true);
    setServerError('');
    if (
      username.trim().length < 4 || usernameTaken || !nickname.trim() || nickTaken || password.length < 8
      || pwConfirm !== password || !termsService || !termsPrivacy
    ) return;
    setSubmitting(true);
    try {
      await signup({ username: username.trim(), nickname: nickname.trim(), skill, password });
      navigate('/onboarding', { replace: true });
    } catch (err) {
      if (err.code === 'username_taken') setUsernameTaken(true);
      else if (err.code === 'nickname_taken') setNickTaken(true);
      else setServerError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <form className="scr-form" onSubmit={onSubmit} noValidate>
        <Header>
          <TopBar title="회원가입" back="/" />
          <p className="signup-hello">반가워요!<br />요리왕에서 쓸 이름을 알려주세요</p>
          <span className="signup-hello__chip"><Icon name="gift" size={14} strokeWidth={2} />가입 즉시 웰컴 포인트 지급</span>
        </Header>

        <div className="body">
          <div className="stack signup-fields">
            <GoogleLoginButton onCredential={onGoogleCredential} />
            <SocialLoginRow />
            <div className="divider">
              <span className="divider__line" />
              <span className="divider__text" style={{ whiteSpace: 'nowrap' }}>또는 직접 입력할게요</span>
              <span className="divider__line" />
            </div>
            <Field
              id="su-user" label="아이디 또는 이메일" autoComplete="username" maxLength={40} icon="mail"
              placeholder="영문/숫자 아이디 또는 이메일"
              value={username} onChange={(e) => setUsername(e.target.value)} error={userError}
            />
            <Field
              id="su-nick" label="닉네임" autoComplete="nickname" maxLength={12} icon="chefHat"
              value={nickname} onChange={(e) => setNickname(e.target.value)} error={nickError}
            />
            <Field
              id="su-pw" label="비밀번호" type={showPw ? 'text' : 'password'} autoComplete="new-password" icon="lock"
              value={password} onChange={(e) => setPassword(e.target.value)} error={pwError}
              rightSlot={(
                <button type="button" className="field-eye" aria-label={showPw ? '비밀번호 숨기기' : '비밀번호 보기'} onClick={() => setShowPw((v) => !v)}>
                  <Icon name={showPw ? 'eyeOff' : 'eye'} size={18} strokeWidth={2} />
                </button>
              )}
            />
            {password && (
              <div className={`pw-strength${strength >= 3 ? ' pw-strength--safe' : ''}`}>
                <div className="pw-strength__bars">
                  {[0, 1, 2].map((i) => <span key={i} className={i < strength ? 'on' : ''} />)}
                </div>
                <span className="pw-strength__label">
                  {strength >= 3 && <Icon name="check" size={13} strokeWidth={3} />}
                  {['너무 짧아요', '약해요', '적당해요', '보안 안전 (안심할 수 있어요)'][strength]}
                </span>
              </div>
            )}
            <Field
              id="su-pw2" label="비밀번호 확인" type={showPwConfirm ? 'text' : 'password'} autoComplete="new-password" icon="lock"
              value={pwConfirm} onChange={(e) => setPwConfirm(e.target.value)} error={pwConfirmError}
              hint={!pwConfirmError && pwConfirm && pwConfirm === password ? '비밀번호가 일치해요' : undefined}
              rightSlot={(
                <button type="button" className="field-eye" aria-label={showPwConfirm ? '비밀번호 숨기기' : '비밀번호 보기'} onClick={() => setShowPwConfirm((v) => !v)}>
                  <Icon name={showPwConfirm ? 'eyeOff' : 'eye'} size={18} strokeWidth={2} />
                </button>
              )}
            />

            <fieldset className="skill-set">
              <legend className="skill-set__q">요리 실력이 어느 정도인가요?</legend>
              {SKILLS.map((s) => {
                const on = skill === s.id;
                return (
                  <label key={s.id} className={`opt ${on ? 'on' : ''}`}>
                    <input
                      type="radio" name="skill" value={s.id} className="sr-only"
                      checked={on} onChange={() => setSkill(s.id)}
                    />
                    <span className="oico" style={{ background: on ? '#fff' : s.tint, color: s.ink }}>
                      <Icon name={s.icon} size={26} />
                    </span>
                    <span className="opt__text">
                      <span className="opt__title">{s.label}</span>
                      <span className="opt__desc">{s.desc}</span>
                    </span>
                    <span className="radio">{on && <Icon name="check" size={16} strokeWidth={3} />}</span>
                  </label>
                );
              })}
            </fieldset>

            <div className="terms-box">
              <label className="terms-box__all">
                <input
                  type="checkbox" checked={termsAll}
                  onChange={(e) => { const v = e.target.checked; setTermsService(v); setTermsPrivacy(v); setTermsMarketing(v); }}
                />
                <span>
                  <b>약관 전체 동의하기</b>
                  <small>필수 및 선택 항목을 포함해요</small>
                </span>
              </label>
              <div className="terms-box__rule" />
              <label className="terms-box__row">
                <input type="checkbox" checked={termsService} onChange={(e) => setTermsService(e.target.checked)} />
                <span><b>[필수]</b> 서비스 이용약관 동의</span>
              </label>
              <label className="terms-box__row">
                <input type="checkbox" checked={termsPrivacy} onChange={(e) => setTermsPrivacy(e.target.checked)} />
                <span><b>[필수]</b> 개인정보 수집 및 이용 동의</span>
              </label>
              <label className="terms-box__row">
                <input type="checkbox" checked={termsMarketing} onChange={(e) => setTermsMarketing(e.target.checked)} />
                <span><b className="terms-box__opt">[선택]</b> 오늘의 대결 &amp; 투표 마감 알림</span>
              </label>
              {termsError && <p className="field-msg field-msg--error" style={{ margin: '6px 0 0 6px' }}><Icon name="alert" size={16} strokeWidth={2.2} />{termsError}</p>}
            </div>
          </div>
        </div>

        <BottomAction>
          {serverError && <p className="field-msg" style={{ color: 'var(--danger, #d64545)' }}>{serverError}</p>}
          <Button type="submit" disabled={submitting}>{submitting ? '가입 중…' : '가입하기'}</Button>
        </BottomAction>
      </form>
    </Screen>
  );
}
