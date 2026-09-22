import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function TodayTopics() {
  const { user, logout } = useAuth();
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    client
      .get("/topics/today")
      .then(({ data }) => setTopics(data))
      .catch(() => setError("오늘의 주제를 불러올 수 없습니다. 새로고침해 주세요."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>🍳 오늘의 주제</h1>
        <div>
          <span className="nickname">{user?.nickname}님</span>
          <button className="link-btn" onClick={logout}>
            로그아웃
          </button>
        </div>
      </header>

      {loading && <p>불러오는 중...</p>}
      {error && <p className="error">{error}</p>}

      <div className="topic-grid">
        {topics.map((topic) => (
          <Link key={topic.id} to={`/topics/${topic.id}`} className="topic-card">
            <h2>{topic.name}</h2>
            <p>{topic.description}</p>
            <div className="topic-meta">
              <span>참가 {topic.submission_count}명</span>
              {topic.has_submitted && <span className="badge">제출 완료</span>}
              {topic.is_closed && <span className="badge closed">마감</span>}
            </div>
          </Link>
        ))}
        {!loading && topics.length === 0 && !error && <p>오늘 등록된 주제가 없습니다.</p>}
      </div>
    </div>
  );
}
