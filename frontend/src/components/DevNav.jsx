import { NavLink } from 'react-router-dom';
import { useApp } from '../state/AppContext';

// Screen jumper from the prototype, for design reviews. Only rendered in dev.
// Recipe id 1 assumes a freshly-seeded backend (backend/app/seed.py seeds 김치볶음밥 first).
const SCREENS = [
  ['/', '01 로그인'], ['/signup', '02 회원가입'], ['/home', '03 홈'], ['/recipes', '04 레시피 목록'],
  ['/recipes/filter', '05 필터'], ['/battle', '06 대결 홈'], ['/onboarding', '07 앱 사용법'],
  ['/profile/edit', '08 정보 수정'], ['/recipes/1', '09 레시피 상세'], ['/menu', '10 메뉴'],
  ['/offline', '11 연결 오류'], ['/battle/camera', '12 사진 촬영'], ['/battle/verify', '12b 요리 인증'],
  ['/battle/done', '13 참가 완료'], ['/battle/vote', '14 투표'], ['/battle/result', '15 대결 결과'], ['/shop', '16 상점'],
];

export default function DevNav() {
  const { loggedIn } = useApp();
  return (
    <nav className="devnav" aria-label="개발용 화면 이동">
      {!loggedIn && <span className="devnav__hint">먼저 로그인/회원가입하세요</span>}
      {SCREENS.map(([to, label]) => (
        <NavLink key={to} to={to} end className={({ isActive }) => (isActive ? 'on' : '')}>
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
