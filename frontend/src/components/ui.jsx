import { Link } from 'react-router-dom';
import Icon from './Icon';

// Primary (orange gradient) or secondary (outlined) pill button.
// Pass `to` for navigation, otherwise it renders a <button>.
export function Button({ to, variant = 'primary', size, className = '', children, ...rest }) {
  const cls = `btn btn--${variant} ${size ? `btn--${size}` : ''} ${className}`;
  if (to) return <Link to={to} className={cls} {...rest}>{children}</Link>;
  return <button type="button" className={cls} {...rest}>{children}</button>;
}

export function Field({ id, label, error, hint, multiline = false, className = '', ...rest }) {
  const Tag = multiline ? 'textarea' : 'input';
  return (
    <div>
      {label && <label className="lbl" htmlFor={id}>{label}</label>}
      <Tag
        id={id}
        className={`field ${multiline ? 'field--area' : ''} ${error ? 'field--error' : ''} ${className}`}
        aria-invalid={!!error}
        aria-describedby={error || hint ? `${id}-msg` : undefined}
        {...rest}
      />
      {error && (
        <p id={`${id}-msg`} className="field-msg field-msg--error">
          <Icon name="alert" size={16} strokeWidth={2.2} />{error}
        </p>
      )}
      {!error && hint && (
        <p id={`${id}-msg`} className="field-msg">
          <Icon name="info" size={14} strokeWidth={2.2} />{hint}
        </p>
      )}
    </div>
  );
}

export function Chip({ on, onClick, children, withCheck = false }) {
  return (
    <button type="button" className={`chip ${on ? 'on' : ''}`} aria-pressed={on} onClick={onClick}>
      {withCheck && on && <Icon name="check" size={14} strokeWidth={3} />}
      {children}
    </button>
  );
}

export function Coin({ size = 22 }) {
  return <span className="coin" style={{ width: size, height: size }}>P</span>;
}

export function PointPill({ points, to }) {
  const inner = (<><Coin />{points.toLocaleString('ko-KR')}</>);
  return to ? <Link className="pt" to={to}>{inner}</Link> : <span className="pt">{inner}</span>;
}

export function Avatar({ name, src, size = 48, className = '', style }) {
  return (
    <span className={`av ${className}`} style={{ width: size, height: size, fontSize: Math.round(size * 0.4), ...style }}>
      {src ? <img src={src} alt="" className="av__img" /> : name?.[0] ?? '?'}
    </span>
  );
}

export function Badge({ tone = 'default', className = '', children }) {
  return <span className={`badge badge--${tone} ${className}`}>{children}</span>;
}

export function ProgressBar({ value, variant = 'light' }) {
  return (
    <div className={`progress progress--${variant}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)}>
      <div className="progress__fill" style={{ width: `${value * 100}%` }} />
    </div>
  );
}

// Photo placeholder (swap for <img> once real photos exist)
export function FoodThumb({ tone, size, icon = 'bowl', iconSize = 40, photo, className = '', children, style }) {
  const [a, b, ink] = tone;
  return (
    <div
      className={`food ${className}`}
      style={{ width: size, height: size, background: `linear-gradient(135deg, ${a}, ${b})`, color: ink, ...style }}
    >
      {photo ? <img src={photo} alt="" className="food__img" /> : <Icon name={icon} size={iconSize} strokeWidth={1.8} />}
      {children}
    </div>
  );
}

// Segmented control used for skill level pickers
export function Segmented({ options, value, onChange, label }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          role="radio"
          aria-checked={value === o.id}
          className={`seg ${value === o.id ? 'on' : ''}`}
          onClick={() => onChange(o.id)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
