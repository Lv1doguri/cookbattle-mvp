// Visual-only placeholders for social logins we haven't wired up yet (Kakao/Naver/Apple).
// They render like real buttons but do nothing when tapped — only Google (GoogleLoginButton)
// is ever functional, and only once VITE_GOOGLE_CLIENT_ID is set.
export default function SocialLoginRow() {
  return (
    <div className="social-row" title="아직 준비 중이에요 — Google 로그인만 실제로 동작해요">
      <button type="button" className="sbtn sbtn--kakao" disabled aria-label="카카오로 계속하기">
        <KakaoIcon /><span>카카오</span>
        <span className="sbtn__badge">추천</span>
      </button>
      <button type="button" className="sbtn sbtn--naver" disabled aria-label="네이버로 계속하기">
        <NaverIcon /><span>네이버</span>
      </button>
      <button type="button" className="sbtn sbtn--apple" disabled aria-label="Apple로 계속하기">
        <AppleIcon /><span>Apple</span>
      </button>
    </div>
  );
}

function KakaoIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#3C1E1E" d="M12 3C6.48 3 2 6.48 2 10.8c0 2.76 1.86 5.18 4.66 6.58-.2.75-.73 2.72-.84 3.14-.13.52.19.51.4.37.17-.11 2.66-1.8 3.74-2.54.66.1 1.34.15 2.04.15 5.52 0 10-3.48 10-7.7C22 6.48 17.52 3 12 3z" />
    </svg>
  );
}

function NaverIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#fff" d="M14.4 12.9 9.6 5H5v14h4.6v-7.9L14.4 19H19V5h-4.6z" />
    </svg>
  );
}

function AppleIcon() {
  return (
    <svg width="18" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#fff"
        d="M16.7 1c.1 1.1-.3 2.2-1 3-.7.8-1.9 1.5-3 1.4-.1-1.1.4-2.2 1-3C14.4 1.6 15.6 1 16.7 1zM20.8 17.2c-.5 1.1-1.1 2.1-1.9 3.1-.9 1.1-1.8 2.2-3.2 2.2-1.4 0-1.8-.8-3.4-.8-1.6 0-2.1.8-3.4.9-1.3 0-2.3-1.2-3.2-2.3C3.7 18 2.4 14.5 3.4 12.1c.6-1.6 1.8-2.9 3.3-2.9 1.3-.1 2.2.9 3.4.9s2.4-.9 3.9-.8c.9 0 2.3.4 3.2 1.5-2.8 1.5-2.3 5.4.6 6.4z"
      />
    </svg>
  );
}
