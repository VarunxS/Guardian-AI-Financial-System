import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { getUserId } from '../utils/auth';

export default function AskGuardian() {
  const [messages, setMessages] = useState(() => {
    const hasAnalysis = !!sessionStorage.getItem('GUARDIAN_ANALYSIS');
    return [{
      role: 'assistant',
      content: hasAnalysis 
        ? "Hello. I am Guardian, your financial immune system. I've analyzed your recent statements and cross-referenced them with current market offers. How can I assist you with your finances today?"
        : "Hello. I am Guardian, your financial immune system. I am currently in general mode. To chat about your specific findings and get personalized insights, please sync your recent transactions."
    }];
  });
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const stored = sessionStorage.getItem('GUARDIAN_ANALYSIS');
    if (stored) setAnalysis(JSON.parse(stored));
  }, []);

  const StatusCycle = () => {
    const [index, setIndex] = useState(0);
    const statuses = [
      "Analyzing request parameters...",
      "Routing to financial domain...",
      "Executing semantic retrieval...",
      "Synthesizing context matrix...",
      "Consulting live web agents (Exa)...",
      "Generating final response..."
    ];

    useEffect(() => {
      const timer = setInterval(() => {
        setIndex(prev => (prev + 1) % statuses.length);
      }, 1800);
      return () => clearInterval(timer);
    }, []);

    return (
      <div className="flex flex-col gap-1.5 overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.p
            key={index}
            initial={{ opacity: 0, x: 5 }}
            animate={{ opacity: 0.8, x: 0 }}
            exit={{ opacity: 0, x: -5 }}
            className="text-[10px] font-mono text-text-ink/80 tracking-tight"
          >
            {`> ${statuses[index]}`}
          </motion.p>
        </AnimatePresence>
        <div className="flex gap-1">
          {statuses.map((_, i) => (
            <div 
              key={i} 
              className={`h-[1px] flex-1 rounded-full transition-all duration-700 ${i <= index ? 'bg-accent/40' : 'bg-border-light'}`} 
            />
          ))}
        </div>
      </div>
    );
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const apiKey = localStorage.getItem('GUARDIAN_API_KEY');
    if (!apiKey) {
      alert("Please enter your API Key in the Settings page first.");
      return;
    }

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage,
          user_id: getUserId(),
          api_key: apiKey
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status}`);
      }

      const data = await response.json();
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.answer,
        source: data.metadata?.source_label || data.mode
      }]);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'I encountered an error trying to connect to the backend. Please check your API key and ensure the FastAPI server is running.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const findingsCount = analysis?.findings_count || 0;
  const healthScore = analysis?.health_score || 'N/A';
  const missedRewards = analysis?.reward_findings?.[0]?.total_missed_monthly || 0;

  return (
    <div className="flex-1 flex flex-col lg:flex-row h-full w-full gap-10 max-w-[1400px] mx-auto pt-10 px-10 pb-2 relative">
      
      {/* Knowledge Context Sidebar (Reference 2 style) */}
      <aside className="hidden lg:flex w-[300px] shrink-0 flex-col gap-6 sticky top-0 h-fit">
        <div className="flex items-center gap-2 mb-2 px-2">
           <span className="material-symbols-outlined text-accent text-[20px] fill-1">hub</span>
           <p className="text-[11px] text-text-muted uppercase tracking-[0.2em] font-bold">Knowledge Matrix</p>
        </div>
        
        <div className="bg-bg-surface border border-border-light rounded-[32px] p-6 shadow-soft space-y-6">
          <div className="flex justify-between items-center pb-4 border-b border-border-light">
            <span className="text-[13px] font-bold text-text-ink">Health Status</span>
            <span className="font-mono text-[16px] font-bold text-status-success">{healthScore}%</span>
          </div>
          <div className="flex justify-between items-center pb-4 border-b border-border-light">
            <span className="text-[13px] font-bold text-text-ink">Active Issues</span>
            <span className="font-mono text-[16px] font-bold text-status-warning">{findingsCount}</span>
          </div>
          <div className="flex justify-between items-center pb-4 border-b border-border-light">
            <span className="text-[13px] font-bold text-text-ink">Reward Leak</span>
            <span className="font-mono text-[16px] font-bold text-status-danger">₹{missedRewards.toLocaleString()}</span>
          </div>
          <div className="pt-2">
             <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-accent shadow-glow" />
                <p className="text-[11px] text-text-muted uppercase font-bold tracking-widest">Active Analysis</p>
             </div>
             <p className="text-[12px] text-text-body leading-relaxed italic opacity-80">
               "Guardian is currently prioritizing your high-severity subscription leaks."
             </p>
          </div>
        </div>

        {/* Suggestion Chips */}
        <div className="flex flex-col gap-3">
           <p className="text-[10px] text-text-muted uppercase font-bold tracking-widest px-2 mb-1">Inquiry Shortcuts</p>
           {[
             "How to save ₹2,000 this month?",
             "Compare my top 3 categories",
             "Analyze my Zomato spend trend"
           ].map((txt, i) => (
             <button 
               key={i} 
               onClick={() => setInput(txt)}
               className="text-left px-5 py-3 rounded-2xl bg-bg-subtle border border-border-light text-[12px] font-semibold text-text-ink hover:bg-bg-hover hover:border-accent/20 transition-all"
             >
               {txt}
             </button>
           ))}
        </div>
      </aside>

      {/* Chat Interface Area */}
      <section className="flex-1 flex flex-col relative h-full">
        
        {/* Messages Scroll View */}
        <div className="flex-1 overflow-y-auto pr-4 pb-32 space-y-8 custom-scrollbar">
          <AnimatePresence>
            {messages.map((msg, idx) => (
              <motion.div 
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} w-full`}
              >
                <div className={`text-[15px] leading-relaxed max-w-[85%] ${
                  msg.role === 'user' 
                    ? 'bg-accent text-white rounded-[24px] rounded-br-none px-6 py-4 shadow-glow' 
                    : 'bg-bg-subtle text-text-ink rounded-[24px] rounded-tl-none border border-border-light px-6 py-4 shadow-soft'
                }`}>
                  <div className={`prose prose-sm max-w-none ${msg.role === 'user' ? 'prose-invert' : ''}`}>
                    <ReactMarkdown>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                  {!analysis && idx === 0 && msg.role === 'assistant' && (
                    <button 
                      onClick={() => document.querySelector('[data-upload-trigger="true"]')?.click()}
                      className="mt-6 flex items-center gap-2 bg-text-ink text-white px-6 py-3 rounded-xl font-bold text-[13px] hover:bg-accent transition-all shadow-glow active:scale-95 uppercase tracking-widest"
                    >
                      <span className="material-symbols-outlined text-[18px]">sync</span>
                      Sync Transactions
                    </button>
                  )}
                </div>
                {msg.source && (
                  <div className="flex items-center gap-1.5 mt-3 ml-2 opacity-60">
                    <span className="material-symbols-outlined text-[14px]">auto_awesome</span>
                    <span className="text-[10px] text-text-muted uppercase font-bold tracking-widest">
                      {msg.source} Agent
                    </span>
                  </div>
                )}
              </motion.div>
            ))}
            
            {isLoading && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-start w-full space-y-3"
              >
                <div className="px-6 py-4 rounded-[24px] rounded-tl-none bg-bg-subtle border border-border-light shadow-soft flex flex-col gap-3 min-w-[200px]">
                  <div className="flex gap-1.5 items-center">
                    <div className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce" />
                    <div className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce delay-100" />
                    <div className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce delay-200" />
                    <span className="text-[11px] text-text-muted uppercase font-bold tracking-[0.2em] ml-2">Thinking</span>
                  </div>
                  
                  {/* Technical Status Cycle */}
                  <div className="flex flex-col gap-1.5">
                    <StatusCycle />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>

        {/* Input Dock (Reference 2 style) */}
        <div className="absolute bottom-0 left-0 right-0 pt-10 pb-4 bg-gradient-to-t from-bg-surface via-bg-surface to-transparent">
          <form onSubmit={handleSubmit} className="relative group">
            <input 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              className="w-full bg-white border border-border-mid focus:border-accent focus:ring-4 focus:ring-accent/5 text-text-ink text-[16px] py-5 pl-8 pr-20 rounded-[32px] outline-none transition-all placeholder:text-text-muted shadow-card" 
              placeholder="Ask anything about your money..." 
              type="text"
            />
            <button 
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-3 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-accent text-white flex items-center justify-center hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:bg-border-strong shadow-glow"
            >
              <span className="material-symbols-outlined text-[24px] font-bold fill-1">arrow_upward</span>
            </button>
          </form>
          <p className="text-[11px] text-text-muted text-center mt-4 opacity-60">
            Guardian can make mistakes. Verify critical financial data.
          </p>
        </div>

      </section>
    </div>
  );
}
