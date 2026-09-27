// All icons are lifted from the Figma prototype (24×24 grid, stroke-based).
// Usage: <Icon name="back" size={24} strokeWidth={2.2} />
const PATHS = {
  back: <path d="M15 5l-7 7 7 7" />,
  chevronRight: <path d="M9 5l7 7-7 7" />,
  chevronDown: <path d="M6 9l6 6 6-6" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  check: <path d="M5 12l5 5 9-10" />,
  bookmark: <path d="M7 4h10v16l-5-4-5 4z" />,
  bell: (
    <>
      <path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </>
  ),
  filter: (
    <>
      <path d="M4 7h10M18 7h2M4 17h2M10 17h10" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="8" cy="17" r="2" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="6" />
      <path d="M20 20l-4.5-4.5" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l3 2" />
    </>
  ),
  history: (
    <>
      <path d="M4 12a8 8 0 1 0 2.5-5.8" />
      <path d="M4 4v4h4" />
      <path d="M12 8v4l3 2" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 12a8 8 0 1 1-2.5-5.8" />
      <path d="M20 4v5h-5" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8v.01" />
    </>
  ),
  alert: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v5M12 16.5v.01" />
    </>
  ),
  camera: (
    <>
      <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
      <circle cx="12" cy="13" r="3.5" />
    </>
  ),
  flash: <path d="M13 3L4 14h6l-1 7 9-11h-6z" />,
  switchCam: (
    <>
      <path d="M17 2l4 4-4 4" />
      <path d="M3 12v-2a4 4 0 0 1 4-4h14" />
      <path d="M7 22l-4-4 4-4" />
      <path d="M21 12v2a4 4 0 0 1-4 4H3" />
    </>
  ),
  edit: <path d="M4 20h4L19 9l-4-4L4 16z" />,
  comment: <path d="M4 5h16v11H9l-5 4z" />,
  play: <path d="M9 6.5v11l9-5.5z" />,
  arrowUp: <path d="M12 19V5M6 11l6-6 6 6" />,
  lock: (
    <>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="9" r="3" />
      <path d="M3 19a6 6 0 0 1 12 0" />
      <path d="M16 6a3 3 0 0 1 0 6M18 19a6 6 0 0 0-2-4.5" />
    </>
  ),
  wallet: (
    <>
      <rect x="3" y="6" width="18" height="13" rx="3" />
      <path d="M3 10h18" />
      <path d="M7 15h3" />
    </>
  ),
  fridge: (
    <>
      <rect x="6" y="3" width="12" height="18" rx="3" />
      <path d="M6 10h12M9 6v2M9 13v3" />
    </>
  ),
  wifiOff: (
    <>
      <path d="M3 3l18 18" />
      <path d="M2 9a15 15 0 0 1 5-3M22 9a15 15 0 0 0-9.5-4M5.5 12.5a10 10 0 0 1 3.5-2M18.5 12.5a10 10 0 0 0-2.5-1.8M9 16a4.5 4.5 0 0 1 4.5-1M12 20h.01" />
    </>
  ),
  heart: <path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10z" />,

  // Food / category
  bowl: (
    <>
      <path d="M3 11h18a9 9 0 0 1-18 0z" />
      <path d="M9 7c0-1.5 1.5-1.5 1.5-3M13 7c0-1.5 1.5-1.5 1.5-3" />
    </>
  ),
  ramen: (
    <>
      <path d="M3 11h18a9 9 0 0 1-18 0z" />
      <path d="M8 7c1-1 2 0 3-1s2 0 3-1 2 0 3-1" />
    </>
  ),
  egg: <ellipse cx="12" cy="13" rx="6" ry="8" />,
  coffee: (
    <>
      <path d="M5 9h11v5a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5z" />
      <path d="M16 10h1.5a2.5 2.5 0 0 1 0 5H16" />
      <path d="M9 3v3M12 3v3" />
    </>
  ),
  cutlery: (
    <>
      <path d="M7 3v8M5 3v5a2 2 0 0 0 4 0V3M7 11v10" />
      <path d="M17 3c-2 1-3 4-3 7h3v11" />
    </>
  ),
  store: (
    <>
      <path d="M4 9l1.5-5h13L20 9" />
      <path d="M4 9h16v2a3 3 0 0 1-6 0 3 3 0 0 1-4 0 3 3 0 0 1-6 0z" />
      <path d="M5 13v7h14v-7" />
      <path d="M10 20v-4h4v4" />
    </>
  ),
  burger: (
    <>
      <path d="M4 11a8 5 0 0 1 16 0z" />
      <path d="M3 14h18" />
      <path d="M4 17h16a2 2 0 0 1-2 3H6a2 2 0 0 1-2-3z" />
    </>
  ),

  // Skill levels
  sprout: (
    <>
      <path d="M12 20v-8" />
      <path d="M12 12c0-4-3-6-7-6 0 4 3 6 7 6zM12 10c0-3 2-5 6-5 0 3-2 5-6 5z" />
    </>
  ),
  pan: (
    <>
      <circle cx="10" cy="13" r="6" />
      <path d="M16 13h6" />
      <circle cx="10" cy="13" r="2" />
    </>
  ),
  chefHat: (
    <>
      <path d="M7 14a4 4 0 1 1 1.5-7.7A4 4 0 0 1 16 6a4 4 0 1 1 1 8v5H7z" />
      <path d="M7 16h10" />
    </>
  ),

  // Tab bar
  tabRecipe: (
    <>
      <path d="M4 10h16v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z" />
      <path d="M2 10h20" />
      <path d="M9 6c0-1 1-1 1-2M14 6c0-1 1-1 1-2" fill="none" />
    </>
  ),
  trophy: (
    <>
      <path d="M8 4h8v5a4 4 0 0 1-8 0z" />
      <path d="M8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4" />
      <path d="M12 13v4M8 20h8" />
    </>
  ),
  home: <path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z" />,
  gift: (
    <>
      <rect x="4" y="9" width="16" height="11" rx="2" />
      <path d="M3 9h18M12 9v11M12 9c-2 0-4-1-4-3s3-2 4 3c1-5 4-5 4-3s-2 3-4 3" />
    </>
  ),
  menu: <path d="M5 7h14M5 12h14M5 17h14" />,
};

export default function Icon({ name, size = 24, strokeWidth = 2, color = 'currentColor', fill = 'none', style, className }) {
  const body = PATHS[name];
  if (!body) {
    if (import.meta.env?.DEV) console.warn(`[Icon] unknown icon: ${name}`);
    return null;
  }
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={fill}
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      style={style}
      className={className}
    >
      {body}
    </svg>
  );
}

// Filled illustration icons (colors baked in, used on food photos / placeholders)
export function EggArt({ size = 54, yolk = '#FFB020', outline }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <ellipse cx="12" cy="13" rx={outline ? 7 : 8} ry={outline ? 6 : 6.5} fill="#fff" stroke={outline} strokeWidth={outline ? 1.8 : 0} />
      <circle cx="12.5" cy="12.5" r={outline ? 2.8 : 3.4} fill={yolk} />
    </svg>
  );
}

export function EggBowlArt({ size = 54 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3 11h18a9 9 0 0 1-18 0z" fill="#fff" />
      <circle cx="9" cy="14" r="2.2" fill="#FFB020" />
      <circle cx="15" cy="14" r="2.2" fill="#FFB020" />
    </svg>
  );
}

export function EggRollArt({ size = 54 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3" y="9" width="18" height="7" rx="3.5" fill="#FFD04D" />
      <path d="M7 9v7M11 9v7M15 9v7" stroke="#F0A51C" strokeWidth="1.2" />
    </svg>
  );
}

export function CrownArt() {
  return (
    <svg width="28" height="20" viewBox="0 0 28 20" aria-hidden="true">
      <path d="M2 18l3-14 6 7 3-9 3 9 6-7 3 14z" fill="#D9B85C" stroke="#B8934A" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

export function MascotArt({ size = 116 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden="true">
      <ellipse cx="60" cy="110" rx="32" ry="5" fill="#C2650F" opacity=".1" />
      <path d="M60 42c22 0 36 16 36 35s-14 29-36 29-36-10-36-29 14-35 36-35z" fill="#fff" stroke="#C2650F" strokeWidth="3" />
      <path d="M38 46a12 12 0 0 1 7-21 16 16 0 0 1 30 0 12 12 0 0 1 7 21z" fill="#fff" stroke="#C2650F" strokeWidth="3" strokeLinejoin="round" />
      <rect x="39" y="41" width="42" height="11" rx="5.5" fill="#F2A868" stroke="#C2650F" strokeWidth="3" />
      <circle cx="50" cy="75" r="4" fill="#1B2215" />
      <circle cx="70" cy="75" r="4" fill="#1B2215" />
      <ellipse cx="42" cy="85" rx="6" ry="3.5" fill="#FFB7A3" />
      <ellipse cx="78" cy="85" rx="6" ry="3.5" fill="#FFB7A3" />
      <path d="M55 85q5 5 10 0" stroke="#1B2215" strokeWidth="3" fill="none" strokeLinecap="round" />
    </svg>
  );
}
