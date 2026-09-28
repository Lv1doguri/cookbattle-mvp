import { useEffect, useRef, useState } from 'react';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const SCRIPT_SRC = 'https://accounts.google.com/gsi/client';

function loadGoogleScript() {
  if (window.google?.accounts?.id) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', reject);
      return;
    }
    const script = document.createElement('script');
    script.src = SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('failed to load Google script'));
    document.head.appendChild(script);
  });
}

// Renders Google's own "Continue with Google" button (Google Identity Services)
// over our own gbtn-styled placeholder, and hands the raw ID token back to the
// caller — verifying it and turning it into our access_token happens server-side
// via POST /auth/google (see AppContext.loginWithGoogle), not here.
//
// Without VITE_GOOGLE_CLIENT_ID set (no OAuth app registered yet), this renders
// the design's static button that explains why it's disabled instead of a real
// Google button — see API_CONTRACT.md, "Google 로그인" section.
export default function GoogleLoginButton({ onCredential, disabled }) {
  const wrapRef = useRef(null);
  const [ready, setReady] = useState(false);
  const onCredentialRef = useRef(onCredential);
  onCredentialRef.current = onCredential;

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    let cancelled = false;
    loadGoogleScript()
      .then(() => { if (!cancelled) setReady(true); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!ready || disabled || !wrapRef.current) return;
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (response) => onCredentialRef.current(response.credential),
    });
    wrapRef.current.innerHTML = '';
    window.google.accounts.id.renderButton(wrapRef.current, {
      theme: 'outline', size: 'large', width: 320, text: 'continue_with', shape: 'pill',
    });
  }, [ready, disabled]);

  if (!GOOGLE_CLIENT_ID) {
    return (
      <button type="button" className="gbtn" disabled title="아직 Google Client ID가 설정되지 않았어요">
        <GoogleG />Google로 계속하기
      </button>
    );
  }

  return <div ref={wrapRef} style={disabled ? { opacity: .4, pointerEvents: 'none' } : undefined} />;
}

function GoogleG() {
  return (
    <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.9 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.5 6.1 29.5 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.7-.4-3.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.5 15.1 18.9 12 24 12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.5 6.1 29.5 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 10-2 13.6-5.2l-6.3-5.3C29.3 35.5 26.8 36 24 36c-5.3 0-9.7-3.1-11.3-7.6l-6.6 5.1C9.6 39.6 16.3 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.1 5.7l6.3 5.3C39.9 37 44 31.8 44 24c0-1.3-.1-2.7-.4-3.5z" />
    </svg>
  );
}
