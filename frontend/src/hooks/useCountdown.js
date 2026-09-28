import { useEffect, useState } from 'react';

// 서버가 준 seconds_left를 받아서, 다음 fetch 전까지는 로컬에서 1초씩 째깍째깍 줄여요.
export default function useCountdown(secondsLeft) {
  const [left, setLeft] = useState(secondsLeft ?? 0);
  useEffect(() => setLeft(secondsLeft ?? 0), [secondsLeft]);
  useEffect(() => {
    const t = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, []);
  const h = Math.floor(left / 3600);
  const m = Math.floor((left % 3600) / 60);
  const s = left % 60;
  const pad = (n) => String(n).padStart(2, '0');
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}
