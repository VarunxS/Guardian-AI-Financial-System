import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

// Reusable Typewriter effect for the terminal
const TypewriterText = ({ text }) => {
   const [displayText, setDisplayText] = useState('');

   useEffect(() => {
      let i = 0;
      setDisplayText('');
      const intervalId = setInterval(() => {
         setDisplayText(text.slice(0, i + 1));
         i++;
         if (i >= text.length) clearInterval(intervalId);
      }, 40);
      return () => clearInterval(intervalId);
   }, [text]);

   return <span>{displayText}</span>;
};

export default function Landing() {
   const terminalText = `Initializing Guardian Pipeline...
Loading embeddings: sentence-transformers/all-MiniLM-L6-v2... OK.
Connecting to ChromaDB... OK.
Verifying LLM keys (GPT-4o / Gemini 2.5)... OK.

[AGENT: INSIGHTS_AGENT] Analyzing transactions for anomalies...
> Found recurring spikes: HDFC Home Loan (₹24.5k -> ₹29.8k).
> Found double charge: Swiggy (₹847).

[AGENT: CARD_DB_AGENT] Semantic retrieval (k=8)...
> Top Match: HDFC Infinia (Super Premium)
> Comparison: Axis Atlas vs Infinia for travel spend.

[AGENT: LIVE_RESEARCH_AGENT] Querying Exa AI Neural Search...
> Found latest 2025 reward multiplier for Axis Atlas.
> Cross-referencing RBI Master Circulars...

[AGENT: BUDGET_GOALS] Forecasting scenarios...
> Royal Enfield target: 14 months (Current)
> Action: Re-allocate ₹3,500/mo dining -> savings.
> New timeline: 11.2 months.

Pipeline complete. Ready for chat.`;

   return (
      <div className="min-h-screen bg-bg-canvas font-sans text-text-ink overflow-x-hidden selection:bg-accent/10 selection:text-accent relative pb-32">

         {/* Mesh/Dot Background Effect */}
         <div className="fixed inset-0 pointer-events-none" style={{ backgroundImage: 'radial-gradient(var(--border-mid) 1px, transparent 1px)', backgroundSize: '32px 32px' }} />

         {/* Navigation */}
         <nav className="fixed top-0 left-0 right-0 h-24 flex items-center justify-between px-10 md:px-20 z-50 bg-bg-canvas/80 backdrop-blur-md border-b border-border-light">
            <div className="flex items-center gap-3">
               <div className="w-10 h-10 rounded-xl bg-accent flex items-center justify-center text-white shadow-glow">
                  <span className="material-symbols-outlined text-[24px] font-bold">shield</span>
               </div>
               <span className="font-bold text-[22px] tracking-tight">Guardian</span>
            </div>
            <div className="flex items-center gap-8">
               <a href="#pipeline" className="text-[13px] font-bold text-text-muted hover:text-text-ink transition-colors uppercase tracking-widest hidden md:block">Pipeline</a>
               <a href="#agents" className="text-[13px] font-bold text-text-muted hover:text-text-ink transition-colors uppercase tracking-widest hidden md:block">Agents</a>
               <Link to="/dashboard" className="h-11 px-6 bg-text-ink text-white rounded-xl text-[13px] font-bold hover:bg-accent transition-all shadow-soft flex items-center justify-center">
                  Enter Console
               </Link>
            </div>
         </nav>

         {/* SECTION 1: HERO */}
         <main className="relative z-10 min-h-[calc(100vh-96px)] mt-24 px-10 md:px-20 max-w-[1300px] mx-auto flex flex-col xl:flex-row items-center justify-center gap-12 pb-16">
            <div className="absolute top-[10%] left-[-5%] w-[600px] h-[600px] bg-accent/5 blur-[120px] rounded-full pointer-events-none -z-10" />

            <div className="flex-1">
               <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="inline-flex items-center gap-2 bg-white border border-border-mid px-4 py-1.5 rounded-full shadow-soft mb-6">
                  <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
                  <span className="text-[11px] font-bold uppercase tracking-widest text-text-body">Local AI Analysis Pipeline</span>
               </motion.div>

               <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="text-[48px] md:text-[64px] lg:text-[72px] font-extrabold tracking-tight leading-[1] mb-6">
                  Your AI <br />Financial <br />Immune System
               </motion.h1>

               <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="border-l-4 border-accent pl-5 mb-8 max-w-[480px]">
                  <p className="text-[16px] text-text-body leading-relaxed">
                     Guardian analyses your bank statements using a multi-agent AI pipeline detecting financial anomalies, optimising credit card rewards, and building personalised savings plans toward your goals.
                  </p>
               </motion.div>

               <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="flex flex-col sm:flex-row gap-4">
                  <Link to="/dashboard" className="h-14 px-8 bg-accent text-white rounded-xl text-[15px] font-bold hover:bg-accent-hover transition-all shadow-glow flex items-center justify-center gap-2">
                     Run Local Analysis
                  </Link>
                  <a href="https://github.com/VarunxS/Guardian-AI-Financial-System" target="_blank" rel="noreferrer" className="h-14 px-8 bg-white border border-border-mid text-text-ink rounded-xl text-[15px] font-bold hover:bg-bg-subtle transition-all shadow-soft flex items-center justify-center gap-2">
                     <span className="material-symbols-outlined text-[20px]">grade</span>
                     Star on GitHub
                  </a>
               </motion.div>
            </div>

            <motion.div
               initial={{ opacity: 0, rotateY: 10, rotateX: 5 }}
               animate={{ opacity: 1, rotateY: -5, rotateX: 2 }}
               transition={{ delay: 0.4, duration: 1 }}
               className="flex-1 w-full max-w-[540px] perspective-1000"
            >
               <div className="bg-[#111827] border border-white/10 rounded-2xl p-5 shadow-[0_20px_40px_rgba(0,0,0,0.15)] shadow-accent/10 transition-transform hover:rotate-0 duration-500">
                  <div className="flex gap-2 mb-3">
                     <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F56]" />
                     <div className="w-2.5 h-2.5 rounded-full bg-[#FFBD2E]" />
                     <div className="w-2.5 h-2.5 rounded-full bg-[#27C93F]" />
                  </div>
                  <div className="font-mono text-[12px] text-border-mid whitespace-pre-wrap leading-relaxed min-h-[280px]">
                     <TypewriterText text={terminalText} />
                     <span className="inline-block w-2 h-[1em] bg-border-mid ml-1 animate-pulse align-middle" />
                  </div>
               </div>
            </motion.div>
         </main>

         {/* SECTION 2: BYOK & PRIVACY */}
         <section className="py-24 px-10 md:px-20 max-w-[1400px] mx-auto border-t border-border-light relative z-10">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
               <motion.div whileInView={{ opacity: 1, y: 0 }} initial={{ opacity: 0, y: 20 }} viewport={{ once: true }} className="bg-white p-8 rounded-3xl border border-border-mid shadow-soft">
                  <div className="text-[13px] font-mono text-text-muted mb-4 border border-border-mid inline-block px-2 py-0.5 rounded">01</div>
                  <h3 className="text-[20px] font-bold mb-3">Configure your LLM</h3>
                  <p className="text-text-body text-[15px] leading-relaxed mb-6">Guardian supports a BYOK (Bring Your Own Key) architecture with a dynamic <code>llm_factory</code>. Choose between GPT-4o, Gemini 2.5, or Mistral for agent reasoning.</p>
                  <div className="bg-bg-canvas font-mono text-[12px] p-3 rounded-xl border border-border-mid text-text-muted">sk-proj-••••••••••••••••••••••</div>
               </motion.div>

               <motion.div whileInView={{ opacity: 1, y: 0 }} initial={{ opacity: 0, y: 20 }} transition={{ delay: 0.1 }} viewport={{ once: true }} className="bg-white p-8 rounded-3xl border border-border-mid shadow-soft">
                  <div className="text-[13px] font-mono text-text-muted mb-4 border border-border-mid inline-block px-2 py-0.5 rounded">02</div>
                  <h3 className="text-[20px] font-bold mb-3">Export bank statement</h3>
                  <p className="text-text-body text-[15px] leading-relaxed mb-6">Download your transaction history from your net banking portal. Guardian accepts CSVs and PDFs.</p>
                  <ul className="space-y-3 text-[14px] font-medium">
                     <li className="flex items-center gap-2"><span className="text-accent material-symbols-outlined text-[18px]">check</span> Bank CSV (SBI, HDFC, ICICI, Axis)</li>
                     <li className="flex items-center gap-2"><span className="text-accent material-symbols-outlined text-[18px]">check</span> Credit card PDF statements</li>
                  </ul>
               </motion.div>

               <motion.div whileInView={{ opacity: 1, y: 0 }} initial={{ opacity: 0, y: 20 }} transition={{ delay: 0.2 }} viewport={{ once: true }} className="bg-white p-8 rounded-3xl border border-border-mid shadow-soft">
                  <div className="text-[13px] font-mono text-text-muted mb-4 border border-border-mid inline-block px-2 py-0.5 rounded">03</div>
                  <h3 className="text-[20px] font-bold mb-3">Tell Guardian your goals</h3>
                  <p className="text-text-body text-[15px] leading-relaxed mb-6">Enter your monthly income and what you're saving for. Guardian calculates how your spending decisions affect each timeline.</p>
                  <div className="bg-bg-canvas p-4 rounded-xl border border-border-mid text-[12px] font-mono">
                     Royal Enfield Classic 350 <br />
                     Target: ₹2,10,000 <br />
                     <div className="w-full bg-border-mid h-2 mt-2 rounded overflow-hidden flex"><div className="w-1/3 bg-accent h-full" /></div>
                  </div>
               </motion.div>
            </div>
         </section>

         {/* SECTION 3: ARCHITECTURE */}
         <section id="pipeline" className="py-24 px-10 md:px-20 max-w-[1400px] mx-auto text-center relative z-10 overflow-hidden bg-white/50 rounded-[64px] border border-border-light my-20">
            {/* Subtle Grid Background for this section only */}
            <div className="absolute inset-0 pointer-events-none opacity-[0.03]" style={{ backgroundImage: 'linear-gradient(var(--border-mid) 1px, transparent 1px), linear-gradient(90deg, var(--border-mid) 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

            <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} className="relative z-10">
               <motion.h2 whileInView={{ opacity: 1, y: 0 }} initial={{ opacity: 0, y: 20 }} viewport={{ once: true }} className="text-[40px] font-extrabold tracking-tight mb-4">
                  Neural Architecture
               </motion.h2>
               <p className="text-text-muted text-[18px] font-bold uppercase tracking-[0.2em] mb-20 opacity-60">Multi-Agent Orchestration & RAG Pipeline</p>

               <div className="flex flex-col items-center gap-10 relative scale-[0.95] origin-top">
                  
                  {/* Data Ingestion Layer */}
                  <motion.div whileHover={{ y: -5 }} className="bg-white/80 backdrop-blur-md border border-border-light p-8 rounded-[40px] shadow-sm w-[360px] relative z-20 group transition-all hover:border-accent/30">
                     <div className="flex items-center gap-4 mb-4">
                        <div className="w-10 h-10 rounded-2xl bg-accent/10 text-accent flex items-center justify-center group-hover:bg-accent group-hover:text-white transition-colors">
                           <span className="material-symbols-outlined text-[20px] fill-1">upload_file</span>
                        </div>
                        <div className="text-left">
                           <h4 className="font-bold text-[15px] text-text-ink">Semantic Data Extraction</h4>
                           <p className="text-[10px] text-accent font-black uppercase tracking-widest mt-0.5">Ingestion Pipeline</p>
                        </div>
                     </div>
                     <p className="text-[12px] text-text-body text-left leading-relaxed font-semibold opacity-70">PyMuPDF-enhanced OCR pipeline converting raw PDF/CSV blobs into structured JSON.</p>
                  </motion.div>


                  {/* Supervisor Node */}
                  <div className="relative group flex flex-col items-center">
                     {/* Technical Probes Left */}
                     <div className="absolute -left-[320px] top-1/2 -translate-y-1/2 hidden xl:flex flex-col gap-6 text-left w-[260px]">
                        <motion.div whileHover={{ x: 5 }} className="p-5 bg-white/80 backdrop-blur-md border-l-4 border-accent rounded-r-2xl shadow-sm">
                           <p className="text-[10px] font-black text-accent uppercase tracking-widest mb-1.5">State Engine</p>
                           <p className="text-[12px] text-text-ink font-bold leading-relaxed">LangGraph recursive state propagation with persistent profile memory.</p>
                        </motion.div>
                        <motion.div whileHover={{ x: 5 }} className="p-5 bg-white/80 backdrop-blur-md border-l-4 border-[#3B82F6] rounded-r-2xl shadow-sm">
                           <p className="text-[10px] font-black text-[#3B82F6] uppercase tracking-widest mb-1.5">Parallel RAG</p>
                           <p className="text-[12px] text-text-ink font-bold leading-relaxed">Async concurrent retrieval across 3 vector collections and live web agents.</p>
                        </motion.div>
                     </div>

                     <motion.div whileInView={{ opacity: 1, scale: 1 }} initial={{ opacity: 0, scale: 0.95 }} viewport={{ once: true }} className="bg-white/80 backdrop-blur-xl border border-accent/20 p-10 rounded-[48px] shadow-soft w-[500px] relative z-20 overflow-hidden hover:border-accent/40 transition-colors group">
                        <div className="absolute top-0 right-0 w-48 h-48 bg-accent/5 rounded-full blur-[80px] -mr-24 -mt-24 group-hover:bg-accent/10 transition-colors" />
                        <div className="flex items-center gap-5 mb-5 relative z-10">
                           <div className="w-14 h-14 rounded-2xl bg-accent text-white flex items-center justify-center shadow-[0_0_20px_rgba(255,87,51,0.3)]">
                              <span className="material-symbols-outlined text-[28px] fill-1">neurology</span>
                           </div>
                           <div className="text-left">
                              <h4 className="font-extrabold text-[20px] text-text-ink leading-tight tracking-tight">Neural RAG Router</h4>
                              <p className="text-[11px] text-accent uppercase font-black tracking-[0.2em] mt-1.5">Autonomous Context Arbitrator</p>
                           </div>
                        </div>
                        <p className="text-[14px] text-text-body text-left leading-relaxed font-bold opacity-70 relative z-10">High-fidelity classification, dynamic provider detection, and multi-source context synthesis across LLM clusters.</p>
                     </motion.div>

                     {/* Technical Probes Right */}
                     <div className="absolute -right-[320px] top-1/2 -translate-y-1/2 hidden xl:flex flex-col gap-6 text-left w-[260px]">
                        <motion.div whileHover={{ x: -5 }} className="p-5 bg-white/80 backdrop-blur-md border-r-4 border-accent rounded-l-2xl shadow-sm text-right">
                           <p className="text-[10px] font-black text-accent uppercase tracking-widest mb-1.5">BYOK Inference</p>
                           <p className="text-[12px] text-text-ink font-bold leading-relaxed">Multi-provider routing (OpenRouter, Gemini, OpenAI) with prefix detection.</p>
                        </motion.div>
                     </div>

                  </div>

                  {/* Branching Agents */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mt-10 w-full relative z-20">
                     {[
                        { id: '01', name: 'Insights Agent', tech: 'Anomaly Detection', icon: 'search_insights' },
                        { id: '02', name: 'Card Database Agent', tech: 'Semantic Retrieval', icon: 'credit_card' },
                        { id: '03', name: 'Live Research Agent', tech: 'Exa AI Neural Search', icon: 'language' },
                        { id: '04', name: 'Budget & Goals', tech: 'Math Forecasting', icon: 'monitoring' }
                     ].map((agent, i) => (
                        <motion.div 
                           key={agent.id}
                           whileHover={{ y: -8, scale: 1.01 }} 
                           className="bg-white/60 backdrop-blur-md border border-border-light p-8 rounded-[40px] shadow-sm hover:border-accent/30 hover:shadow-glow/5 transition-all group"
                        >
                           <div className="w-12 h-12 rounded-2xl bg-accent/5 text-accent flex items-center justify-center mb-5 group-hover:bg-accent group-hover:text-white transition-all">
                              <span className="material-symbols-outlined text-[22px]">{agent.icon}</span>
                           </div>
                           <div className="text-[10px] font-black text-accent uppercase tracking-[0.25em] mb-2 opacity-40">Node {agent.id}</div>
                           <h4 className="font-extrabold mb-3 text-[16px] text-text-ink group-hover:text-accent transition-colors">{agent.name}</h4>
                           <div className="h-0.5 w-6 bg-accent/10 mb-4 group-hover:w-12 transition-all" />
                           <p className="text-[10px] text-text-body leading-relaxed font-bold opacity-50 uppercase tracking-widest">{agent.tech}</p>
                        </motion.div>
                     ))}
                  </div>


                  {/* RAG Layer */}
                  <motion.div whileHover={{ scale: 1.02 }} className="bg-white/60 backdrop-blur-md border border-border-light p-10 rounded-[48px] shadow-sm w-[480px] mt-10 group transition-all hover:border-accent/30">
                     <div className="flex items-center gap-4 mb-4 justify-center">
                        <div className="w-10 h-10 rounded-xl bg-accent/5 text-accent border border-accent/10 flex items-center justify-center group-hover:bg-accent group-hover:text-white transition-all">
                           <span className="material-symbols-outlined text-[20px]">database</span>
                        </div>
                        <h4 className="font-extrabold text-[16px] text-text-ink tracking-tight">ChromaDB Vector Persistence</h4>
                     </div>
                     <p className="text-[12px] text-text-body font-bold leading-relaxed opacity-60 px-4">Persistent context storage utilizing local semantic embeddings for stateful multi-turn reasoning.</p>
                  </motion.div>
               </div>
            </motion.div>
         </section>

          {/* SECTION 4: EXPLORE CARDS */}
          <section id="explore" className="py-32 px-10 md:px-20 max-w-[1400px] mx-auto relative z-10">
             <div className="flex flex-col lg:flex-row items-center gap-20">
                <motion.div whileInView={{ opacity: 1, x: 0 }} initial={{ opacity: 0, x: -30 }} viewport={{ once: true }} className="flex-1 text-left">
                   <div className="w-12 h-12 rounded-2xl bg-accent/10 text-accent flex items-center justify-center mb-6">
                      <span className="material-symbols-outlined text-[24px]">explore</span>
                   </div>
                   <h2 className="text-[48px] font-extrabold tracking-tight mb-6 leading-tight">
                      Deep Card <span className="text-accent">Exploration</span> Engine
                   </h2>
                   <p className="text-[18px] text-text-body leading-relaxed mb-8 font-medium opacity-80">
                      Access a curated, semantic database of the world's most exclusive credit cards. Compare rewards, fees, and real-world returns with 99.9% data fidelity.
                   </p>
                   <ul className="space-y-4 mb-10">
                      {['Real-time Reward Simulation', 'Semantic Perk Comparison', 'Hidden Fee Discovery'].map((item, i) => (
                         <li key={i} className="flex items-center gap-3 text-[15px] font-bold text-text-ink">
                            <div className="w-1.5 h-1.5 rounded-full bg-accent" />
                            {item}
                         </li>
                      ))}
                   </ul>
                   <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="bg-accent text-white px-10 py-5 rounded-3xl font-black text-[14px] uppercase tracking-widest shadow-glow/20">
                      Explore the Catalog
                   </motion.button>
                </motion.div>
                <motion.div whileInView={{ opacity: 1, scale: 1 }} initial={{ opacity: 0, scale: 0.9 }} viewport={{ once: true }} className="flex-1 relative">
                   <div className="absolute inset-0 bg-accent/5 rounded-[64px] blur-[100px] -z-10" />
                   <img 
                      src="/assets/card-mockup.png" 
                      alt="Premium Credit Card" 
                      className="w-full rounded-[48px] shadow-soft border border-white/20"
                   />
                </motion.div>
             </div>
          </section>


         {/* SECTION 6: AGENTS UI MOCKUPS */}
         <section id="agents" className="py-24 px-10 md:px-20 max-w-[1400px] mx-auto relative z-10 border-t border-border-light">
            <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-24">
               <h2 className="text-[40px] font-extrabold tracking-tight mb-4">Autonomous Agent Clusters</h2>
               <p className="text-text-muted text-[16px] font-bold uppercase tracking-[0.2em] opacity-60">Specialized intelligence for every financial vertical</p>
            </motion.div>
            {/* Agent 1 */}
            <div className="flex flex-col lg:flex-row items-center gap-16 mb-32">
               <motion.div whileInView={{ opacity: 1, x: 0 }} initial={{ opacity: 0, x: -30 }} viewport={{ once: true }} className="flex-1">
                  <span className="bg-accent/10 text-accent font-bold text-[12px] px-3 py-1 rounded-full tracking-wider uppercase mb-4 inline-block">Agent 01</span>
                  <h3 className="text-[32px] font-bold mb-4 tracking-tight">Insights Agent</h3>
                  <p className="text-[16px] text-text-body leading-relaxed mb-6">Identifies unusual spikes, recurring anomalies, and potential liabilities like EMIs or utility increases across your entire transaction history.</p>
                  <div className="flex flex-wrap gap-2">
                     <span className="bg-bg-subtle text-[12px] font-mono px-3 py-1.5 rounded-lg border border-border-mid">Anomaly detection</span>
                     <span className="bg-bg-subtle text-[12px] font-mono px-3 py-1.5 rounded-lg border border-border-mid">Merchant mapping</span>
                  </div>
               </motion.div>
               <motion.div whileInView={{ opacity: 1, x: 0 }} initial={{ opacity: 0, x: 30 }} viewport={{ once: true }} className="flex-1 w-full max-w-[600px]">
                  {/* Realistic Mock UI */}
                  <div className="bg-white border border-border-mid rounded-3xl p-6 shadow-soft font-sans">
                     <div className="border-l-4 border-[#F59E0B] bg-bg-canvas p-4 rounded-r-xl mb-4">
                        <div className="flex justify-between items-center mb-1">
                           <span className="font-bold flex items-center gap-1"><span className="text-[#F59E0B] material-symbols-outlined text-[16px]">bolt</span> Medium</span>
                           <span className="font-bold">₹1,499</span>
                        </div>
                        <div className="text-[11px] font-bold text-text-muted uppercase tracking-widest mb-3">HEADSPACE + CULT.FIT · DUPLICATE</div>
                        <p className="text-[14px] text-text-body">Both are in the health category, costing a combined ₹1,998/month. Cult.fit is ₹1,499 more expensive.</p>
                     </div>
                     <div className="border-l-4 border-[#EF4444] bg-bg-canvas p-4 rounded-r-xl">
                        <div className="flex justify-between items-center mb-1">
                           <span className="font-bold flex items-center gap-1"><span className="text-[#EF4444] material-symbols-outlined text-[16px]">error</span> High</span>
                           <span className="font-bold">₹847</span>
                        </div>
                        <div className="text-[11px] font-bold text-text-muted uppercase tracking-widest mb-3">SWIGGY · DOUBLE PAYMENT</div>
                        <p className="text-[14px] text-text-body">₹847 charged twice within 18 hours on 14 March.</p>
                     </div>
                  </div>
               </motion.div>
            </div>

            {/* Agent 2 */}
            <div className="flex flex-col lg:flex-row-reverse items-center gap-16 mb-32">
               <motion.div whileInView={{ opacity: 1, x: 0 }} initial={{ opacity: 0, x: 30 }} viewport={{ once: true }} className="flex-1">
                  <span className="bg-accent/10 text-accent font-bold text-[12px] px-3 py-1 rounded-full tracking-wider uppercase mb-4 inline-block">Agent 02</span>
                  <h3 className="text-[32px] font-bold mb-4 tracking-tight">Reward Optimiser</h3>
                  <p className="text-[16px] text-text-body leading-relaxed mb-6">Breaks down your exact category spend (e.g. 40% dining, 30% travel) and simulates returns across a live database of Indian credit cards.</p>
               </motion.div>
               <motion.div whileInView={{ opacity: 1, x: 0 }} initial={{ opacity: 0, x: -30 }} viewport={{ once: true }} className="flex-1 w-full max-w-[600px]">
                  <div className="bg-white border border-border-mid rounded-3xl p-6 shadow-soft font-mono text-[13px]">
                     <div className="flex justify-between items-center mb-6">
                        <span className="font-bold">✦ Reward Optimiser</span>
                        <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-text-ink" /> Agent Synced</span>
                     </div>
                     <div className="mb-4">
                        <div className="text-text-muted mb-1">PRIMARY CARD</div>
                        <div className="font-bold text-[15px]">ICICI Amazon Pay Credit Card</div>
                        <div className="text-text-muted">Best for: shopping · groceries</div>
                     </div>
                     <div className="border-t border-border-light my-4" />
                     <div className="grid grid-cols-3 gap-4">
                        <div>
                           <div className="text-text-muted mb-1">MONTHLY REWARD</div>
                           <div className="font-bold">₹549</div>
                        </div>
                        <div>
                           <div className="text-text-muted mb-1">ANNUAL FEE</div>
                           <div className="font-bold">₹3,500</div>
                        </div>
                        <div>
                           <div className="text-text-muted mb-1">NET YEARLY GAIN</div>
                           <div className="font-bold">₹3,087</div>
                        </div>
                     </div>
                  </div>
               </motion.div>
            </div>

            {/* Agent 3 */}
            <div className="flex flex-col lg:flex-row items-center gap-16">
               <motion.div whileInView={{ opacity: 1, x: 0 }} initial={{ opacity: 0, x: -30 }} viewport={{ once: true }} className="flex-1">
                  <span className="bg-accent/10 text-accent font-bold text-[12px] px-3 py-1 rounded-full tracking-wider uppercase mb-4 inline-block">Agent 03</span>
                  <h3 className="text-[32px] font-bold mb-4 tracking-tight">Budget & Goals Agent</h3>
                  <p className="text-[16px] text-text-body leading-relaxed mb-6">The strategic engine driven by <strong>Math-First Intelligence</strong>. Python handles deterministic forecasting while a single LLM call interprets behavioral impact.</p>
               </motion.div>
               <motion.div whileInView={{ opacity: 1, x: 0 }} initial={{ opacity: 0, x: 30 }} viewport={{ once: true }} className="flex-1 w-full max-w-[600px]">
                  <div className="bg-white border border-border-mid rounded-3xl p-6 shadow-soft font-mono text-[13px]">
                     <div className="flex justify-between items-center mb-2">
                        <span className="font-bold text-[15px]">🎯 Royal Enfield Classic 350</span>
                        <span className="text-accent">achievable</span>
                     </div>
                     <div className="text-text-muted mb-4">₹2,10,000 target · ₹34,000 saved · 16% there</div>

                     <div className="h-3 w-full border border-border-mid rounded-full overflow-hidden mb-6 flex">
                        <div className="w-[16%] bg-accent h-full" />
                        <div className="flex-1" style={{ backgroundImage: 'radial-gradient(var(--border-mid) 1px, transparent 1px)', backgroundSize: '4px 4px' }} />
                     </div>

                     <div className="space-y-2 mb-6">
                        <div className="flex justify-between"><span className="text-text-muted">At current pace</span><span className="font-bold">14.0 months</span></div>
                        <div className="flex justify-between"><span className="text-text-muted">Balanced month</span><span><span className="font-bold">11.2 months</span> <span className="text-accent text-[11px] ml-2">← -84 days</span></span></div>
                        <div className="flex justify-between"><span className="text-text-muted">Conservative</span><span><span className="font-bold">9.1 months</span> <span className="text-accent text-[11px] ml-2">← -147 days</span></span></div>
                     </div>

                     <div className="border-t border-border-light pt-4">
                        <div className="text-text-muted mb-2 uppercase tracking-widest text-[11px]">Biggest Lever</div>
                        <p>Cut <span className="bg-bg-canvas px-1 border border-border-mid rounded">food_dining</span> ₹6,999 → ₹3,500 this month.</p>
                        <p>Moves goal from 14 to 11.2 months.</p>
                     </div>
                  </div>
               </motion.div>
            </div>
         </section>

         {/* SECTION 5: TECH STACK */}
         <section className="py-24 px-10 md:px-20 bg-white border-y border-border-light relative z-10">
            <div className="max-w-[1000px] mx-auto text-center">
               <h2 className="text-[32px] font-extrabold mb-12">The Guardian Tech Stack</h2>

               <div className="bg-bg-canvas border border-border-mid rounded-3xl p-8 shadow-inner text-left max-w-[800px] mx-auto">
                  <div className="grid grid-cols-[150px_1fr] gap-4 py-3 border-b border-border-light">
                     <div className="font-bold text-[13px] text-text-muted uppercase tracking-widest">Orchestration</div>
                     <div className="font-mono text-[14px]">LangGraph · Parallel Async RAG · Supabase</div>
                  </div>
                  <div className="grid grid-cols-[150px_1fr] gap-4 py-3 border-b border-border-light">
                     <div className="font-bold text-[13px] text-text-muted uppercase tracking-widest">Inference (BYOK)</div>
                     <div className="font-mono text-[14px]">GPT-4o · Gemini 2.5 · OpenRouter · Mistral</div>
                  </div>
                  <div className="grid grid-cols-[150px_1fr] gap-4 py-3 border-b border-border-light">
                     <div className="font-bold text-[13px] text-text-muted uppercase tracking-widest">Web Research</div>
                     <div className="font-mono text-[14px]">Exa AI (Neural Search Engine)</div>
                  </div>
                  <div className="grid grid-cols-[150px_1fr] gap-4 py-3 border-b border-border-light">
                     <div className="font-bold text-[13px] text-text-muted uppercase tracking-widest">Vector Store</div>
                     <div className="font-mono text-[14px]">ChromaDB (Persistent Semantic Embeddings)</div>
                  </div>
                  <div className="grid grid-cols-[150px_1fr] gap-4 py-3 border-b border-border-light">
                     <div className="font-bold text-[13px] text-text-muted uppercase tracking-widest">Backend</div>
                     <div className="font-mono text-[14px]">FastAPI + Python 3.11 (Async Concurrency)</div>
                  </div>
                  <div className="grid grid-cols-[150px_1fr] gap-4 py-3 border-b border-border-light">
                     <div className="font-bold text-[13px] text-text-muted uppercase tracking-widest">Database</div>
                     <div className="font-mono text-[14px]">Supabase (PostgreSQL + Profile Cache)</div>
                  </div>
                  <div className="grid grid-cols-[150px_1fr] gap-4 py-3 border-b border-border-light">
                     <div className="font-bold text-[13px] text-text-muted uppercase tracking-widest">Frontend</div>
                     <div className="font-mono text-[14px]">React 19 · Vite · Framer Motion · Tailwind</div>
                  </div>
                  <div className="grid grid-cols-[150px_1fr] gap-4 py-3">
                     <div className="font-bold text-[13px] text-text-muted uppercase tracking-widest">Privacy</div>
                     <div className="font-mono text-[14px]">Encrypted local processing · No data reselling</div>
                  </div>
               </div>
            </div>
         </section>

         {/* SECTION 6: FOOTER / BUILDER */}
         <footer className="pt-24 pb-12 px-10 md:px-20 max-w-[1400px] mx-auto text-center relative z-10">
            <div className="bg-accent text-white p-12 rounded-[40px] shadow-glow flex flex-col items-center justify-center max-w-[800px] mx-auto mb-16">
               <h2 className="text-[32px] md:text-[48px] font-extrabold mb-4 tracking-tight">Take control of your capital.</h2>
               <p className="text-[16px] md:text-[18px] mb-8 text-white/90 max-w-[540px]">Stop leaking money to financial anomalies and unoptimized reward loops. Run the local Guardian pipeline today.</p>
               <Link to="/dashboard" className="h-16 px-10 bg-white text-accent rounded-2xl text-[16px] font-bold hover:scale-105 transition-all flex items-center justify-center gap-3 shadow-[0_10px_20px_rgba(0,0,0,0.1)]">
                  Enter Console <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
               </Link>
            </div>

            <div className="flex flex-col items-center justify-center mb-12 border border-border-light bg-white rounded-3xl p-8 max-w-[600px] mx-auto shadow-soft">
               <div className="text-[11px] font-bold text-text-muted uppercase tracking-widest mb-2">Architected & Engineered By</div>
               <div className="text-[24px] font-extrabold text-text-ink mb-6">Varun Singla</div>
               
               <div className="flex flex-wrap items-center justify-center gap-4">
                  <a href="https://varun-singla-portfolio.vercel.app" target="_blank" rel="noreferrer" className="h-11 px-5 bg-text-ink text-white rounded-xl text-[14px] font-bold hover:bg-accent transition-all shadow-soft flex items-center gap-2">
                     <span className="material-symbols-outlined text-[18px]">language</span> Portfolio
                  </a>
                  <a href="https://www.linkedin.com/in/varun-singla-0b1744291/" target="_blank" rel="noreferrer" className="h-11 px-5 bg-[#0A66C2] text-white rounded-xl text-[14px] font-bold hover:bg-[#004182] transition-all shadow-soft flex items-center gap-2">
                     LinkedIn
                  </a>
                  <button 
                     onClick={(e) => {
                        navigator.clipboard.writeText('varunsingla608@gmail.com');
                        e.currentTarget.querySelector('.email-text').textContent = 'Copied!';
                        setTimeout(() => e.currentTarget.querySelector('.email-text').textContent = 'varunsingla608@gmail.com', 2000);
                     }}
                     className="group h-11 px-5 bg-white border border-border-mid text-text-ink rounded-xl text-[14px] font-bold hover:bg-bg-subtle transition-all shadow-soft flex items-center justify-center cursor-pointer relative w-[130px] hover:w-[260px]"
                     title="Click to copy"
                  >
                     <div className="flex items-center gap-2 absolute transition-opacity duration-300 opacity-100 group-hover:opacity-0 group-hover:pointer-events-none">
                        <span className="material-symbols-outlined text-[18px]">mail</span> 
                        <span>Contact</span>
                     </div>
                     <div className="flex items-center gap-2 absolute transition-opacity duration-300 opacity-0 group-hover:opacity-100 whitespace-nowrap">
                        <span className="material-symbols-outlined text-[16px]">content_copy</span> 
                        <span className="text-[13px] email-text">varunsingla608@gmail.com</span>
                     </div>
                  </button>
               </div>
            </div>

            <div className="text-[12px] md:text-[13px] text-text-muted font-bold uppercase tracking-widest flex flex-col md:flex-row flex-wrap justify-center items-center gap-3 md:gap-4">
               <span>© 2026 Guardian AI</span>
               <span className="hidden md:inline">·</span>
               <a href="https://github.com/VarunxS/Guardian-AI-Financial-System" target="_blank" rel="noreferrer" className="hover:text-accent transition-colors flex items-center gap-1">
                 <span className="material-symbols-outlined text-[16px]">code</span> GitHub Repository
               </a>
            </div>
         </footer>
      </div>
   );
}
