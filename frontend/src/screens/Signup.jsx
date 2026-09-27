import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Screen, Header, TopBar, BottomAction } from '../components/Screen';
import { Button, Field } from '../components/ui';
import Icon from '../components/Icon';
import { SKILLS } from '../data/mock';
import { useApp } from '../state/AppContext';

export default function Signup() {
  const { signup, isNicknameTaken } = useApp();
  const navigate = useNavigate();
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [skill, setSkill] = useState('intermediate');
  const [touched, setTouched] = useState(false);

  const nickError =
    touched && nickname.trim().length === 0 ? '닉네임을 입력해 주세요'
      : nickname && isNicknameTaken(nickname) ? '이미 사용 중인 닉네임입니다'
        : '';
  const pwError = touched && password.length < 8 ? '비밀번호는 8자 이상이에요' : '';

  const onSubmit = (e) => {
    e.preventDefault();
    setTouched(true);
    if (!nickname.trim() || isNicknameTaken(nickname) || password.length < 8) return;
    signup({ nickname: nickname.trim(), skill });
    navigate('/onboarding', { replace: true });
  };

  return (
    <Screen>
      <form className="scr-form" onSubmit={onSubmit} noValidate>
        <Header>
          <TopBar title="회원가입" back="/" />
          <p className="signup-hello">반가워요!<br />요리왕에서 쓸 이름을 알려주세요</p>
        </Header>

        <div className="body">
          <div className="stack signup-fields">
            <Field
              id="su-nick" label="닉네임" autoComplete="nickname" maxLength={12}
              value={nickname} onChange={(e) => setNickname(e.target.value)} error={nickError}
            />
            <Field
              id="su-pw" label="비밀번호" type="password" autoComplete="new-password"
              value={password} onChange={(e) => setPassword(e.target.value)} error={pwError}
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
          </div>
        </div>

        <BottomAction>
          <Button type="submit">가입하기</Button>
        </BottomAction>
      </form>
    </Screen>
  );
}
