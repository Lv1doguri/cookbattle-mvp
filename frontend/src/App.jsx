import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { useApp } from './state/AppContext';
import DevNav from './components/DevNav';

import Login from './screens/Login';
import Signup from './screens/Signup';
import Onboarding from './screens/Onboarding';
import Home from './screens/Home';
import Recipes from './screens/Recipes';
import Filter from './screens/Filter';
import RecipeDetail from './screens/RecipeDetail';
import Battle from './screens/Battle';
import CookVerifyCamera from './screens/CookVerifyCamera';
import CookVerify from './screens/CookVerify';
import JoinDone from './screens/JoinDone';
import Vote from './screens/Vote';
import BattleResult from './screens/BattleResult';
import Shop from './screens/Shop';
import Menu from './screens/Menu';
import ProfileEdit from './screens/ProfileEdit';
import Offline from './screens/Offline';

function RequireAuth() {
  const { loggedIn, online } = useApp();
  const location = useLocation();
  if (!loggedIn) return <Navigate to="/" replace state={{ from: location }} />;
  if (!online) return <Offline />;
  return <Outlet />;
}

export default function App() {
  const { booting } = useApp();
  if (booting) return null; // restoring a saved login before deciding what to render

  return (
    <>
      {import.meta.env.DEV && <DevNav />}
      <div className="stage">
        <div className="phone">
          <Routes>
            <Route path="/" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/offline" element={<Offline />} />

            <Route element={<RequireAuth />}>
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/home" element={<Home />} />
              <Route path="/recipes" element={<Recipes />} />
              <Route path="/recipes/filter" element={<Filter />} />
              <Route path="/recipes/:id" element={<RecipeDetail />} />
              <Route path="/battle" element={<Battle />} />
              <Route path="/battle/camera" element={<CookVerifyCamera />} />
              <Route path="/battle/verify" element={<CookVerify />} />
              <Route path="/battle/done" element={<JoinDone />} />
              <Route path="/battle/vote" element={<Vote />} />
              <Route path="/battle/result" element={<BattleResult />} />
              <Route path="/shop" element={<Shop />} />
              <Route path="/menu" element={<Menu />} />
              <Route path="/profile/edit" element={<ProfileEdit />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </>
  );
}
