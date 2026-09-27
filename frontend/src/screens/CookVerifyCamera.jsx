import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Screen, IconButton } from '../components/Screen';
import Icon from '../components/Icon';
import { BATTLES } from '../data/mock';
import { useApp } from '../state/AppContext';

// In-app camera only (no gallery upload) so entries are cooked, not downloaded.
// Uses getUserMedia; falls back to a placeholder frame when no camera / permission denied.
export default function CookVerifyCamera() {
  const { user, setDraftPhoto } = useApp();
  const navigate = useNavigate();
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
    const video = videoRef.current;
    if (status === 'live' && video?.videoWidth) {
      const side = Math.min(video.videoWidth, video.videoHeight);
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = Math.min(side, 1080);
      const sx = (video.videoWidth - side) / 2;
      const sy = (video.videoHeight - side) / 2;
      canvas.getContext('2d').drawImage(video, sx, sy, side, side, 0, 0, canvas.width, canvas.height);
      setDraftPhoto(canvas.toDataURL('image/jpeg', 0.85));
    } else {
      setDraftPhoto(null);
    }
    stop();
    navigate('/battle/verify');
  }, [status, setDraftPhoto, navigate]);

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
        <span className="cam-pill">{BATTLES[user.skill].topic} 대결 인증샷</span>
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

      <p className="cam-hint">음식이 화면 가운데에 잘 보이도록 담아주세요</p>

      <div className="cam-controls">
        <button type="button" className="cam-switch" onClick={() => setFacing((f) => (f === 'environment' ? 'user' : 'environment'))}>
          <Icon name="switchCam" size={15} style={{ marginRight: 5 }} />전환
        </button>
        <button type="button" className="shutter" aria-label="촬영하기" onClick={capture}>
          <span />
        </button>
        <span />
      </div>
    </Screen>
  );
}
