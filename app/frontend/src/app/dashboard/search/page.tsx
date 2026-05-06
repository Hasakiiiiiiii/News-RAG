"use client";
import React, { useState, useEffect } from 'react';
import { 
  Search, 
  ChevronDown, 
  FileText, 
  X,
  Loader2,
  Newspaper
} from 'lucide-react';

const formatDate = (dateString: string) => {
  if (!dateString || dateString === 'N/A') return 'N/A';
  try {
    const datePart = dateString.split('T')[0];
    const [year, month, day] = datePart.split('-');
    return `${day}/${month}/${year}`;
  } catch (e) {
    return dateString;
  }
};

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('All Sources');
  const [topK, setTopK] = useState(10);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  const [rawResults, setRawResults] = useState<any[]>([]); 
  const [results, setResults] = useState<any[]>([]);       
  const [isLoading, setIsLoading] = useState(false);       

  // --- HÀM GỌI API THUẦN POSTGRESQL ---
  const fetchResults = async () => {
    setIsLoading(true);
    
    try {
      // Gắn query và limit thẳng vào URL API
      const searchParam = query.trim() ? `&q=${encodeURIComponent(query)}` : '';
      const res = await fetch(`http://localhost:8000/articles?limit=50${searchParam}`); 
      
      if (!res.ok) throw new Error("Lỗi kết nối API PostgreSQL");
      
      const data = await res.json();
      
      const mappedResults = data.map((item: any) => {
        return {
          id: item.id,
          title: item.title,
          source: item.source || 'Unknown',  // Lấy thẳng domain từ dim_source
          date: item.published_date || 'N/A', // Lấy ngày chuẩn từ dim_time
          author: item.author || 'Tác giả',   // Lấy tên thật từ dim_author
          snippet: item.snippet || 'Không có tóm tắt...', // Lấy 150 chữ từ dim_content
          url: item.url || '#'
        };
      });
      
      setRawResults(mappedResults);
    } catch (error) {
      console.error("Lỗi khi fetch data:", error);
      alert("Không thể kết nối Backend. Chắc chắn FastAPI đang chạy ở port 8000 nhé!");
      setRawResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = () => fetchResults();

  useEffect(() => {
    fetchResults();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Lọc dữ liệu Frontend (Source, TopK)
  useEffect(() => {
    let filtered = [...rawResults];

    if (source !== 'All Sources') {
      filtered = filtered.filter(item => item.source === source);
    }
    
    // Vì SQL đã order by thời gian mới nhất rồi nên không cần sort lại
    setResults(filtered.slice(0, topK));

  }, [rawResults, source, topK, startDate, endDate]);

  return (
    <div className="p-6 md:p-8 space-y-6 bg-[#f8fafc] min-h-screen">
      <div className="mb-2">
        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2 uppercase tracking-tight">
          <span className="text-indigo-600">2. NEWS SEARCH</span> 
          <span className="text-slate-500 font-medium text-lg normal-case">(Tìm kiếm kho bài báo)</span>
        </h1>
      </div>

      {/* SEARCH BAR SECTION */}
      <div className="bg-white p-2 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-2">
        <div className="flex-1 flex items-center px-3 gap-3">
          <Search size={20} className="text-slate-400" />
          <input 
            type="text" 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Nhập tiêu đề bài báo cần tìm..." 
            className="flex-1 bg-transparent outline-none text-slate-700 py-2 font-medium"
            disabled={isLoading}
          />
          {query && !isLoading && (
            <X size={16} className="text-slate-300 cursor-pointer hover:text-slate-500" onClick={() => {setQuery('');}} />
          )}
        </div>
        <button 
          onClick={handleSearch}
          disabled={isLoading}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 flex items-center gap-2 text-white px-8 py-2.5 rounded-xl font-bold transition-all active:scale-95"
        >
          {isLoading ? <Loader2 size={18} className="animate-spin" /> : null}
          {isLoading ? 'Đang tìm...' : 'Search'}
        </button>
      </div>

      {/* FILTERS SECTION */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
        <div className="col-span-3 space-y-1.5">
          <label className="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-1">Source</label>
          <select 
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-bold text-slate-700 outline-none focus:border-indigo-500 transition-colors cursor-pointer appearance-none"
          >
            <option>All Sources</option>
            <option>vnexpress.net</option>
            <option>dantri.com.vn</option>
            <option>vietnamnet.vn</option>
            <option>cafef.vn</option>
            <option>vneconomy.vn</option>
          </select>
        </div>
        
        <div className="col-span-5 space-y-1.5">
          <label className="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-1">Date range</label>
          <div className="flex items-center gap-2">
            <input 
              type="date" 
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm font-bold text-slate-700 outline-none focus:border-indigo-500 cursor-pointer"
            />
            <span className="text-slate-400 font-bold">-</span>
            <input 
              type="date" 
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm font-bold text-slate-700 outline-none focus:border-indigo-500 cursor-pointer"
            />
          </div>
        </div>

        <div className="col-span-4 flex gap-4">
          <div className="space-y-1.5 flex-1">
            <label className="text-[11px] font-black text-slate-400 uppercase tracking-widest ml-1">Limit</label>
            <select 
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm font-bold text-slate-700 outline-none focus:border-indigo-500 transition-colors cursor-pointer appearance-none"
            >
              <option value={10}>10 bài</option>
              <option value={20}>20 bài</option>
              <option value={50}>50 bài</option>
            </select>
          </div>
          <button 
            onClick={() => { 
              setQuery(''); 
              setSource('All Sources'); 
              setTopK(10); 
              setStartDate(''); 
              setEndDate(''); 
              setTimeout(() => fetchResults(), 100);
            }}
            className="h-[42px] mt-auto bg-slate-100 text-slate-600 hover:bg-slate-200 px-6 rounded-xl font-bold text-sm transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      {/* RESULTS LIST */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/30">
          <h3 className="font-bold text-slate-800">
            {query.trim() === '' ? 'Bài báo mới cập nhật' : `Kết quả tìm kiếm cho "${query}"`} <span className="text-slate-400 font-normal">({isLoading ? '...' : results.length} bài viết)</span>
          </h3>
          <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-tighter">
            Sắp xếp: <span className="text-indigo-600">Mới nhất trước</span>
          </div>
        </div>

        <div className="p-6 space-y-4">
          {isLoading ? (
             <div className="py-20 text-center space-y-3">
               <div className="flex justify-center items-center">
                  <Loader2 size={40} className="text-indigo-500 animate-spin" />
               </div>
               <p className="text-slate-400 font-medium">Đang truy xuất dữ liệu từ kho bài báo...</p>
             </div>
          ) : results.length > 0 ? (
            results.map((result) => (
              <div key={result.id} className="border border-slate-100 rounded-2xl p-5 hover:border-indigo-200 hover:shadow-md transition-all group bg-white flex gap-5 items-start">
                
                {/* Icon Column */}
                <div className="flex flex-col items-center justify-center shrink-0 w-16 h-16 bg-slate-50 rounded-2xl border border-slate-100 text-indigo-400 group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors">
                  <Newspaper size={28} strokeWidth={1.5} />
                </div>

                {/* Content Column */}
                <div className="flex-1 space-y-2">
                  <h4 className="text-lg font-bold text-slate-800 group-hover:text-indigo-600 transition-colors leading-tight">
                    {result.title}
                  </h4>
                  <div className="flex items-center gap-3 text-[11px] font-bold text-slate-400">
                    <span className="text-slate-600 uppercase tracking-wider">{result.source}</span>
                    <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                    <span>{formatDate(result.date)}</span>
                    <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                    <span>{result.author}</span>
                  </div>
                  <p className="text-sm text-slate-500 leading-relaxed line-clamp-1 italic">
                    {result.snippet}
                  </p>
                </div>

                {/* Action Column */}
                <div className="flex items-center gap-2 self-center shrink-0">
                  <a href={result.url} target="_blank" rel="noreferrer" className="bg-slate-50 text-slate-700 hover:bg-indigo-600 hover:text-white px-4 py-2 rounded-xl text-xs font-bold transition-all border border-slate-200 hover:border-indigo-600 flex items-center gap-2">
                    Xem bài gốc
                  </a>
                </div>
              </div>
            ))
          ) : (
            <div className="py-20 text-center space-y-3">
              <div className="inline-block p-4 bg-slate-50 rounded-full text-slate-300">
                <Search size={40} />
              </div>
              <p className="text-slate-400 font-medium">Không có bài báo nào phù hợp. Hãy thử từ khóa khác.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}