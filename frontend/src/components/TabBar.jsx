import { NavLink } from 'react-router-dom';
import Icon from './Icon';

const TABS = [
  { to: '/recipes', label: '레시피', icon: 'tabRecipe' },
  { to: '/battle', label: '대결', icon: 'trophy' },
  { to: '/home', label: '홈', icon: 'home' },
  { to: '/shop', label: '상점', icon: 'gift' },
  { to: '/menu', label: '메뉴', icon: 'menu' },
];

// Active tab shows a filled icon, like the prototype.
export default function TabBar() {
  return (
    <nav className="tab" aria-label="하단 탭">
      {TABS.map((t) => (
        <NavLink key={t.to} to={t.to} className={({ isActive }) => (isActive ? 'on' : '')}>
          {({ isActive }) => (
            <>
              <Icon name={t.icon} fill={isActive && t.icon !== 'menu' ? 'currentColor' : 'none'} />
              {t.label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
