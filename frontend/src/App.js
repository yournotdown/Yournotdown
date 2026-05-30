import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import HomePage from "./pages/HomePage";
import VibePage from "./pages/VibePage";
import CategoriesPage from "./pages/CategoriesPage";
import CategoryDetailPage from "./pages/CategoryDetailPage";
import AdminLoginPage from "./pages/AdminLoginPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminBusinessAnalyticsPage from "./pages/AdminBusinessAnalyticsPage";
import AuthCallback from "./pages/AuthCallback";
import "@/index.css";

function AppRouter() {
  const location = useLocation();
  // Per Emergent Auth playbook: detect session_id in URL fragment synchronously during render
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/vibe" element={<VibePage />} />
      <Route path="/categories" element={<CategoriesPage />} />
      <Route path="/c/:slug" element={<CategoryDetailPage />} />
      <Route path="/admin/login" element={<AdminLoginPage />} />
      <Route path="/admin" element={<AdminDashboardPage />} />
      <Route path="/admin/business/:id" element={<AdminBusinessAnalyticsPage />} />
      <Route path="*" element={<HomePage />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans">
      <BrowserRouter>
        <AppRouter />
        <Toaster theme="dark" position="top-center" richColors />
      </BrowserRouter>
    </div>
  );
}

export default App;
