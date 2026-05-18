"use client";
import React, { useEffect, useState } from 'react';
import { Activity, Database, Server, Zap, CheckCircle2, AlertCircle, Clock, GitBranch, Table } from 'lucide-react';

export default function PipelineMonitor() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('http://localhost:8000/pipeline/status');
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error("Fetch monitor error:", err);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!data) return <div className="p-8">Đang tải dữ liệu giám sát...</div>;

  return (
    <div className="p-8 bg-[#f8fafc] min-h-screen space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <Activity className="text-indigo-600" /> System Monitoring
        </h1>
        <div className="flex gap-2">
          <span className="flex items-center gap-1 text-xs font-bold bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full">
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div> SYSTEM LIVE
          </span>
        </div>
      </div>

      {/* Dãy Card trạng thái dịch vụ */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Object.entries(data.services).map(([key, value]: any) => (
          <div key={key} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{key}</p>
              <p className="text-sm font-bold text-slate-700 capitalize">{value}</p>
            </div>
            <CheckCircle2 size={20} className="text-emerald-500" />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* DATABASE SCHEMA */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <h3 className="font-bold text-slate-700 mb-6 flex items-center gap-2">
            <Table size={18} className="text-indigo-600" /> Database Schema (Live)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
            {data.db_schema?.map((table: any) => (
              <div key={table.table_name} className="border border-slate-100 rounded-xl overflow-hidden shadow-sm">
                <div className="bg-slate-50 px-3 py-2 border-b border-slate-100 flex items-center justify-between">
                  <span className="text-xs font-bold text-indigo-700">{table.table_name}</span>
                  <Database size={12} className="text-slate-400" />
                </div>
                <div className="p-2 space-y-1">
                  {table.columns.map((col: any) => (
                    <div key={col.name} className="flex justify-between items-center text-[10px]">
                      <span className="text-slate-600 font-medium">{col.name}</span>
                      <span className="text-slate-300 italic">{col.type}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ETL PIPELINE (PENTAHO LOGIC) */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <h3 className="font-bold text-slate-700 mb-6 flex items-center gap-2">
            <GitBranch size={18} className="text-indigo-600" /> ETL Pipeline (Pentaho Flow)
          </h3>
          <div className="space-y-4 relative">
            {data.pipeline_steps?.map((step: any, idx: number) => (
              <div key={step.id} className="flex items-center gap-4 relative">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shadow-sm z-10 ${
                  step.type === 'config' ? 'bg-orange-100 text-orange-600 border border-orange-200' :
                  step.type === 'db' ? 'bg-blue-100 text-blue-600 border border-blue-200' :
                  step.type === 'transform' ? 'bg-purple-100 text-purple-600 border border-purple-200' :
                  'bg-emerald-100 text-emerald-600 border border-emerald-200'
                }`}>
                  {idx + 1}
                </div>
                <div className="flex-1 bg-slate-50 px-4 py-2 rounded-lg border border-slate-100">
                  <span className="text-sm font-bold text-slate-700">{step.name}</span>
                  <span className="ml-3 text-[10px] text-slate-400 font-medium uppercase tracking-tighter">[{step.type}]</span>
                </div>
                {idx < data.pipeline_steps.length - 1 && (
                  <div className="absolute left-4 top-8 w-0.5 h-4 bg-slate-100 -ml-[1px]"></div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sơ đồ Ingestion Flow */}
      <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
        <h3 className="font-bold text-slate-700 mb-8 flex items-center gap-2">
          <Server size={18} /> Data Ingestion Flow
        </h3>
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 relative">
          {data.components.map((comp: any, idx: number) => (
            <React.Fragment key={idx}>
              <div className="flex flex-col items-center z-10">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg transition-all ${
                  comp.status === 'active' ? 'bg-indigo-600 text-white scale-105' : 'bg-slate-100 text-slate-400'
                }`}>
                  {idx === 0 && <Zap size={20} />}
                  {idx === 1 && <Clock size={20} />}
                  {idx === 2 && <Database size={20} />}
                  {idx === 3 && <Activity size={20} />}
                </div>
                <p className="mt-3 font-bold text-slate-700 text-xs">{comp.name}</p>
                <p className="text-[9px] text-slate-400 font-medium uppercase">{comp.status}</p>
                <p className="text-[10px] font-bold text-indigo-600 mt-0.5">{comp.processed} items</p>
              </div>
              {idx < data.components.length - 1 && (
                <div className="hidden md:block flex-1 h-[2px] bg-slate-100"></div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}
  );
}