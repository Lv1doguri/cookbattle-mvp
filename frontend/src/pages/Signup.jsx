import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import GoogleLoginButton from "../components/GoogleLoginButton";
import { errorMessage } from "../api/client";

const TIERS = [
  { value: "beginner", label: "하 (초보)" },
  { value: "intermediate", label: "중" },
  { value: "advanced", label: "상 (고수)" },
];

export default function Signup() {
  const { signup, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [skillTier, setSkillTier] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await signup(email, password, nickname, skillTier);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err, "회원가입에 실패했습니다"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogleCredential(idToken, tier) {
    setError("");
    try {
      await loginWithGoogle(idToken, tier);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err, "구글 회원가입에 실패했습니다"));
    }
  }

  return (
    <div className="auth-page">
      <h1>🍳 CookBattle</h1>
      <form onSubmit={handleSubmit} className="auth-form">
        <input
          type="text"
          placeholder="닉네임"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          required
        />
        <input type="email" placeholder="이메일" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input
          type="password"
          placeholder="비밀번호"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={4}
        />

        <div className="tier-select">
          {TIERS.map((tier) => (
            <label key={tier.value}>
              <input
                type="radio"
                name="skillTier"
                value={tier.value}
                checked={skillTier === tier.value}
                onChange={(e) => setSkillTier(e.target.value)}
              />
              {tier.label}
            </label>
          ))}
        </div>

        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting || !skillTier}>
          {submitting ? "가입 중..." : "회원가입"}
        </button>
      </form>

      <div className="divider">또는</div>
      <GoogleLoginButton skillTier={skillTier} disabled={!skillTier} onCredential={handleGoogleCredential} />

      <p>
        이미 계정이 있으신가요? <Link to="/login">로그인</Link>
      </p>
    </div>
  );
}
