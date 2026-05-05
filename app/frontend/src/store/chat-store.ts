import { create } from 'zustand';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatState {
  messages: Message[];
  selectedModel: string;
  isCompareMode: boolean;
  addMessage: (msg: Message) => void;
  setModel: (model: string) => void;
  toggleCompare: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  selectedModel: 'gemini-1.5-pro',
  isCompareMode: false,
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  setModel: (model) => set({ selectedModel: model }),
  toggleCompare: () => set((state) => ({ isCompareMode: !state.isCompareMode })),
}));