import { Link, useNavigate } from 'react-router-dom';
import Icon from './Icon';

// One phone screen. `tone` switches the background (default / plain / dark / soft).
export function Screen({ tone = 'default', className = '', children, ...rest }) {
  return (
    <div className={`scr scr--${tone} ${className}`} {...rest}>
      {children}
    </div>
  );
}

// Gradient header area that sits under the top bar.
export function Header({ className = '', children, ...rest }) {
  return (
    <header className={`hdr ${className}`} {...rest}>
      {children}
    </header>
  );
}

// Top bar. Large brand-colored title for tab roots, small title + back button for sub-pages.
export function TopBar({ title, back, brand = false, logo, children }) {
  const navigate = useNavigate();
  return (
    <div className={`top ${back ? 'top--sub' : ''}`}>
      {back && (
        <IconButton label="뒤로" onClick={() => (typeof back === 'string' ? navigate(back) : navigate(-1))}>
          <Icon name="back" strokeWidth={2.2} />
        </IconButton>
      )}
      {title && (
        <span style={{ display: 'flex', alignItems: 'center', gap: 8, flexGrow: 1 }}>
          {logo && <img src={logo} alt="" style={{ width: 26, height: 26, borderRadius: 8, flexShrink: 0 }} />}
          <h1 className={back ? 'ttl-s' : `ttl ${brand ? 'ttl--brand' : ''}`}>{title}</h1>
        </span>
      )}
      {children}
    </div>
  );
}

export function IconButton({ label, to, onClick, variant = '', children, dot = false }) {
  const cls = `ibtn ${variant ? `ibtn--${variant}` : ''}`;
  const inner = (
    <>
      {children}
      {dot && <span className="ibtn__dot" />}
    </>
  );
  return to ? (
    <Link className={cls} to={to} aria-label={label}>{inner}</Link>
  ) : (
    <button type="button" className={cls} onClick={onClick} aria-label={label}>{inner}</button>
  );
}

// Sticky bottom action area (above home indicator)
export function BottomAction({ className = '', children }) {
  return <div className={`bottom-action ${className}`}>{children}</div>;
}
