import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import client, { toImageUrl } from "../api/client";

export default function Results() {
  const { id } = useParams();
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    client
      .get(`/topics/${id}/results`)
      .then(({ data }) => setResults(data))
      .catch(() => setError("결과를 불러올 수 없습니다."));
  }, [id]);

  return (
    <div className="page">
      <Link to={`/topics/${id}`} className="link-btn">
        ← 대결로 돌아가기
      </Link>
      {error && <p className="error">{error}</p>}
      {results && (
        <>
          <h1>{results.topic_name} 결과</h1>
          <div className="results-list">
            {results.entries.map((entry) => (
              <div key={entry.submission_id} className={`result-row ${entry.is_winner ? "winner" : ""}`}>
                <span className="rank">{entry.is_winner ? "🏆" : `${entry.rank}위`}</span>
                <img src={toImageUrl(entry.image_url)} alt={entry.nickname} />
                <span className="nickname">{entry.nickname}</span>
                <span className="votes">{entry.vote_count}표</span>
              </div>
            ))}
            {results.entries.length === 0 && <p>아직 제출된 사진이 없습니다.</p>}
          </div>
        </>
      )}
    </div>
  );
}
