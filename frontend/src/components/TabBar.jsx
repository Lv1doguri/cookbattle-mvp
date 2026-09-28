import { NavLink } from 'react-router-dom';
import Icon from './Icon';

const TABS = [
  { to: '/home', label: '홈', icon: 'home' },
  { to: '/recipes', label: '레시피', icon: 'tabRecipe' },
  { to: '/battle', label: '대결', icon: 'trophy', center: true },
  { to: '/shop', label: '상점', icon: 'gift' },
  { to: '/menu', label: '메뉴', icon: 'menu' },
];

// Active tab shows a filled icon, like the prototype. The 대결 tab is a
// permanently-raised floating button (design's .center/.fab), not a regular tab.
export default function TabBar() {
  return (
    <nav className="tab" aria-label="하단 탭">
      {TABS.map((t) =>
        t.center ? (
          <NavLink key={t.to} to={t.to} className="center" aria-label={t.label}>
            <span className="fab"><Icon name={t.icon} fill="currentColor" /></span>
            <span className="lbl">{t.label}</span>
          </NavLink>
        ) : (
          <NavLink key={t.to} to={t.to} className={({ isActive }) => (isActive ? 'on' : '')}>
            {({ isActive }) => (
              <>
                <Icon name={t.icon} fill={isActive && t.icon !== 'menu' ? 'currentColor' : 'none'} />
                {t.label}
              </>
            )}
          </NavLink>
        )
      )}
    </nav>
  );
}
