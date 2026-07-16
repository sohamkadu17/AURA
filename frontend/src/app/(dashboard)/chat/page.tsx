"use client";

import { useState, useEffect, useRef } from "react";
import { Send, Loader2, Sparkles, User as UserIcon, Plus, MessageSquare, Trash2, Edit2, Check, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import toast from "react-hot-toast";
import api from "@/lib/api";

type Message = {
  id: number;
  content: string;
  sender: "user" | "aura";
  created_at?: string;
};

type Conversation = {
  id: number;
  title: string;
};

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  
  // Edit state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const loadConversations = async () => {
    try {
      const res = await api.get("/chat/conversations");
      setConversations(res.data);
      return res.data;
    } catch (err) {
      console.error("Failed to load conversations", err);
      return [];
    }
  };

  const loadMessages = async (convId: number) => {
    try {
      const msgRes = await api.get(`/chat/conversations/${convId}/messages`);
      const formatted = msgRes.data.map((m: any) => ({
        id: m.id,
        content: m.content,
        sender: m.role === "user" ? "user" : "aura",
        created_at: m.created_at,
      }));
      setMessages(formatted);
    } catch (err) {
      console.error("Failed to load messages", err);
    }
  };

  // Initial load
  useEffect(() => {
    const init = async () => {
      const convs = await loadConversations();
      if (convs.length > 0) {
        setConversationId(convs[0].id);
        loadMessages(convs[0].id);
      }
    };
    init();
  }, []);

  const handleSelectChat = (id: number) => {
    if (conversationId === id) return;
    setConversationId(id);
    loadMessages(id);
  };

  const handleNewChat = async () => {
    try {
      const res = await api.post("/chat/conversations", { title: "New Chat" });
      await loadConversations();
      setConversationId(res.data.id);
      setMessages([]);
    } catch (err) {
      toast.error("Failed to create chat");
    }
  };

  const handleDeleteChat = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    try {
      await api.delete(`/chat/conversations/${id}`);
      toast.success("Chat deleted");
      const updatedConvs = await loadConversations();
      if (conversationId === id) {
        if (updatedConvs.length > 0) {
          setConversationId(updatedConvs[0].id);
          loadMessages(updatedConvs[0].id);
        } else {
          setConversationId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      toast.error("Failed to delete chat");
    }
  };

  const startEdit = (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const submitEdit = async (e: React.MouseEvent | React.FormEvent, id: number) => {
    e.preventDefault();
    e.stopPropagation();
    if (!editTitle.trim()) return;
    try {
      await api.patch(`/chat/conversations/${id}`, { title: editTitle.trim() });
      setEditingId(null);
      await loadConversations();
      toast.success("Renamed chat");
    } catch (err) {
      toast.error("Failed to rename chat");
    }
  };

  const cancelEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMsg: Message = { id: Date.now(), content: input, sender: "user" };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      let currentConvId = conversationId;
      if (!currentConvId) {
        const res = await api.post("/chat/conversations", { title: "New Chat" });
        currentConvId = res.data.id;
        setConversationId(currentConvId);
      }

      const response = await api.post("/chat/", {
        message: userMsg.content,
        conversation_id: currentConvId,
      });

      const auraMsg: Message = {
        id: Date.now() + 1,
        content: response.data.response,
        sender: "aura",
      };
      setMessages((prev) => [...prev, auraMsg]);
      
      // Reload conversations in case title was auto-updated by backend
      await loadConversations();
    } catch (err: any) {
      toast.error("Failed to send message");
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex h-full bg-transparent overflow-hidden">
      
      {/* Sidebar for Chat History */}
      <div className="w-64 border-r border-white/5 flex flex-col bg-background/40 backdrop-blur-md shrink-0 z-20 hidden md:flex">
        <div className="p-4 border-b border-white/5">
          <button
            onClick={handleNewChat}
            className="flex items-center justify-center space-x-2 w-full py-2.5 bg-primary/10 hover:bg-primary/20 text-primary rounded-xl transition-colors border border-primary/20"
          >
            <Plus size={18} />
            <span className="font-medium">New Chat</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => handleSelectChat(conv.id)}
              className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-colors ${
                conversationId === conv.id ? "bg-white/10 text-white" : "text-gray-400 hover:bg-white/5 hover:text-gray-200"
              }`}
            >
              {editingId === conv.id ? (
                <div className="flex items-center space-x-2 w-full">
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="flex-1 bg-black/30 border border-white/20 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-primary"
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => e.key === "Enter" && submitEdit(e as any, conv.id)}
                  />
                  <button onClick={(e) => submitEdit(e, conv.id)} className="text-green-400 hover:text-green-300">
                    <Check size={16} />
                  </button>
                  <button onClick={cancelEdit} className="text-gray-400 hover:text-white">
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex items-center space-x-3 overflow-hidden">
                    <MessageSquare size={16} className="shrink-0" />
                    <span className="truncate text-sm font-medium">{conv.title}</span>
                  </div>
                  <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={(e) => startEdit(e, conv)} className="p-1 hover:text-primary transition-colors">
                      <Edit2 size={14} />
                    </button>
                    <button onClick={(e) => handleDeleteChat(e, conv.id)} className="p-1 hover:text-red-400 transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full bg-transparent min-w-0">
        {/* Header */}
        <header className="px-8 py-5 border-b border-white/5 bg-background/50 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-semibold text-white">AURA Assistant</h1>
            <p className="text-xs text-gray-400 mt-1">Multi-Model LLM Orchestration</p>
          </div>
        </header>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-8 space-y-6 scroll-smooth">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-50 space-y-4">
              <Sparkles className="w-12 h-12 text-primary" />
              <h2 className="text-xl font-medium text-white">How can I help you today?</h2>
              <p className="text-gray-400 text-sm max-w-sm">
                I can answer general questions, help with code, or search your uploaded documents.
              </p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={`${msg.id}-${idx}`}
                className={`flex items-start space-x-4 max-w-3xl mx-auto ${
                  msg.sender === "user" ? "flex-row-reverse space-x-reverse" : ""
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    msg.sender === "user"
                      ? "bg-surface border border-white/10 text-gray-300"
                      : "bg-primary/20 text-primary border border-primary/30"
                  }`}
                >
                  {msg.sender === "user" ? <UserIcon size={16} /> : <Sparkles size={16} />}
                </div>
                <div
                  className={`px-5 py-3.5 rounded-2xl text-sm leading-relaxed ${
                    msg.sender === "user"
                      ? "bg-primary text-white rounded-tr-sm"
                      : "glass text-gray-200 rounded-tl-sm markdown-body overflow-x-auto space-y-2 [&_p]:mb-2 [&_pre]:bg-black/50 [&_pre]:p-2 [&_pre]:rounded [&_code]:bg-black/30 [&_code]:px-1 [&_code]:rounded [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4 [&_a]:text-blue-400 [&_a]:underline"
                  }`}
                >
                  {msg.sender === "user" ? (
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  ) : (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  )}
                </div>
              </div>
            ))
          )}

          {isTyping && (
            <div className="flex items-start space-x-4 max-w-3xl mx-auto">
              <div className="w-8 h-8 rounded-full bg-primary/20 text-primary border border-primary/30 flex items-center justify-center shrink-0">
                <Sparkles size={16} />
              </div>
              <div className="px-5 py-4 glass rounded-2xl rounded-tl-sm flex space-x-2 items-center">
                <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 sm:p-6 bg-background border-t border-white/5">
          <div className="max-w-3xl mx-auto relative">
            <form onSubmit={handleSend} className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message AURA..."
                className="w-full bg-surface border border-white/10 rounded-2xl py-4 pl-5 pr-14 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all shadow-lg"
                disabled={isTyping}
              />
              <button
                type="submit"
                disabled={!input.trim() || isTyping}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-primary hover:bg-primary-hover text-white rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isTyping ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              </button>
            </form>
            <div className="text-center mt-3 text-xs text-gray-500">
              AURA can make mistakes. Verify important information.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
