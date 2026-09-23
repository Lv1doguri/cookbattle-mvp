import { useEffect, useRef, useState } from "react";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const SCRIPT_SRC = "https://accounts.google.com/gsi/client";

function loadGoogleScript() {
  if (window.google?.accounts?.id) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", reject);
      return;
    }
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("failed to load Google script"));
    document.head.appendChild(script);
  });
}

// Renders Google's own "Continue with Google" button (Google Identity
// Services) and hands the raw ID token back to the caller — verifying
// it and turning it into our own access_token happens server-side via
// POST /auth/google, not here.
export default function GoogleLoginButton({ skillTier, onCredential, disabled }) {
  const buttonRef = useRef(null);
  const [ready, setReady] = useState(false);
  const skillTierRef = useRef(skillTier);
  skillTierRef.current = skillTier;

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    let cancelled = false;
    loadGoogleScript()
      .then(() => {
        if (!cancelled) setReady(true);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!ready || disabled || !buttonRef.current) return;
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (response) => onCredential(response.credential, skillTierRef.current),
    });
    buttonRef.current.innerHTML = "";
    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: "outline",
      size: "large",
      width: 320,
      text: "continue_with",
    });
  }, [ready, disabled, onCredential]);

  if (!GOOGLE_CLIENT_ID) return null;

  return (
    <div>
      <div ref={buttonRef} style={disabled ? { opacity: 0.4, pointerEvents: "none" } : undefined} />
      {disabled && <p className="hint">실력 등급을 먼저 선택해주세요</p>}
    </div>
  );
}
