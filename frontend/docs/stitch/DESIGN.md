---
name: CookMatch Sensory Studio
colors:
  surface: '#fff8f6'
  surface-dim: '#e5d7d2'
  surface-bright: '#fff8f6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fff1ec'
  surface-container: '#f9ebe6'
  surface-container-high: '#f3e5e0'
  surface-container-highest: '#ede0db'
  on-surface: '#211a17'
  on-surface-variant: '#5b4039'
  inverse-surface: '#362f2c'
  inverse-on-surface: '#fceee9'
  outline: '#907067'
  outline-variant: '#e4beb4'
  surface-tint: '#b02f00'
  primary: '#b02f00'
  on-primary: '#ffffff'
  primary-container: '#ff5722'
  on-primary-container: '#541200'
  inverse-primary: '#ffb5a0'
  secondary: '#735c00'
  on-secondary: '#ffffff'
  secondary-container: '#fdd34d'
  on-secondary-container: '#725b00'
  tertiary: '#006e1c'
  on-tertiary: '#ffffff'
  tertiary-container: '#41a447'
  on-tertiary-container: '#003208'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbd1'
  primary-fixed-dim: '#ffb5a0'
  on-primary-fixed: '#3b0900'
  on-primary-fixed-variant: '#862200'
  secondary-fixed: '#ffe087'
  secondary-fixed-dim: '#ebc23e'
  on-secondary-fixed: '#241a00'
  on-secondary-fixed-variant: '#574500'
  tertiary-fixed: '#94f990'
  tertiary-fixed-dim: '#78dc77'
  on-tertiary-fixed: '#002204'
  on-tertiary-fixed-variant: '#005313'
  background: '#fff8f6'
  on-background: '#211a17'
  surface-variant: '#ede0db'
typography:
  headline-display:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 44px
  headline-display-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '800'
    lineHeight: 36px
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 30px
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 28px
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
  body-lg:
    fontFamily: Noto Sans
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
  body-md:
    fontFamily: Noto Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Noto Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '700'
    lineHeight: 20px
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 14px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-sm: 0.75rem
  margin: 1rem
  margin-lg: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style
The design system embodies the warmth, vitality, and lively camaraderie of solo living and everyday home cooking. Rather than feeling sterile or overly gourmet, the visual tone captures the hearty sizzle of a pan, the playful spirit of daily kitchen showdowns, and the inviting aroma of a freshly plated meal. 

Combining **Tactile Soft Modernism** with an energetic **Appetite-Driven Visual Style**, the interface prioritizes high-contrast photography, rounded surfaces, and comforting tactile depth. The visual tension balances playful gamification (real-time countdowns, live recipe duels, voting stamps) with clean editorial restraint, ensuring user-generated dish photos remain the heroic focal point. The emotional response is immediate: comforting, delightfully appetizing, accessible, and intensely community-oriented.

## Colors
The color architecture stimulates appetite and engagement through sun-drenched, culinary-inspired tones:

- **Primary (Terracotta / Flame Orange - `#FF5722` & `#FF7043`):** Evokes stovetop flames, rich gochujang and roasted tomato sauces, and high-energy culinary duels. Reserved for key calls to action, voting interactions, active duel timers, and triumphant celebratory badges.
- **Secondary (Butter Yellow - `#FFD54F` with cream highlights `#FFF8E1`):** Represents melted butter, golden fried eggs, and comforting carbohydrates. Employed for secondary banners, highlight chips, voting percentages, and warmth-focused micro-interactions.
- **Tertiary (Fresh Herb Green - `#4CAF50`):** Inspired by scallions, microgreens, and crisp culinary garnishes. Utilized for freshness indicators, budget-saver tags, successful cook steps, and active cooking availability cues.
- **Base & Neutral (Crisp Charcoal - `#2B2421` & Cream Milk Canvas - `#FAF8F5` / `#FFFFFF`):** Eliminates harsh blue-black grays in favor of deep roasted espresso for high-legibility typography, laid over a comforting, warm-white ceramic foundation (`#FAF8F5`).

Color contrasts rigorously respect accessibility, ensuring text on primary orange and herb green remains readable with crisp white counters or dark charcoal overlays.

## Typography
Typography is paired to provide optimal Korean and alphanumeric rhythm. **Plus Jakarta Sans** delivers a friendly, energetic geometric structure with generous counters for headings, battle metrics, vote tallies, and punchy culinary labels. **Noto Sans** ensures immaculate legibility across body text, recipe steps, cost estimations, and community comment threads.

- **Numerals & Battle Stakes:** Metrics, vote shares, and countdown clocks use tabular, bold weight pairings to eliminate layout jitter during live voting cycles.
- **Micro-Copy & Badges:** Labels leverage tight tracking and uppercase styling for English pairings, while Korean equivalents maintain balanced, comfortable spacing for readability on compact mobile viewports.

## Layout & Spacing
The layout model is driven by an 8pt spatial grid designed specifically for vertical mobile scrolling and touch ergonomical zones:

- **Mobile Viewport Structure:** Uses a single-column fluid shell with `16px` (`margin`) outer edge breathing room, allowing food imagery to extend flush (full-bleed) when highlighting live match headers, or safely inset within rounded ceramic cards.
- **Duel Layout Rhythm:** Head-to-head battle cards divide into a 2-column comparison matrix using `gutter-sm` (12px), keeping contestant cards side-by-side without visual cramping.
- **Thumb Zone Hierarchy:** High-frequency actions (voting triggers, battle commentary, match submissions) are pinned to a lower 64px floating action zone, clearing horizontal swiping gestures and screen edges.

## Elevation & Depth
Depth mimics physical tableware arranged on a clean kitchen tabletop, blending soft ambient warmth with crisp tactile layers:

- **Surface Tiers:**
  - Base: Warm Ceramic Tint (`#FAF8F5`).
  - Elevated Container / Recipe Cards: Pure Porcelain White (`#FFFFFF`).
  - Active Duel Overlays & Modal Drawers: Butter Cream Tint (`#FFF8E1`).
- **Warm Ambient Shadows:** Casts diffuse, non-muddy shadows tinted with 4% to 8% warm terracotta amber (`rgba(43, 36, 33, 0.08)`) instead of synthetic cold gray.
- **Micro-Depression & Press States:** Tapping a card or vote button depresses the element down by 2px with an inner warm glow, simulating a tactile button or stamp press.

## Shapes
Surfaces adopt a generous roundedness scale (`roundedness: 2` with 16px base corners and 24px outer containers), referencing ceramic cookware, round bowls, and cast iron pans. 

- **Dish Cards & Banners:** Feature `rounded-xl` (24px) corners to provide an organic, non-industrial framing for culinary photos.
- **Interactive Badges & Vote Pills:** Employ pill-shaped full radiuses (9999px) to convey softness, safety, and tap-friendly accessibility.
- **Image Masking:** Recipe images are clipped cleanly with matched continuous curves, preventing jagged photographic corners from interrupting the interface flow.

## Components

- **Battle Duel Card (Versus Card):** Split card design showcasing contestant photos side by side with an embedded central "VS" badge in Butter Yellow (`#FFD54F`). Features real-time animated percentage bars beneath each dish that expand as votes lock in.
- **Vote & Action Buttons:**
  - *Primary Vote Button:* Pill-shaped, Flame Orange (`#FF5722`) with bold white typography, generating a warm ripple and gentle haptic feedback on press.
  - *Secondary Support Button:* Soft Cream (`#FFF8E1`) surface with Flame Orange border and text.
- **Culinary Timer Pill:** High-contrast countdown chip containing an animated flame or kettle icon, styled in deep charcoal with vibrant orange digits, communicating battle urgency.
- **Ingredient & Cost Chips:** Compact tags indicating recipe price-per-portion (e.g., "₩3,500 컷", "냉장고 파먹기"), set in Herb Green tint (`#E8F5E9`) with crisp green text (`#2E7D32`).
- **Input Fields & Kitchen Review Box:** Enclosed within warm white backgrounds with a subtle 1px border (`#EFEBE6`). On active focus, the border shifts to Terracotta Orange with an ethereal 3px warm butter bloom.
- **Chef Level & Badges:** Circular and shield emblems crowned with playful culinary icons (Frying Pan Novice, Single-Burner Maestro), embellished with golden butter highlights and soft edge embossments.