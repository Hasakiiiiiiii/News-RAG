"use client";
import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, Bot, User, Cpu, Sparkles, Loader2, Database, ChevronDown
} from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  model?: string;
  sourcesCount?: number;
  duration?: number;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'ai',
      content: 'Xin chào! Tôi là Trợ lý AI được kết nối với kho dữ liệu tin tức. Bạn muốn cập nhật thông tin gì hôm nay?',
      model: 'Hệ thống'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const [models, setModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('default');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false); // <-- Thêm dòng này

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Tự động cuộn xuống tin nhắn mới nhất
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Lấy danh sách Model từ Backend
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch('http://localhost:8000/models');
        if (res.ok) {
          const data = await res.json();
          // Cấu trúc API trả về {"models": [{"name": "...", "provider": "..."}, ...]}
          if (data.models && data.models.length > 0) {
            setModels(data.models);
            setSelectedModel(data.models[0].name); // Chọn model đầu tiên làm mặc định
          }
        }
      } catch (error) {
        console.error("Lỗi lấy danh sách models:", error);
      }
    };
    fetchModels();
  }, []);

  // Hàm gửi tin nhắn
  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Gọi API Full RAG Pipeline
      const res = await fetch('http://localhost:8000/search', {
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
        content: data.raw_data?.summary || 'Xin lỗi, tôi không thể tổng hợp được câu trả lời lúc này.',
        model: selectedModel,
        sourcesCount: data.raw_data?.total || 0,
        duration: data.raw_data?.duration_ms || 0
      };

      setMessages(prev => [...prev, aiMessage]);

    } catch (error) {
      console.error("Lỗi chat:", error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'ai',
        content: 'Đã có lỗi xảy ra khi kết nối tới hệ thống AI. Vui lòng kiểm tra lại Backend (FastAPI).',
        model: 'System Error'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  return (
    <div className="p-6 md:p-8 bg-[#f8fafc] min-h-screen flex flex-col h-[calc(100vh-4rem)]">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center mb-6 gap-4 shrink-0">
        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <span className="text-indigo-600">3. AI ASSISTANT</span> 
          <span className="text-slate-500 font-medium text-lg">(Trò chuyện với dữ liệu)</span>
        </h1>
        
        {/* Model Selector */}
        {/* Custom Model Selector */}
        <div className="relative">
          {/* Nút bấm */}
          <button 
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            disabled={isLoading || models.length === 0}
            className="flex items-center gap-3 bg-white hover:bg-slate-50 px-4 py-2.5 rounded-xl border border-slate-200 shadow-sm transition-all focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 disabled:opacity-50 disabled:cursor-not-allowed"
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
            <ChevronDown 
              size={16} 
              className={`text-slate-400 ml-4 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} 
            />
          </button>

          {/* Menu thả xuống */}
          {isDropdownOpen && (
            <>
              {/* Overlay vô hình để tắt menu khi click ra ngoài */}
              <div 
                className="fixed inset-0 z-40" 
                onClick={() => setIsDropdownOpen(false)}
              ></div>

              {/* Danh sách Model */}
              <div className="absolute right-0 mt-2 w-72 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden origin-top-right animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="p-3 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500">Chuyển đổi AI</span>
                  <span className="text-[10px] font-semibold text-slate-400 bg-white px-2 py-0.5 rounded-full border border-slate-200 shadow-sm">
                    {models.length} options
                  </span>
                </div>
                
                <div className="max-h-[60vh] overflow-y-auto p-2 space-y-1 custom-scrollbar">
                  {models.map((m) => {
                    const isSelected = selectedModel === m.name;
                    return (
                      <button
                        key={m.name}
                        onClick={() => {
                          setSelectedModel(m.name);
                          setIsDropdownOpen(false);
                        }}
                        className={`w-full text-left flex items-center justify-between px-3 py-2.5 rounded-lg transition-all ${
                          isSelected 
                            ? 'bg-indigo-50 border-indigo-100' 
                            : 'hover:bg-slate-50 border-transparent'
                        } border`}
                      >
                        <div className="flex flex-col gap-0.5">
                          <span className={`text-sm font-bold ${isSelected ? 'text-indigo-700' : 'text-slate-700'}`}>
                            {m.name}
                          </span>
                          <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            {m.provider}
                          </span>
                        </div>
                        
                        {/* Dấu tích xanh nếu đang được chọn */}
                        {isSelected && (
                          <div className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center shadow-sm">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                          </div>
                        )}
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
              
              {/* Avatar AI (Bên trái) */}
              {msg.role === 'ai' && (
                <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 border border-indigo-200">
                  <Sparkles size={20} className="text-indigo-600" />
                </div>
              )}

              {/* Message Bubble */}
              <div className={`max-w-[75%] rounded-2xl px-5 py-3.5 shadow-sm ${
                msg.role === 'user' 
                  ? 'bg-indigo-600 text-white rounded-tr-sm' 
                  : 'bg-white border border-slate-200 text-slate-700 rounded-tl-sm'
              }`}>
                <div className="text-sm leading-relaxed whitespace-pre-wrap">
                  {msg.content}
                </div>
                
                {/* Meta info cho AI Message (Dựa vào RAG) */}
                {msg.role === 'ai' && msg.model && msg.id !== 'welcome' && (
                  <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-4 text-[11px] font-medium text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <Cpu size={12} /> {msg.model}
                    </span>
                    {msg.sourcesCount !== undefined && (
                      <span className="flex items-center gap-1.5 text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
                        <Database size={12} /> Dùng {msg.sourcesCount} nguồn tin
                      </span>
                    )}
                    {msg.duration !== undefined && (
                      <span className="text-slate-300">{msg.duration}ms</span>
                    )}
                  </div>
                )}
              </div>

              {/* Avatar User (Bên phải) */}
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
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm flex items-center gap-2">
                <Loader2 size={16} className="text-indigo-500 animate-spin" />
                <span className="text-sm text-slate-500 font-medium">Đang đọc tài liệu và suy nghĩ...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* INPUT AREA */}
        <div className="p-4 bg-white border-t border-slate-100">
          <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 p-2 rounded-xl focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-50 transition-all">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Hỏi AI về tin tức, thị trường, lãi suất..."
              className="flex-1 bg-transparent border-none outline-none text-sm text-slate-700 px-3 font-medium placeholder:text-slate-400"
              disabled={isLoading}
            />
            <button 
              onClick={handleSendMessage}
              disabled={!input.trim() || isLoading}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white p-2.5 rounded-lg transition-colors flex items-center justify-center"
            >
              <Send size={18} className={isLoading ? 'opacity-0' : 'opacity-100'} />
              {isLoading && <Loader2 size={18} className="absolute animate-spin" />}
            </button>
          </div>
          <div className="text-center mt-2">
            <span className="text-[10px] text-slate-400">AI có thể mắc sai lầm. Hãy luôn kiểm tra lại các thông tin quan trọng từ báo gốc.</span>
          </div>
        </div>

      </div>
    </div>
  );
}