import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Screen } from '../components/Screen';
import { Button, Field } from '../components/ui';
import { MascotArt } from '../components/Icon';
import { useApp } from '../state/AppContext';

export default function Login() {
  const { login } = useApp();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const onSubmit = (e) => {
    e.preventDefault();
    if (!email.includes('@')) return setError('이메일 형식을 확인해 주세요');
    if (password.length < 8) return setError('비밀번호는 8자 이상이에요');
    setError('');
    login(email);
    navigate('/home', { replace: true });
  };

  return (
    <Screen tone="soft">
      <div className="body">
        <div className="login-brand">
          <MascotArt />
          <h1 className="login-brand__name">요리왕</h1>
          <p className="login-brand__tag">요리하고, 공유하고, 대결하다</p>
        </div>

        <form className="card login-form" onSubmit={onSubmit} noValidate>
          <Field
            id="login-email" label="이메일" type="email" autoComplete="email"
            className="field--soft" placeholder="you@university.ac.kr"
            value={email} onChange={(e) => setEmail(e.target.value)}
          />
          <Field
            id="login-pw" label="비밀번호" type="password" autoComplete="current-password"
            className="field--soft" error={error}
            value={password} onChange={(e) => setPassword(e.target.value)}
          />
          <Button type="submit" style={{ marginTop: 6 }}>로그인</Button>
        </form>

        <p className="login-foot">
          계정이 없으신가요? <Link to="/signup">회원가입</Link>
        </p>
      </div>
    </Screen>
  );
}
