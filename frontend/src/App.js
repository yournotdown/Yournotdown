import { BrowserRouter, Navigate, Routes, Route, useLocation, useParams } from "react-router-dom";
import { Toaster } from "sonner";
import HomePage from "./pages/HomePage";
import VibePage from "./pages/VibePage";
import TonightPage from "./pages/TonightPage";
import CategoriesPage from "./pages/CategoriesPage";
import CategoryDetailPage from "./pages/CategoryDetailPage";
import AdminLoginPage from "./pages/AdminLoginPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminBusinessAnalyticsPage from "./pages/AdminBusinessAnalyticsPage";
import AuthCallback from "./pages/AuthCallback";
import { cityPath, DEFAULT_CITY_SLUG } from "./lib/cities";
import "@/index.css";

// build marker: force production frontend rebuild
function NashvilleRedirect({ path = "" }) {
  const location = useLocation();
  return <Navigate to={`${cityPath(DEFAULT_CITY_SLUG, path)}${location.search}`} replace />;
}

function NashvilleCategoryRedirect() {
  const { slug } = useParams();
  return <NashvilleRedirect path={`c/${slug}`} />;
}

function AppRouter() {
  const location = useLocation();
  // Per Emergent Auth playbook: detect session_id in URL fragment synchronously during render
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/admin/login" element={<AdminLoginPage />} />
      <Route path="/admin" element={<AdminDashboardPage />} />
      <Route path="/admin/business/:id" element={<AdminBusinessAnalyticsPage />} />
      <Route path="/" element={<NashvilleRedirect />} />
      <Route path="/vibe" element={<NashvilleRedirect path="vibe" />} />
      <Route path="/tonight" element={<NashvilleRedirect path="tonight" />} />
      <Route path="/categories" element={<NashvilleRedirect path="categories" />} />
      <Route path="/c/:slug" element={<NashvilleCategoryRedirect />} />
      <Route path="/:citySlug" element={<HomePage />} />
      <Route path="/:citySlug/vibe" element={<VibePage />} />
      <Route path="/:citySlug/tonight" element={<TonightPage />} />
      <Route path="/:citySlug/categories" element={<CategoriesPage />} />
      <Route path="/:citySlug/c/:slug" element={<CategoryDetailPage />} />
      <Route path="*" element={<NashvilleRedirect />} />
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
