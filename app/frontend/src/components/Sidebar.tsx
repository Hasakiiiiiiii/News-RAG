"use client";
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, Search, MessageSquare, 
  Newspaper, Activity, Settings, 
  TerminalSquare, ShieldCheck
} from 'lucide-react';

const MENU_ITEMS = [
  { name: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { name: 'Semantic Search', icon: Search, href: '/dashboard/search' },
  { name: 'AI Chat', icon: MessageSquare, href: '/dashboard/chat' },
  { name: 'Article Explorer', icon: Newspaper, href: '/dashboard/article' },
  { name: 'Pipeline Monitor', icon: Activity, href: '/dashboard/monitor' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 bg-[#0f172a] h-full flex flex-col p-4 border-r border-slate-800 font-sans">
      {/* Logo */}
      <div className="flex items-center gap-3 px-2 mb-8 text-white mt-2">
        <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <TerminalSquare size={20} className="text-white" />
        </div>
        <span className="text-xl font-bold tracking-wide">News RAG</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1.5">
        {MENU_ITEMS.map((item) => {
          const isActive = pathname === item.href || (item.href === '/dashboard' && pathname === '/');
          return (
            <Link 
              key={item.href} 
              href={item.href} 
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
                isActive 
                  ? 'bg-[#3730a3] text-white shadow-md' // Màu tím đậm của item active
                  : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
              }`}
            >
              <item.icon size={20} strokeWidth={isActive ? 2.5 : 2} />
              <span className="text-sm font-semibold">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* System Status & User Profile */}
      <div className="mt-auto flex flex-col gap-4">
        <div className="border-t border-slate-700/50 pt-4 px-2 space-y-3">
          <div className="flex items-center gap-2 text-slate-300">
            <ShieldCheck size={16} className="text-emerald-500" />
            <span className="text-xs font-semibold">System Status</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
            <span className="text-xs font-medium text-slate-400">All systems operational</span>
          </div>
        </div>

        <div className="border-t border-slate-700/50 pt-4 flex items-center gap-3 px-2 pb-2">
          <img 
            src="https://ui-avatars.com/api/?name=Tien+San&background=f1f5f9&color=0f172a&bold=true" 
            className="w-10 h-10 rounded-full border-2 border-slate-600" 
            alt="Tien San" 
          />
          <div className="overflow-hidden">
            <p className="text-sm font-bold text-white tracking-wide">Tien_sann</p>
            <p className="text-[11px] text-slate-400 font-medium">Developer</p>
          </div>
        </div>
      </div>
    </div>
  );
}