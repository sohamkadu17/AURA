"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { MessageSquare, FileText, CheckSquare, LogOut, Sparkles } from "lucide-react";
import toast from "react-hot-toast";
import { useEffect } from "react";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/tasks", label: "Tasks", icon: CheckSquare },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (!token) {
        router.push("/login");
      }
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    toast.success("Logged out");
    router.push("/login");
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 glass-panel border-r border-white/5 flex flex-col h-full shrink-0 relative z-20">
        <div className="p-6 flex items-center space-x-3 border-b border-white/5">
          <div className="p-2 bg-primary/20 rounded-xl">
            <Sparkles className="w-6 h-6 text-primary" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">AURA</span>
        </div>

        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${
                  isActive
                    ? "bg-primary/20 text-primary font-medium"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? "text-primary" : "text-gray-500"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/5">
          <button
            onClick={handleLogout}
            className="flex items-center space-x-3 px-4 py-3 w-full rounded-xl text-gray-400 hover:text-red-400 hover:bg-red-400/10 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 relative overflow-hidden flex flex-col">
        {/* Decorative background blur */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[100px] pointer-events-none z-0" />
        <div className="relative z-10 w-full h-full flex flex-col">{children}</div>
      </main>
    </div>
  );
}
