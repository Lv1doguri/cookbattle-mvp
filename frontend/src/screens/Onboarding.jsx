import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Screen, BottomAction } from '../components/Screen';
import { Button } from '../components/ui';
import { ONBOARDING } from '../data/mock';

const MINI_TABS = ['레시피', '대결', '홈', '상점', '메뉴'];

export default function Onboarding() {
  const navigate = useNavigate();
  const [i, setI] = useState(0);
  const step = ONBOARDING[i];
  const last = i === ONBOARDING.length - 1;
  const bubbleRight = step.highlight >= 2;

  return (
    <Screen tone="mist">
      <div className="onb-top">
        <span className="onb-count">{i + 1} / {ONBOARDING.length}</span>
        <Link to="/home" className="onb-skip">건너뛰기</Link>
      </div>

      <div className="onb-stage">
        <div className="onb-phone" aria-hidden="true">
          <div className="onb-phone__hero" />
          <div className="onb-phone__grid"><div /><div /></div>
          <div className="onb-phone__block" />
          <div className="onb-phone__tabs">
            {MINI_TABS.map((t, idx) => (
              <span key={t} className={`mt ${idx === step.highlight ? 'on' : ''}`}>
                <span className="mi" />{t}
              </span>
            ))}
          </div>
        </div>
        <div className={`onb-bubble ${bubbleRight ? 'onb-bubble--right' : 'onb-bubble--left'}`}>{step.hint}</div>
      </div>

      <div className="onb-copy">
        <h1>{step.title}</h1>
        <p>{step.body.split('\n').map((l, k) => <span key={k}>{l}<br /></span>)}</p>
        <div className="dots" aria-label="튜토리얼 단계">
          {ONBOARDING.map((_, k) => (
            <button
              key={k} type="button" aria-current={k === i ? 'step' : undefined} aria-label={`${k + 1}단계`}
              className={`dot-ind ${k === i ? 'on' : ''}`} onClick={() => setI(k)}
            />
          ))}
        </div>
      </div>

      <BottomAction>
        <Button onClick={() => (last ? navigate('/home') : setI(i + 1))}>{last ? '시작하기' : '다음'}</Button>
      </BottomAction>
    </Screen>
  );
}
