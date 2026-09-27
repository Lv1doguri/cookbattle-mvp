# 요리왕 — frontend

React + Vite implementation of the 요리왕 Figma prototype (19 screens → 16 routes; the shop
confirm sheet and "교환 완료" dialog are overlays inside `/shop` instead of separate pages).

## Run

```bash
npm install
npm run dev      # http://localhost:5173 — dark bar on top jumps between screens (dev only)
npm run build    # production build in dist/
```

The camera screen needs `localhost` or HTTPS (browser rule for `getUserMedia`). To test on a
phone on the same Wi-Fi, run `npm run dev -- --host` and open it over HTTPS (e.g. via a tunnel),
or the screen falls back to a placeholder frame.

## Structure

```
src/
  main.jsx               router + global state provider
  App.jsx                routes, auth guard, offline screen switch
  state/AppContext.jsx   all client state + actions (login, submitEntry, vote, redeem, ...)
  data/mock.js           recipes, battles, shop items, onboarding copy  ← replace with API
  components/
    Icon.jsx             every icon from the prototype, <Icon name="..." />
    Screen.jsx           Screen, Header, TopBar, IconButton, BottomAction
    TabBar.jsx           bottom tabs (NavLink, filled icon when active)
    ui.jsx               Button, Field, Chip, Segmented, Avatar, Badge, PointPill, ...
    DevNav.jsx           screen jumper for design reviews
  screens/               one file per screen
  styles/
    global.css           design tokens (colors, radii, shadows) + primitives
    screens.css          per-screen styles
```

## Routes

| Route | Screen |
|---|---|
| `/` | 01 로그인 |
| `/signup` | 02 회원가입 |
| `/onboarding` | 07 앱 사용법 (4 steps) |
| `/home` | 03 홈 |
| `/recipes` | 04 레시피 목록 |
| `/recipes/filter` | 05 필터 |
| `/recipes/:id` | 09 레시피 상세 |
| `/battle` | 06 대결 홈 |
| `/battle/camera` | 12 사진 촬영 (in-app camera only) |
| `/battle/verify` | 12b 요리 인증 |
| `/battle/done` | 13 참가 완료 |
| `/battle/vote` | 14 투표 |
| `/battle/result` | 15 대결 결과 |
| `/shop` | 16 상점 + 17 교환 확인 (sheet) + 18 교환 완료 (dialog) |
| `/menu` | 10 메뉴 |
| `/profile/edit` | 08 정보 수정 |
| `/offline` | 11 연결 오류 (also shown automatically when the browser goes offline) |

## What works

- Login / signup validation (8+ char password, duplicate nickname check — try `자취생`)
- Skill level picked at signup decides your battle group; changeable in 정보 수정
- Recipe search (name, category, ingredient), quick chips, sort toggle, bookmarks, comments
- Filter screen: multi-select chips, live result count, reset
- Battle: view all three groups, join only your own; one entry per battle; +1P on submit
- Camera: live preview, front/back switch, torch where supported, square capture
- Vote: one vote per battle, can't vote for your own entry
- Shop: level locks, "N P 더 필요해요", confirm sheet, points deducted on exchange

## Next steps for the backend

Every action in `AppContext.jsx` is where an API call goes. State is in memory, so a refresh
logs you out — swap in real auth (or persist to `localStorage`) when the API is ready.
