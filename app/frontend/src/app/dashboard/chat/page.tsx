"use client";
import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, Bot, User, Cpu, Sparkles, Loader2, Database, ChevronDown, Scale, Search
} from 'lucide-react';
import { marked } from 'marked';

// --- MỞ RỘNG INTERFACE ĐỂ CHỨA NHIỀU LOẠI DATA ---
interface Message {
  id: string;
  role: 'user' | 'ai';
  type: 'welcome' | 'rag' | 'retrieve' | 'compare' | 'error';
  content?: string;
  model?: string;
  duration?: number;
  
  // Dành riêng cho RAG
  sources?: Array<{title: string, url: string}>;
  sourcesCount?: number;
  
  // Dành riêng cho Retrieve
  retrieveResults?: Array<{title: string, url: string, content_snippet: string, score: number}>;
  
  // Dành riêng cho Compare
  comparisons?: Array<{model: string, response: string}>;
  contextDocsCount?: number;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'ai',
      type: 'welcome',
      content: 'Xin chào! Tôi là Trợ lý AI được kết nối với kho dữ liệu tin tức. Bạn muốn cập nhật thông tin gì hôm nay? Bạn có thể Hỏi AI, Tìm kiếm DB hoặc So sánh các Model.',
      model: 'Hệ thống'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [actionType, setActionType] = useState<string>(''); // Lưu trạng thái đang load cái gì
  
  const [models, setModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('default');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch('http://localhost:8000/models');
        if (res.ok) {
          const data = await res.json();
          if (data.models && data.models.length > 0) {
            setModels(data.models);
            setSelectedModel(data.models[0].name);
          }
        }
      } catch (error) {
        console.error("Lỗi lấy danh sách models:", error);
      }
    };
    fetchModels();
  }, []);

  const filterThinkingProcess = (content: string) => {
    return (content || "").replace(/<think>[\s\S]*?<\/think>/g, '').trim();
  };

  // --- HÀM GỬI TIN NHẮN THEO LOẠI ---
  const handleSendMessage = async (type: 'rag' | 'retrieve' | 'compare' = 'rag') => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      type: 'rag',
      content: input.trim()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setActionType(type);

    let endpoint = "/search";
    if (type === 'retrieve') endpoint = "/search/retrieve";
    if (type === 'compare') endpoint = "/search/compare";

    try {
      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: userMessage.content,
          model: selectedModel
        }),
      });

      if (!res.ok) throw new Error("Lỗi kết nối Backend");
      const data = await res.json();
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        type: type,
        model: selectedModel,
      };

      // Xử lý dữ liệu dựa trên loại request
      if (type === 'rag') {
        const rawContent = data.raw_data?.summary || '';
        aiMessage.content = filterThinkingProcess(rawContent) || 'Xin lỗi, tôi không tìm thấy thông tin phù hợp.';
        aiMessage.sourcesCount = data.raw_data?.total || 0;
        aiMessage.sources = data.raw_data?.results || [];
        aiMessage.duration = data.raw_data?.duration_ms;
      } 
      else if (type === 'retrieve') {
        aiMessage.sourcesCount = data.total_found || 0;
        aiMessage.retrieveResults = data.results || [];
      } 
      else if (type === 'compare') {
        aiMessage.contextDocsCount = data.context_documents || 0;
        aiMessage.comparisons = (data.model_responses || []).map((m: any) => {
           let text = typeof m.response === 'object' ? m.response.summary : m.response;
           return {
             model: m.model,
             response: filterThinkingProcess(text)
           };
        });
      }

      setMessages(prev => [...prev, aiMessage]);

    } catch (error) {
      console.error("Lỗi chat:", error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'ai',
        type: 'error',
        content: 'Đã có lỗi xảy ra khi kết nối tới hệ thống AI. Vui lòng kiểm tra lại Backend.',
      }]);
    } finally {
      setIsLoading(false);
      setActionType('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSendMessage('rag'); // Mặc định Enter là gọi RAG
    }
  };

  // --- RENDER NỘI DUNG AI DỰA TRÊN LOẠI TIN NHẮN ---
  const renderAIMessageContent = (msg: Message) => {
    if (msg.type === 'error' || msg.type === 'welcome') {
      return <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>;
    }

    if (msg.type === 'rag') {
      return (
        <div className="w-full">
          {/* Parse Markdown thay vì text thuần */}
          <div 
            className="prose max-w-none text-sm text-slate-700 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: marked(msg.content || "") }} 
          />
          
          {msg.sources && msg.sources.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <h3 className="text-[11px] font-bold text-slate-400 mb-2 uppercase tracking-wider">🔗 Nguồn tham khảo</h3>
              <div className="flex flex-wrap gap-2">
                {msg.sources.map((s, i) => (
                  <a key={i} href={s.url} target="_blank" rel="noreferrer" 
                     className="px-3 py-1.5 bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-600 text-xs rounded-md transition truncate max-w-[250px]" 
                     title={s.title}>
                    [{i+1}] {s.title}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    if (msg.type === 'retrieve') {
      return (
        <div className="w-full">
          <div className="flex items-center gap-2 mb-4 text-slate-700 font-bold border-b pb-2">
            <Database size={18} className="text-slate-500"/>
            <span>Kết quả Qdrant ({msg.sourcesCount})</span>
          </div>
          <div className="space-y-3">
            {msg.retrieveResults?.map((hit, i) => (
              <div key={i} className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                <a href={hit.url} target="_blank" rel="noreferrer" className="text-indigo-600 font-semibold text-sm hover:underline line-clamp-2">
                  [{i+1}] {hit.title}
                </a>
                <p className="text-sm mt-2 text-slate-600 italic line-clamp-3">"{hit.content_snippet}"</p>
                <div className="mt-2 text-[11px] text-emerald-600 font-medium">
                  Độ tương đồng (Score): {hit.score.toFixed(4)}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (msg.type === 'compare') {
      return (
        <div className="w-full">
          <div className="mb-4 text-sm text-slate-500 flex items-center gap-2 border-b pb-2">
            <Scale size={16} /> So sánh phản hồi từ các Models (Context: {msg.contextDocsCount} tài liệu)
          </div>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {msg.comparisons?.map((comp, i) => (
              <div key={i} className="bg-slate-50 p-4 rounded-xl border border-slate-200 shadow-sm border-t-4 border-t-indigo-500">
                <h3 className="font-bold text-slate-700 mb-3 text-sm uppercase tracking-wide border-b border-slate-200 pb-2">
                  {comp.model}
                </h3>
                <div 
                  className="prose max-w-none text-sm text-slate-700 overflow-y-auto max-h-72 custom-scrollbar pr-2"
                  dangerouslySetInnerHTML={{ __html: marked(comp.response || "") }}
                />
              </div>
            ))}
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="p-6 md:p-8 bg-[#f8fafc] min-h-screen flex flex-col h-[calc(100vh-4rem)]">
      {/* HEADER (Giữ nguyên Model Selector) */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center mb-6 gap-4 shrink-0">
        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <span className="text-indigo-600">3. AI ASSISTANT</span> 
          <span className="text-slate-500 font-medium text-lg">(Trò chuyện với dữ liệu)</span>
        </h1>
        
        <div className="relative">
          <button 
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            disabled={isLoading || models.length === 0}
            className="flex items-center gap-3 bg-white hover:bg-slate-50 px-4 py-2.5 rounded-xl border border-slate-200 shadow-sm transition-all focus:ring-2 focus:ring-indigo-100 disabled:opacity-50"
          >
            <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-indigo-50/50 border border-indigo-100 text-indigo-600">
              <Cpu size={16} />
            </div>
            <div className="flex flex-col items-start">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider leading-none mb-1">
                Model đang dùng
              </span>
              <span className="text-sm font-bold text-slate-700 leading-none">
                {selectedModel === 'default' ? 'Đang tải...' : selectedModel}
              </span>
            </div>
            <ChevronDown size={16} className={`text-slate-400 ml-4 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {isDropdownOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setIsDropdownOpen(false)}></div>
              <div className="absolute right-0 mt-2 w-72 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden origin-top-right animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="p-3 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500">Chuyển đổi AI</span>
                  <span className="text-[10px] font-semibold text-slate-400 bg-white px-2 py-0.5 rounded-full border border-slate-200 shadow-sm">
                    {models.length} options
                  </span>
                </div>
                <div className="max-h-[60vh] overflow-y-auto p-2 space-y-1">
                  {models.map((m) => {
                    const isSelected = selectedModel === m.name;
                    return (
                      <button
                        key={m.name}
                        onClick={() => { setSelectedModel(m.name); setIsDropdownOpen(false); }}
                        className={`w-full text-left flex items-center justify-between px-3 py-2.5 rounded-lg transition-all ${isSelected ? 'bg-indigo-50 border-indigo-100' : 'hover:bg-slate-50 border-transparent'} border`}
                      >
                        <div className="flex flex-col gap-0.5">
                          <span className={`text-sm font-bold ${isSelected ? 'text-indigo-700' : 'text-slate-700'}`}>{m.name}</span>
                          <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>{m.provider}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* CHAT CONTAINER */}
      <div className="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
        
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              
              {/* Avatar AI */}
              {msg.role === 'ai' && (
                <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 border border-indigo-200">
                  {msg.type === 'retrieve' ? <Database size={18} className="text-indigo-600"/> :
                   msg.type === 'compare' ? <Scale size={18} className="text-indigo-600"/> :
                   <Sparkles size={20} className="text-indigo-600" />}
                </div>
              )}

              {/* Message Bubble (Mở rộng max-width nếu là compare hoặc retrieve) */}
              <div className={`${
                msg.type === 'compare' || msg.type === 'retrieve' ? 'w-full md:max-w-[85%]' : 'max-w-[75%]'
              } rounded-2xl px-5 py-4 shadow-sm ${
                msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-sm' : 'bg-white border border-slate-200 text-slate-700 rounded-tl-sm'
              }`}>
                {/* Render nội dung linh hoạt */}
                {msg.role === 'user' ? (
                  <div className="text-sm font-medium whitespace-pre-wrap">{msg.content}</div>
                ) : (
                  renderAIMessageContent(msg)
                )}
                
                {/* Meta info cho RAG */}
                {msg.role === 'ai' && msg.type === 'rag' && msg.id !== 'welcome' && (
                  <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-4 text-[11px] font-medium text-slate-400">
                    <span className="flex items-center gap-1.5"><Cpu size={12} /> {msg.model}</span>
                    {msg.sourcesCount !== undefined && (
                      <span className="flex items-center gap-1.5 text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
                        <Database size={12} /> Dùng {msg.sourcesCount} nguồn tin
                      </span>
                    )}
                    {msg.duration !== undefined && <span>{msg.duration}ms</span>}
                  </div>
                )}
              </div>

              {/* Avatar User */}
              {msg.role === 'user' && (
                <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center shrink-0 border border-slate-300">
                  <User size={20} className="text-slate-600" />
                </div>
              )}
            </div>
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex gap-4 justify-start">
              <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 border border-indigo-200">
                <Bot size={20} className="text-indigo-600" />
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm flex items-center gap-3">
                <Loader2 size={18} className="text-indigo-500 animate-spin" />
                <span className="text-sm text-slate-500 font-medium">
                  {actionType === 'retrieve' ? 'Đang lục lọi trong Qdrant...' : 
                   actionType === 'compare' ? 'Đang yêu cầu các Models phản hồi...' : 
                   'Đang đọc tài liệu và suy nghĩ...'}
                </span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* INPUT AREA (Đã thêm 3 nút chức năng) */}
        <div className="p-4 bg-white border-t border-slate-100">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 p-2 rounded-xl focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-50 transition-all">
              <input 
                type="text" 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Nhập câu hỏi (VD: Tình hình giá vàng hôm nay?)"
                className="flex-1 bg-transparent border-none outline-none text-sm text-slate-700 px-3 font-medium placeholder:text-slate-400"
                disabled={isLoading}
              />
            </div>
            
            <div className="flex flex-wrap items-center justify-end gap-2">
              <button 
                onClick={() => handleSendMessage('rag')}
                disabled={!input.trim() || isLoading}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white py-2 px-4 rounded-lg transition-colors flex items-center gap-2 text-sm font-semibold shadow-sm"
              >
                <Sparkles size={16} /> Hỏi AI
              </button>
              
              <button 
                onClick={() => handleSendMessage('retrieve')}
                disabled={!input.trim() || isLoading}
                className="bg-slate-700 hover:bg-slate-800 disabled:bg-slate-300 text-white py-2 px-4 rounded-lg transition-colors flex items-center gap-2 text-sm font-semibold shadow-sm"
              >
                <Search size={16} /> Tìm Qdrant
              </button>

              <button 
                onClick={() => handleSendMessage('compare')}
                disabled={!input.trim() || isLoading}
                className="bg-purple-600 hover:bg-purple-700 disabled:bg-slate-300 text-white py-2 px-4 rounded-lg transition-colors flex items-center gap-2 text-sm font-semibold shadow-sm"
              >
                <Scale size={16} /> So sánh LLMs
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}