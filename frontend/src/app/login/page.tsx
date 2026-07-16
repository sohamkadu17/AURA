"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, ArrowRight } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);

      const response = await api.post("/auth/token", params, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      localStorage.setItem("token", response.data.access_token);
      toast.success("Successfully logged in!");
      router.push("/chat");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to login. Check your credentials.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass-panel w-full max-w-md p-8 rounded-2xl relative overflow-hidden">
        {/* Glow effect */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 bg-primary/20 blur-[60px] rounded-full pointer-events-none" />

        <div className="relative z-10">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
              Welcome back
            </h1>
            <p className="text-gray-400 mt-2 text-sm">
              Enter your credentials to access AURA
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Username</label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="Student ID or Handle"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary hover:bg-primary-hover text-white rounded-xl px-4 py-3 font-medium flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  Sign In
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-400">
            Don't have an account?{" "}
            <Link href="/register" className="text-primary hover:text-primary-hover font-medium transition-colors">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
