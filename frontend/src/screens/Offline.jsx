import { useState } from 'react';
import { Screen, TopBar } from '../components/Screen';
import TabBar from '../components/TabBar';
import Icon from '../components/Icon';
import { useApp } from '../state/AppContext';

// Rendered automatically by <App> whenever the browser goes offline,
// and reachable at /offline for design review.
export default function Offline({ onRetry }) {
  const { setOnline } = useApp();
  const [checking, setChecking] = useState(false);

  const retry = () => {
    setChecking(true);
    setTimeout(() => {
      setChecking(false);
      if (navigator.onLine) {
        setOnline(true);
        onRetry?.();
      }
    }, 600);
  };

  return (
    <Screen tone="mist">
      <TopBar title="요리왕" brand />
      <div className="offline" role="alert">
        <div className="offline__halo">
          <span className="offline__ico"><Icon name="wifiOff" size={40} /></span>
        </div>
        <h2>연결을 확인해 주세요</h2>
        <p>인터넷 연결이 불안정해요.<br />잠시 후 다시 시도해 주세요.</p>
        <button type="button" className="offline__retry" onClick={retry} disabled={checking}>
          <Icon name="refresh" size={18} strokeWidth={2.4} className={checking ? 'spin' : ''} />
          {checking ? '확인 중…' : '다시 시도'}
        </button>
      </div>
      <TabBar />
    </Screen>
  );
}
