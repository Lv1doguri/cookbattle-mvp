import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Screen, IconButton } from '../components/Screen';
import Icon from '../components/Icon';
import { useApp } from '../state/AppContext';

// 조작(사진 한 장을 어디서 가져옴) 방지용으로 각도별 사진을 여러 장 요구해요. 백엔드 ENTRY_MIN_PHOTOS와 맞춰주세요.
const ANGLE_PROMPTS = ['재료·조리 전 모습', '조리 중인 모습', '완성된 요리'];

// In-app camera only (no gallery upload) so entries are cooked, not downloaded.
// Uses getUserMedia; falls back to a placeholder frame when no camera / permission denied.
export default function CookVerifyCamera() {
  const { setDraftPhotos, fetchBattle } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  // Battle.jsx tells us which card (테마 vs 오늘의 대결) was tapped; defaults to
  // daily/내 그룹 if opened without state (e.g. a refresh mid-flow).
  const { kind, tier } = location.state || {};
  const [topic, setTopic] = useState('');
  const [shots, setShots] = useState([]); // 지금까지 찍은 각도별 dataURL들

  useEffect(() => {
    fetchBattle(tier, kind).then((b) => setTopic(b.topic)).catch(() => {});
  }, [fetchBattle, tier, kind]);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [facing, setFacing] = useState('environment');
  const [flash, setFlash] = useState(false);
  const [status, setStatus] = useState('loading'); // loading | live | unavailable

  const stop = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  };

  useEffect(() => {
    let cancelled = false;
    async function start() {
      stop();
      if (!navigator.mediaDevices?.getUserMedia) return setStatus('unavailable');
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: facing, width: { ideal: 1280 }, height: { ideal: 1280 } },
          audio: false,
        });
        if (cancelled) return stream.getTracks().forEach((t) => t.stop());
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        setStatus('live');
      } catch {
        if (!cancelled) setStatus('unavailable');
      }
    }
    start();
    return () => {
      cancelled = true;
      stop();
    };
  }, [facing]);

  // Torch works on most Android Chrome back cameras; elsewhere the toggle is visual only.
  useEffect(() => {
    const track = streamRef.current?.getVideoTracks()[0];
    if (track?.getCapabilities?.().torch) {
      track.applyConstraints({ advanced: [{ torch: flash }] }).catch(() => {});
    }
  }, [flash, status]);

  const capture = useCallback(() => {
    let shot = null;
    const video = videoRef.current;
    if (status === 'live' && video?.videoWidth) {
      const side = Math.min(video.videoWidth, video.videoHeight);
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = Math.min(side, 1080);
      const sx = (video.videoWidth - side) / 2;
      const sy = (video.videoHeight - side) / 2;
      canvas.getContext('2d').drawImage(video, sx, sy, side, side, 0, 0, canvas.width, canvas.height);
      shot = canvas.toDataURL('image/jpeg', 0.85);
    }
    const next = [...shots, shot];
    setShots(next);
    if (next.length >= ANGLE_PROMPTS.length) {
      setDraftPhotos(next);
      stop();
      navigate('/battle/verify', { state: { kind, tier } });
    }
  }, [status, shots, setDraftPhotos, navigate, kind, tier]);

  const retakeLast = useCallback(() => setShots((s) => s.slice(0, -1)), []);

  return (
    <Screen tone="dark">
      <div className="cam-bg" aria-hidden="true" />
      <video
        ref={videoRef}
        className={`cam-video ${facing === 'user' ? 'cam-video--mirror' : ''}`}
        hidden={status !== 'live'}
        autoPlay playsInline muted
      />
      <div className="cam-grid" aria-hidden="true" />

      <div className="cam-top">
        <IconButton label="촬영 취소" variant="glass" onClick={() => navigate('/battle')}>
          <Icon name="close" size={22} strokeWidth={2.4} />
        </IconButton>
        <span className="cam-pill">{topic} 인증샷 {shots.length + 1}/{ANGLE_PROMPTS.length}</span>
        <IconButton label={flash ? '플래시 끄기' : '플래시 켜기'} variant="glass" onClick={() => setFlash((f) => !f)}>
          <Icon name="flash" size={20} fill={flash ? 'currentColor' : 'none'} />
        </IconButton>
      </div>

      <div className="cam-stage">
        <div className="cam-frame">
          <span className="corner corner--tl" /><span className="corner corner--tr" />
          <span className="corner corner--bl" /><span className="corner corner--br" />
          {status !== 'live' && (
            <div className="cam-placeholder">
              <Icon name="bowl" size={56} strokeWidth={1.4} />
              {status === 'unavailable' && <span>카메라를 사용할 수 없어요.<br />권한을 허용하면 바로 찍을 수 있어요.</span>}
            </div>
          )}
        </div>
      </div>

      <p className="cam-hint">지금은 <b>{ANGLE_PROMPTS[shots.length]}</b>을 찍어주세요</p>

      {shots.length > 0 && (
        <div className="cam-shots">
          {shots.map((s, i) => (
            <span key={i} className="cam-shots__thumb">
              {s ? <img src={s} alt="" /> : <Icon name="bowl" size={16} />}
            </span>
          ))}
        </div>
      )}

      <div className="cam-controls">
        {shots.length > 0 ? (
          <button type="button" className="cam-switch" onClick={retakeLast}>
            <Icon name="refresh" size={15} style={{ marginRight: 5 }} />다시 찍기
          </button>
        ) : (
          <button type="button" className="cam-switch" onClick={() => setFacing((f) => (f === 'environment' ? 'user' : 'environment'))}>
            <Icon name="switchCam" size={15} style={{ marginRight: 5 }} />전환
          </button>
        )}
        <button type="button" className="shutter" aria-label="촬영하기" onClick={capture}>
          <span />
        </button>
        <span />
      </div>
    </Screen>
  );
}
