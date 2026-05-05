"use client";
import React, { useState, useEffect } from 'react';
import { 
  RefreshCw, FileText, Globe, Clock, Box,
  TrendingUp, PieChart as PieIcon, Users, Tag, Activity, Server, Database
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import StatCard from '../../components/StatCard';


export default function DashboardPage() {
  // --- STATE LƯU DỮ LIỆU THẬT ---
  const [stats, setStats] = useState({ 
    total_articles: 0, 
    total_sources: 0, 
    total_vectors: 0,
    top_authors: [] as any[],
    source_distribution: [] as any[], // Thêm mảng này
    trend_data: [] as any[], // Thêm mảng này
    latest_articles: [] as any[] // Dành cho phần bài viết mới nhất ở dưới (nếu có)
  });

  // Mảng màu sắc tự động (Hỗ trợ tối đa 6 đầu báo, nếu có nhiều báo hơn nó sẽ quay vòng lại)
  const COLORS = ['#3b82f6', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4'];
  
  const [isRefreshing, setIsRefreshing] = useState(false);

  // --- HÀM GỌI API THẬT ---
  const fetchStats = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch('http://localhost:8000/stats');
      if (res.ok) {
        const data = await res.json();
        setStats({
          total_articles: data.total_articles || 0,
          total_sources: data.total_sources || 0,
          total_vectors: data.total_vectors || 0,
          top_authors: data.top_authors || [],
          source_distribution: (data.source_distribution || []).map((item: any, idx: number) => ({
            ...item,
            color: COLORS[idx % COLORS.length]
          })),
          trend_data: data.trend_data || [], // <-- Đổ data vào State
          latest_articles: data.latest_articles || [] // <-- Thêm dòng này
        });
      }
    } catch (error) {
      console.error("Lỗi fetch stats:", error);
    } finally {
      setTimeout(() => setIsRefreshing(false), 500);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div className="p-6 md:p-8 space-y-6 bg-[#f8fafc] min-h-screen">
      {/* HEADER */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <span className="text-indigo-600">1. DASHBOARD</span> 
          <span className="text-slate-500 font-medium text-lg">(Tổng quan hệ thống)</span>
        </h1>
        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium bg-white px-3 py-1.5 rounded-full border border-slate-200 shadow-sm">
          <span>Live Data</span>
          <RefreshCw 
            size={14} 
            className={`cursor-pointer hover:text-indigo-600 text-indigo-500 ${isRefreshing ? 'animate-spin' : ''}`} 
            onClick={fetchStats}
          />
        </div>
      </div>

      {/* 1. KPI CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard 
          title="Total Articles" 
          value={stats.total_articles.toLocaleString()} 
          subValue="PostgreSQL" 
          subText="" 
          icon={FileText} 
          colorClass="text-indigo-500" 
          bgClass="bg-indigo-50" 
          trendTextClass="text-indigo-600 font-semibold"
        />
        <StatCard 
          title="Total Vectors" 
          value={stats.total_vectors.toLocaleString()} 
          subValue="Qdrant Cloud" 
          subText="" 
          icon={Box} 
          colorClass="text-purple-500" 
          bgClass="bg-purple-50" 
          trendTextClass="text-purple-600 font-semibold"
        />
        {/* <StatCard 
          title="Total Domains" 
          value={stats.total_sources.toLocaleString()} 
          subValue="Nguồn báo" 
          subText="" 
          icon={Globe} 
          colorClass="text-blue-500" 
          bgClass="bg-blue-50" 
          trendTextClass="text-blue-600 font-semibold" 
        /> */}
        <StatCard 
          title="Data Warehouse" 
          value="Ready" 
          subValue="Star Schema" 
          subText="" 
          icon={Database} 
          colorClass="text-emerald-500" 
          bgClass="bg-emerald-50" 
          trendTextClass="text-emerald-600 font-semibold"
        />
        <StatCard 
          title="Latest Crawl" 
          value="5 mins ago" 
          subValue="Hệ thống ổn định" 
          subText="" 
          icon={Clock} 
          colorClass="text-orange-500" 
          bgClass="bg-orange-50" 
          trendTextClass="text-orange-600 font-semibold" 
        />
      </div>

      {/* 2. MIDDLE CHARTS */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Line Chart (ĐÃ NỐI API THẬT) */}
        <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
          <h3 className="font-bold text-slate-700 flex items-center gap-2 mb-4"><TrendingUp size={18} className="text-indigo-500" /> Số bài viết theo ngày</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              {/* Thay lineData bằng stats.trend_data */}
              <LineChart data={stats.trend_data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
                <YAxis tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                <Line type="monotone" dataKey="count" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4, fill: '#4f46e5', strokeWidth: 2, stroke: '#fff' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie Chart (ĐÃ NỐI API THẬT) */}
        <div className="lg:col-span-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col hover:shadow-md transition-shadow">
          <h3 className="font-bold text-slate-700 flex items-center gap-2 mb-4"><PieIcon size={18} className="text-blue-500"/> Phân bổ theo nguồn</h3>
          <div className="flex-1 flex items-center justify-center relative">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={stats.source_distribution} innerRadius={60} outerRadius={80} paddingAngle={2} dataKey="value">
                  {stats.source_distribution.map((entry, index) => ( 
                    <Cell key={`cell-${index}`} fill={entry.color} /> 
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
              <span className="text-[10px] text-slate-400 font-bold uppercase">Total</span><br/>
              <span className="text-lg font-black text-slate-700">{stats.total_articles.toLocaleString()}</span>
            </div>
          </div>
          {/* Chú thích màu (Legend) lấy từ data thật */}
          <div className="space-y-2 mt-4 max-h-24 overflow-y-auto pr-1">
            {stats.source_distribution.map(item => (
              <div key={item.name} className="flex justify-between items-center text-xs font-semibold">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: item.color }}></div>
                  <span className="text-slate-600 truncate max-w-[120px]" title={item.name}>{item.name}</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-slate-500 font-medium">{item.value.toLocaleString()}</span>
                  <span className="text-slate-400 w-10 text-right">{item.percent}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bar Chart (Top Authors - ĐÃ NỐI API THẬT) */}
        <div className="lg:col-span-3 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col hover:shadow-md transition-shadow">
          <h3 className="font-bold text-slate-700 flex items-center gap-2 mb-6"><Users size={18} className="text-emerald-500" /> Top tác giả </h3>
          <div className="space-y-4 flex-1">
            {stats.top_authors.length > 0 ? (
              stats.top_authors.map((author, index) => (
                <div key={index} className="flex items-center justify-between gap-3">
                  <span className="text-xs font-bold text-slate-700 w-24 truncate" title={author.name}>{author.name}</span>
                  <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full transition-all duration-1000" style={{ width: `${author.percent}%` }}></div>
                  </div>
                  <span className="text-xs font-bold text-slate-400 w-8 text-right">{author.count}</span>
                </div>
              ))
            ) : (
              <div className="text-center text-sm text-slate-400 mt-10">Đang tải dữ liệu...</div>
            )}
          </div>
        </div>
      </div>

      {/* 3. BOTTOM SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Widget: Bài báo mới cập nhật (Có thanh cuộn) */}
        <div className="lg:col-span-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex flex-col">
          <h3 className="font-bold text-slate-700 flex items-center gap-2 mb-4">
            <FileText size={18} className="text-orange-500" /> Vừa cập nhật
          </h3>
          
          {/* Thêm max-h-[210px] và overflow-y-auto để tạo thanh cuộn */}
          <div className="flex-1 overflow-y-auto max-h-[210px] pr-2 space-y-4">
            {stats.latest_articles && stats.latest_articles.length > 0 ? (
              stats.latest_articles.map((article, idx) => (
                <div key={idx} className="flex flex-col gap-1 pb-3 border-b border-slate-50 last:border-0 last:pb-0">
                  <p className="text-[13px] font-semibold text-slate-700 leading-tight line-clamp-2" title={article.title}>
                    {article.title}
                  </p>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 font-medium">
                    <span className="uppercase text-orange-500/80">{article.source}</span>
                    <span>{article.date}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center text-sm text-slate-400 mt-10">Đang tải dữ liệu...</div>
            )}
          </div>
        </div>
        
        {/* Activity */}
        <div className="lg:col-span-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
          <h3 className="font-bold text-slate-700 flex items-center gap-2 mb-4"><Activity size={18} className="text-rose-500" /> Hoạt động gần đây</h3>
          <ul className="space-y-4">
            {[
              { text: 'Crawl hoàn thành (vnexpress.net)', time: '5 mins ago' },
              { text: 'ETL nạp Warehouse thành công', time: '8 mins ago' },
              { text: 'Vectorize: Push lên Qdrant', time: '10 mins ago' },
              { text: 'Làm sạch dữ liệu Text', time: '18 mins ago' }
            ].map((item, idx) => (
              <li key={idx} className="flex justify-between items-center text-xs">
                <div className="flex items-center gap-2 text-slate-600 font-medium">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-500"></div>
                  {item.text}
                </div>
                <span className="text-slate-400">{item.time}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* System Stats Table */}
        <div className="lg:col-span-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
          <h3 className="font-bold text-slate-700 flex items-center gap-2 mb-4"><Server size={18} className="text-slate-500"/> Thống kê hệ thống</h3>
          <div className="space-y-3">
            {[
              { label: 'PostgreSQL (Metadata)', value: stats.total_articles.toLocaleString(), unit: 'rows' },
              { label: 'Data Warehouse (Fact)', value: stats.total_articles.toLocaleString(), unit: 'rows' },
              { label: 'Qdrant Collection', value: stats.total_vectors.toLocaleString(), unit: 'vectors' },
              { label: 'Hệ thống Server', value: 'Healthy', unit: '🟢' },
            ].map((stat, idx) => (
              <div key={idx} className="flex justify-between items-center py-2 border-b border-slate-50 last:border-0">
                <span className="text-xs font-semibold text-slate-700">{stat.label}</span>
                <span className="text-xs font-bold text-slate-900">
                  {stat.value} <span className="text-slate-400 font-normal">{stat.unit}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}