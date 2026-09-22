import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import client, { toImageUrl } from "../api/client";

export default function TopicDetail() {
  const { id } = useParams();
  const [topic, setTopic] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [voteMessage, setVoteMessage] = useState("");

  async function refresh() {
    const [topicRes, subsRes] = await Promise.all([
      client.get(`/topics/${id}`),
      client.get(`/topics/${id}/submissions`),
    ]);
    setTopic(topicRes.data);
    setSubmissions(subsRes.data);
  }

  useEffect(() => {
    refresh().catch(() => setError("주제 정보를 불러올 수 없습니다."));
  }, [id]);

  function handleFileChange(e) {
    const f = e.target.files[0];
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : null);
  }

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      await client.post(`/topics/${id}/submissions`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setFile(null);
      setPreview(null);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "업로드에 실패했습니다");
    } finally {
      setUploading(false);
    }
  }

  async function handleVote(submissionId) {
    setVoteMessage("");
    try {
      await client.post(`/submissions/${submissionId}/vote`);
      await refresh();
    } catch (err) {
      setVoteMessage(err.response?.data?.detail || "투표에 실패했습니다");
    }
  }

  if (!topic) {
    return (
      <div className="page">
        {error ? <p className="error">{error}</p> : <p>불러오는 중...</p>}
      </div>
    );
  }

  const hasVoted = submissions.some((s) => s.has_voted);

  return (
    <div className="page">
      <Link to="/" className="link-btn">
        ← 오늘의 주제로
      </Link>
      <h1>{topic.name}</h1>
      <p>{topic.description}</p>

      {!topic.has_submitted && (
        <form onSubmit={handleUpload} className="upload-form">
          <h2>내 요리 사진 올리기</h2>
          <input type="file" accept="image/*" onChange={handleFileChange} required />
          {preview && <img src={preview} alt="미리보기" className="preview" />}
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={uploading || !file}>
            {uploading ? "업로드 중..." : "제출하기"}
          </button>
        </form>
      )}

      <h2>참가자 사진 ({submissions.length})</h2>
      {voteMessage && <p className="error">{voteMessage}</p>}
      <div className="submission-grid">
        {submissions.map((sub) => (
          <div key={sub.id} className="submission-card">
            <img src={toImageUrl(sub.image_url)} alt={sub.nickname} />
            <div className="submission-info">
              <span>{sub.nickname}</span>
              <span>{sub.vote_count}표</span>
            </div>
            {!sub.is_mine && (
              <button disabled={hasVoted} onClick={() => handleVote(sub.id)}>
                {sub.has_voted ? "투표함 ✓" : hasVoted ? "이미 투표함" : "투표하기"}
              </button>
            )}
            {sub.is_mine && <span className="badge">내 제출</span>}
          </div>
        ))}
        {submissions.length === 0 && <p>아직 제출된 사진이 없습니다.</p>}
      </div>

      <Link to={`/topics/${id}/results`} className="link-btn">
        결과 보기 →
      </Link>
    </div>
  );
}
