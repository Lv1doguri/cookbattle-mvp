import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Screen } from '../components/Screen';
import { Button, Field } from '../components/ui';
import Icon from '../components/Icon';
import logo from '../assets/logo.png';
import GoogleLoginButton from '../components/GoogleLoginButton';
import SocialLoginRow from '../components/SocialLoginRow';
import { useApp } from '../state/AppContext';

export default function Login() {
  const { login, loginWithGoogle } = useApp();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return setError('이메일 또는 아이디를 입력해 주세요');
    if (password.length < 8) return setError('비밀번호는 8자 이상이에요');
    setError('');
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate('/home', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const onGoogleCredential = async (idToken) => {
    setError('');
    try {
      await loginWithGoogle(idToken);
      navigate('/home', { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <Screen tone="soft">
      <div className="body">
        <div className="login-brand">
          <span className="login-brand__logo-wrap">
            <img src={logo} alt="자취 요리왕 로고" className="login-brand__logo" />
          </span>
          <div className="login-brand__title">
            <h1 className="login-brand__name">자취 요리왕</h1>
            <span className="badge badge--beta">BETA</span>
          </div>
          <p className="login-brand__tag">요리하고, 공유하고, 대결하다</p>
          <span className="login-brand__chip">
            <Icon name="trophy" size={15} strokeWidth={2} />오늘 배틀에 투표하면 +1P 적립!
          </span>
        </div>

        <form className="card login-form" onSubmit={onSubmit} noValidate>
          <Field
            id="login-email" label="이메일 또는 아이디" type="text" autoComplete="username" icon="mail"
            className="field--soft" placeholder="you@university.ac.kr (또는 아이디)"
            value={email} onChange={(e) => setEmail(e.target.value)}
          />
          <Field
            id="login-pw" label="비밀번호" type={showPw ? 'text' : 'password'} autoComplete="current-password"
            icon="lock" className="field--soft" error={error}
            value={password} onChange={(e) => setPassword(e.target.value)}
            rightSlot={(
              <button type="button" className="field-eye" aria-label={showPw ? '비밀번호 숨기기' : '비밀번호 보기'} onClick={() => setShowPw((v) => !v)}>
                <Icon name={showPw ? 'eyeOff' : 'eye'} size={18} strokeWidth={2} />
              </button>
            )}
          />
          <label className="auto-login">
            <input type="checkbox" checked readOnly />자동 로그인 유지
          </label>
          <Button type="submit" disabled={submitting} style={{ marginTop: 2 }}>{submitting ? '로그인 중…' : '요리 배틀 입장하기'}</Button>

          <div className="divider">
            <span className="divider__line" />
            <span className="divider__text">간편 로그인</span>
            <span className="divider__line" />
          </div>
          <GoogleLoginButton onCredential={onGoogleCredential} />
          <SocialLoginRow />
        </form>

        <Link to="/signup" className="signup-promo">
          <span className="signup-promo__ico"><Icon name="gift" size={20} strokeWidth={1.8} /></span>
          <span className="signup-promo__text">
            <b>아직 회원이 아니신가요?</b>
            <span>30초 가입하고 웰컴 포인트 받기</span>
          </span>
          <Icon name="chevronRight" size={18} strokeWidth={2.4} color="var(--ink-6)" />
        </Link>
      </div>
    </Screen>
  );
}
