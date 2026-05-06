"use client";
import React, { useState, useEffect } from 'react';
import { 
  Table as TableIcon, Filter, Search, ExternalLink, 
  ChevronLeft, ChevronRight, RefreshCcw, Calendar, Database,
  Layers, Brackets, Network, ChevronDown, ChevronUp
} from 'lucide-react';

// Định nghĩa kiểu dữ liệu
interface Article {
  id: string | number;
  title: string;
  url: string;
  source?: string;
  published_date?: string;
}

interface ChunkData {
  chunk_id: string;
  text: string;
}

export default function ArticleExplorerPage() {
  // State cho Articles
  const [articles, setArticles] = useState<Article[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  // State cho Vector Chunks
  const [expandedRow, setExpandedRow] = useState<string | number | null>(null);
  const [chunksData, setChunksData] = useState<ChunkData[]>([]);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);

  // Lấy danh sách bài báo
  const fetchArticles = async () => {
    setIsLoading(true);
    setExpandedRow(null); // Đóng chunk view khi đổi trang
    try {
      const offset = (page - 1) * limit;
      const res = await fetch(`http://localhost:8000/articles?q=${searchQuery}&limit=${limit}&offset=${offset}`);
      
      if (res.ok) {
        const data = await res.json();
        setArticles(data);
        
        // Logic tính tổng số trang đơn giản dựa trên độ dài mảng trả về
        if (data.length < limit) {
          setTotalPages(page);
        } else {
          setTotalPages(page + 1);
        }
      }
    } catch (error) {
      console.error("Lỗi khi tải dữ liệu bài báo:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchArticles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1); 
    fetchArticles();
  };

  // Lấy chi tiết Chunks của 1 bài báo
  const fetchChunks = async (articleId: string | number) => {
    if (expandedRow === articleId) {
      setExpandedRow(null);
      return;
    }
    
    setExpandedRow(articleId);
    setIsLoadingChunks(true);
    try {
      const res = await fetch(`http://localhost:8000/articles/${articleId}/chunks`);
      const data = await res.json();
      setChunksData(data.chunks || []);
    } catch (error) {
      console.error("Lỗi lấy chunks", error);
      setChunksData([]);
    } finally {
      setIsLoadingChunks(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', { 
      day: '2-digit', month: '2-digit', year: 'numeric'
    });
  };

  return (
    <div className="p-6 md:p-8 bg-[#f8fafc] min-h-screen">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Database className="text-indigo-600" /> 
            DATA EXPLORER & VECTOR MANAGER
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Duyệt dữ liệu thô và kiểm tra thuật toán Chunking trước khi đưa vào Qdrant.
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <button 
            onClick={() => fetchArticles()}
            className="p-2.5 bg-white border border-slate-200 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors shadow-sm"
            title="Làm mới dữ liệu"
          >
            <RefreshCcw size={18} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* TOOLBAR */}
      <div className="bg-white p-4 rounded-t-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="w-full md:w-96 relative flex items-center">
          <Search size={16} className="absolute left-3 text-slate-400" />
          <input 
            type="text" 
            placeholder="Tìm theo tiêu đề bài báo..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-400 transition-all"
          />
        </form>

        <div className="flex gap-2 w-full md:w-auto">
          <button className="flex items-center gap-2 px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors">
            <Filter size={16} /> Lọc nâng cao
          </button>
        </div>
      </div>

      {/* DATA TABLE */}
      <div className="bg-white border-x border-b border-slate-200 shadow-sm overflow-x-auto rounded-b-2xl">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-xs uppercase tracking-wider font-bold text-slate-500">
              <th className="p-4 w-16 text-center">ID</th>
              <th className="p-4 w-2/4">Tiêu đề bài báo</th>
              <th className="p-4 w-32">Nguồn</th>
              <th className="p-4 w-32">Thời gian</th>
              <th className="p-4 text-center w-32">Data Lineage</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-sm">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, idx) => (
                <tr key={idx} className="animate-pulse">
                  <td className="p-4"><div className="h-4 bg-slate-200 rounded w-8 mx-auto"></div></td>
                  <td className="p-4"><div className="h-4 bg-slate-200 rounded w-3/4"></div></td>
                  <td className="p-4"><div className="h-4 bg-slate-200 rounded w-20"></div></td>
                  <td className="p-4"><div className="h-4 bg-slate-200 rounded w-24"></div></td>
                  <td className="p-4"><div className="h-6 bg-slate-200 rounded-md w-24 mx-auto"></div></td>
                </tr>
              ))
            ) : articles.length > 0 ? (
              articles.map((article) => (
                <React.Fragment key={article.id}>
                  <tr className={`hover:bg-indigo-50/50 transition-colors group ${expandedRow === article.id ? 'bg-indigo-50/80' : ''}`}>
                    <td className="p-4 text-center text-slate-400 font-mono text-xs">{article.id}</td>
                    <td className="p-4 font-medium text-slate-700">
                      <a href={article.url} target="_blank" rel="noreferrer" className="hover:text-indigo-600 flex items-center gap-1 group/link">
                        <span className="line-clamp-2">{article.title}</span>
                        <ExternalLink size={14} className="opacity-0 group-hover/link:opacity-100 transition-opacity text-indigo-400" />
                      </a>
                    </td>
                    <td className="p-4">
                      <span className="bg-slate-100 text-slate-600 px-2.5 py-1 rounded-md text-xs font-semibold border border-slate-200">
                        {article.source || 'N/A'}
                      </span>
                    </td>
                    <td className="p-4 text-slate-500 flex items-center gap-2 mt-2">
                      <Calendar size={14} className="text-slate-400" />
                      {formatDate(article.published_date)}
                    </td>
                    <td className="p-4 text-center">
                      <button 
                        onClick={() => fetchChunks(article.id)}
                        className={`inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all w-full ${
                          expandedRow === article.id 
                            ? 'bg-slate-800 text-emerald-400 shadow-md ring-2 ring-slate-800 ring-offset-1' 
                            : 'bg-white border border-slate-200 text-slate-600 hover:border-indigo-300 hover:text-indigo-600'
                        }`}
                      >
                        <Layers size={14} />
                        {expandedRow === article.id ? 'Đóng' : 'Xem Vector'}
                        {expandedRow === article.id ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                      </button>
                    </td>
                  </tr>

                  {/* KHU VỰC HIỂN THỊ CHUNKS */}
                  {expandedRow === article.id && (
                    <tr>
                      <td colSpan={5} className="p-0 border-b border-slate-200">
                        <div className="bg-slate-900 p-6 shadow-inner">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="text-emerald-400 font-bold flex items-center gap-2">
                              <Network size={18} />
                              Data Pipeline: Chunking Results
                            </h4>
                            <span className="text-slate-400 text-xs font-mono bg-slate-800 px-3 py-1 rounded-full border border-slate-700">
                              Tổng cộng: <strong className="text-white">{chunksData.length}</strong> chunks
                            </span>
                          </div>

                          {isLoadingChunks ? (
                            <div className="flex items-center justify-center py-8 text-emerald-400">
                              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-400"></div>
                            </div>
                          ) : chunksData.length === 0 ? (
                            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 text-center">
                              <p className="text-slate-400 text-sm">Chưa có dữ liệu vector cho bài báo này trong Data Warehouse.</p>
                            </div>
                          ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                              {chunksData.map((chunk, idx) => (
                                <div key={idx} className="bg-slate-800 border border-slate-700 rounded-xl p-4 hover:border-emerald-500/50 transition-all shadow-sm group">
                                  <div className="flex items-center justify-between mb-3 border-b border-slate-700 pb-2">
                                    <span className="bg-slate-700 text-slate-300 px-2 py-1 rounded text-[10px] font-mono flex items-center gap-1 font-bold group-hover:bg-emerald-900/50 group-hover:text-emerald-400 transition-colors">
                                      <Brackets size={12} /> Chunk #{idx + 1}
                                    </span>
                                    <span className="text-slate-500 text-[10px] truncate max-w-[150px] font-mono">
                                      {chunk.chunk_id}
                                    </span>
                                  </div>
                                  <p className="text-slate-300 text-xs leading-relaxed line-clamp-6 mb-3 font-medium">
                                    {chunk.text}
                                  </p>
                                  <div className="flex gap-2">
                                    <span className="text-[10px] bg-indigo-500/10 text-indigo-400 px-2 py-1 rounded border border-indigo-500/20 flex-1 text-center font-semibold">
                                      Est. Tokens: ~{Math.round(chunk.text.length / 4)}
                                    </span>
                                    <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded border border-emerald-500/20 flex-1 text-center font-semibold">
                                      Status: Ready
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="p-12 text-center text-slate-400">
                  <TableIcon size={48} className="mx-auto mb-4 opacity-20" />
                  <p>Không tìm thấy bài báo nào trong cơ sở dữ liệu.</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* PAGINATION */}
        {!isLoading && articles.length > 0 && (
          <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between rounded-b-2xl">
            <span className="text-sm text-slate-500 font-medium">
              Trang <strong className="text-slate-800">{page}</strong> 
              {totalPages > page ? ` / ${totalPages}+` : ` / ${totalPages}`}
            </span>
            <div className="flex gap-2">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 bg-white border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
              >
                <ChevronLeft size={18} />
              </button>
              <button 
                onClick={() => setPage(p => p + 1)}
                disabled={articles.length < limit}
                className="p-2 bg-white border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}