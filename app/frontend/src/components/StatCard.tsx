import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string;
  subValue?: string;
  subText?: string;
  icon: LucideIcon;
  colorClass: string;
  bgClass: string;
  trendTextClass?: string;
}

export default function StatCard({ 
  title, value, subValue, subText, icon: Icon, colorClass, bgClass, trendTextClass = "text-emerald-500"
}: StatCardProps) {
  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-start gap-4">
      <div className={`p-3 rounded-xl ${bgClass} ${colorClass}`}>
        <Icon size={24} strokeWidth={2} />
      </div>
      <div className="space-y-1">
        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">{title}</p>
        <h3 className="text-2xl font-black text-slate-800">{value}</h3>
        {subValue && (
          <p className="text-[11px] font-bold">
            <span className={trendTextClass}>{subValue}</span>
            {subText && <span className="text-slate-400 ml-1">{subText}</span>}
          </p>
        )}
      </div>
    </div>
  );
}