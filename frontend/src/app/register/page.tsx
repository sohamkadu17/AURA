"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, ArrowRight } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    
    setIsLoading(true);

    try {
      const response = await api.post("/auth/register", {
        username,
        password,
      });

      localStorage.setItem("token", response.data.access_token);
      toast.success("Account created successfully!");
      router.push("/chat");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Registration failed. Try a different username.");
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
              Create Account
            </h1>
            <p className="text-gray-400 mt-2 text-sm">
              Join AURA to start using your AI assistant
            </p>
          </div>

          <form onSubmit={handleRegister} className="space-y-5">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Username</label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="Choose a username"
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
                placeholder="Create a strong password"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Confirm Password</label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="Repeat password"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary hover:bg-primary-hover text-white rounded-xl px-4 py-3 font-medium flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed group mt-2"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  Sign Up
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-400">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:text-primary-hover font-medium transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
