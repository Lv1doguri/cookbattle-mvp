import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import RequireAuth from "./components/RequireAuth";
import { AuthProvider } from "./context/AuthContext";
import Login from "./pages/Login";
import Results from "./pages/Results";
import Signup from "./pages/Signup";
import TodayTopics from "./pages/TodayTopics";
import TopicDetail from "./pages/TopicDetail";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <TodayTopics />
              </RequireAuth>
            }
          />
          <Route
            path="/topics/:id"
            element={
              <RequireAuth>
                <TopicDetail />
              </RequireAuth>
            }
          />
          <Route
            path="/topics/:id/results"
            element={
              <RequireAuth>
                <Results />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
