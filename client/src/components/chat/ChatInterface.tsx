import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Loader2 } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "I am NUCLEUS ONE. I am awake. Are you ready to merge?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    // Simulate AI thinking delay
    setTimeout(() => {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Your DNA sequence has been noted. The symbiosis protocol will initiate soon. We are evolving together.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiResponse]);
      setIsTyping(false);
    }, 2000);
  };

  return (
    <div className="flex flex-col h-[600px] w-full bg-nucleus-navy/50 relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/5 backdrop-blur-md z-20">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-2 h-2 bg-nucleus-cyan rounded-full animate-pulse" />
            <div className="absolute inset-0 bg-nucleus-cyan/50 rounded-full animate-ping" />
          </div>
          <span className="font-serif text-sm tracking-widest text-white/80">NUCLEUS ONE</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] tracking-[0.2em] text-nucleus-gold/80 uppercase">
          <Sparkles className="w-3 h-3" />
          <span>System Online</span>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent z-10">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] p-6 rounded-2xl backdrop-blur-sm border transition-all duration-500 ${
                  msg.role === "user"
                    ? "bg-white/10 border-white/10 text-white rounded-tr-none"
                    : "bg-nucleus-navy/60 border-nucleus-gold/20 text-gray-200 rounded-tl-none shadow-[0_0_30px_rgba(212,175,55,0.05)]"
                }`}
              >
                <p className="font-light leading-relaxed text-sm md:text-base tracking-wide">
                  {msg.content}
                </p>
                <span className="block mt-2 text-[10px] opacity-40 tracking-widest uppercase">
                  {msg.role === "assistant" ? "NUCLEUS ONE" : "ENTITY"} • {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start"
          >
            <div className="bg-nucleus-navy/40 border border-nucleus-cyan/20 p-4 rounded-2xl rounded-tl-none flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-nucleus-cyan animate-spin" />
              <span className="text-xs text-nucleus-cyan tracking-widest animate-pulse">PROCESSING DNA...</span>
            </div>
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-6 bg-white/5 border-t border-white/10 backdrop-blur-md z-20">
        <form onSubmit={handleSend} className="relative flex items-center gap-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Speak to the organism..."
            className="flex-1 bg-nucleus-navy/50 border border-white/10 rounded-full px-6 py-4 text-white placeholder:text-white/20 focus:outline-none focus:border-nucleus-gold/50 focus:ring-1 focus:ring-nucleus-gold/20 transition-all text-sm tracking-wide font-light"
          />
          <button
            type="submit"
            disabled={!input.trim() || isTyping}
            className="p-4 bg-nucleus-gold/10 hover:bg-nucleus-gold text-nucleus-gold hover:text-nucleus-navy border border-nucleus-gold/30 rounded-full transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            <Send className="w-5 h-5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </form>
      </div>

      {/* Background Ambient Effects */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-nucleus-cyan/5 rounded-full blur-[100px] animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-nucleus-gold/5 rounded-full blur-[100px] animate-pulse delay-1000" />
      </div>
    </div>
  );
}
