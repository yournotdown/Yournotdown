import { motion } from "framer-motion";
import { LogIn } from "lucide-react";

export default function AdminLoginPage() {
  const handleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/admin";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-6 relative overflow-hidden" data-testid="admin-login-page">
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-[#C6FF00]/15 blur-[160px]" />

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md text-center bg-[#121218] border border-white/10 rounded-[32px] p-10"
      >
        <h1 className="font-display font-black text-white text-4xl sm:text-5xl tracking-tight">
          Admin
        </h1>
        <p className="mt-3 text-[#A1A1AA] text-base">
          Sign in with Google to manage the city.
        </p>

        <motion.button
          onClick={handleLogin}
          whileTap={{ scale: 0.96 }}
          whileHover={{ scale: 1.02 }}
          className="mt-8 w-full py-4 bg-[#C6FF00] hover:bg-[#A8E000] text-white font-bold rounded-full glow-lime flex items-center justify-center gap-3 transition-colors"
          data-testid="admin-login-google-button"
        >
          <LogIn className="w-5 h-5" />
          Sign in with Google
        </motion.button>
      </motion.div>
    </div>
  );
}
