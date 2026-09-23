import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import GoogleLoginButton from "../components/GoogleLoginButton";
import { errorMessage } from "../api/client";

export default function Login() {
  const { login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err, "로그인에 실패했습니다"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogleCredential(idToken) {
    setError("");
    try {
      await loginWithGoogle(idToken, undefined);
      navigate("/");
    } catch (err) {
      if (err.response?.status === 400) {
        setError("처음 사용하는 구글 계정이에요. 회원가입 페이지에서 실력 등급을 선택하고 진행해주세요.");
      } else {
        setError(errorMessage(err, "구글 로그인에 실패했습니다"));
      }
    }
  }

  return (
    <div className="auth-page">
      <h1>🍳 CookBattle</h1>
      <form onSubmit={handleSubmit} className="auth-form">
        <input type="email" placeholder="이메일" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input
          type="password"
          placeholder="비밀번호"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "로그인 중..." : "로그인"}
        </button>
      </form>

      <div className="divider">또는</div>
      <GoogleLoginButton onCredential={handleGoogleCredential} />

      <p>
        계정이 없으신가요? <Link to="/signup">회원가입</Link>
      </p>
    </div>
  );
}
