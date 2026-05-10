import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

function FindingCard({ finding, isResolved = false, onResolve, onUndo }) {
  const navigate = useNavigate();
  const getSeverityStyle = (severity) => {
    switch(severity) {
      case 'high': return { text: 'text-status-danger', bg: 'bg-status-danger/10', border: 'border-status-danger/20', icon: 'error' };
      case 'medium': return { text: 'text-status-warning', bg: 'bg-status-warning/10', border: 'border-status-warning/20', icon: 'warning' };
      default: return { text: 'text-status-success', bg: 'bg-status-success/10', border: 'border-status-success/20', icon: 'check_circle' };
    }
  };
  
  const style = getSeverityStyle(finding.severity);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`group relative bg-bg-surface border border-border-light rounded-[32px] p-8 shadow-soft hover:shadow-card hover:border-accent/10 transition-all duration-300 mb-6 ${isResolved ? 'opacity-50 grayscale' : ''}`}
    >
      <div className="flex justify-between items-start mb-6">
        <div className="flex items-center gap-5">
          <div className={`w-14 h-14 rounded-2xl ${style.bg} flex items-center justify-center ${style.text} shadow-inner`}>
            <span className="material-symbols-outlined text-[28px] fill-1">{style.icon}</span>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] font-black uppercase tracking-[0.15em] ${style.text}`}>
                {finding.severity || 'LOW'} PRIORITY
              </span>
              <span className="w-1 h-1 rounded-full bg-border-mid" />
              <span className="text-text-muted text-[10px] uppercase font-black tracking-[0.15em]">
                {finding.type?.replace('_', ' ') || 'AUDIT'}
              </span>
            </div>
            <h4 className="text-[20px] font-black text-text-ink leading-tight tracking-tight">
              {finding.merchant || finding.title || 'Audit Observation'}
            </h4>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {(finding.rupee_impact > 0 || finding.monthly_cost > 0) && (
            <div className="text-right">
              <p className="text-[24px] font-mono font-black text-text-ink tracking-tighter leading-none">
                ₹{Math.round(finding.rupee_impact || finding.monthly_cost).toLocaleString()}
              </p>
              <p className="text-[10px] text-text-muted uppercase font-black tracking-widest mt-1.5">Impact / MO</p>
            </div>
          )}

          {isResolved ? (
             <button 
               onClick={() => onUndo(finding.id || finding.merchant || finding.title)}
               className="w-12 h-12 rounded-2xl bg-white border border-border-light flex items-center justify-center text-text-muted hover:text-accent hover:border-accent/30 transition-all shadow-soft shrink-0"
               title="Undo Resolution"
             >
               <span className="material-symbols-outlined text-[20px]">undo</span>
             </button>
          ) : (
             <button 
               onClick={() => onResolve(finding.id || finding.merchant || finding.title)}
               className="w-12 h-12 rounded-2xl bg-bg-subtle border border-border-light flex items-center justify-center text-text-muted hover:text-status-success hover:border-status-success/30 transition-all shadow-soft shrink-0"
               title="Mark as Resolved"
             >
               <span className="material-symbols-outlined text-[20px]">done</span>
             </button>
          )}
        </div>
      </div>

      <p className="text-[15px] text-text-body leading-relaxed mb-8 pl-[76px] font-medium opacity-80">
        {finding.explanation || finding.observation || finding.summary || 'Strategic insight derived from automated audit analysis.'}
      </p>

      {!isResolved && (finding.action || finding.suggestion) && (
        <div className="ml-[76px] p-6 bg-bg-subtle rounded-[24px] flex flex-col md:flex-row md:items-center justify-between gap-6 border border-border-light">
          <div className="flex-1">
            <p className="text-[11px] text-text-muted uppercase font-black tracking-[0.1em] mb-2">Guardian Recommended Action</p>
            <p className="text-[14px] text-text-ink font-bold leading-relaxed">{finding.action || finding.suggestion}</p>
          </div>
          <button 
            onClick={() => {
              if (finding.type === 'reward') navigate('/rewards');
              else if (finding.type === 'behavioural') navigate('/budget');
              else if (finding.type === 'subscription') {
                alert(`Guardian Tip: To resolve ${finding.merchant || 'this'}, login to the service provider's portal or your banking app and cancel the recurring mandate.`);
              }
            }}
            className="px-6 py-3 bg-text-ink text-white text-[12px] font-black uppercase tracking-widest rounded-xl hover:bg-accent transition-all shadow-glow shrink-0 active:scale-95"
          >
            Execute Strategy
          </button>
        </div>
      )}
    </motion.div>
  );
}

export default function Findings() {
  const [analysis, setAnalysis] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all');
  const [isResolvedOpen, setIsResolvedOpen] = useState(false);
  const [resolvedIds, setResolvedIds] = useState([]);

  useEffect(() => {
    const stored = sessionStorage.getItem('GUARDIAN_ANALYSIS');
    if (stored) setAnalysis(JSON.parse(stored));
    
    const storedResolved = localStorage.getItem('GUARDIAN_RESOLVED_IDS');
    if (storedResolved) setResolvedIds(JSON.parse(storedResolved));
  }, []);

  const handleResolve = (id) => {
    const newResolved = [...resolvedIds, id];
    setResolvedIds(newResolved);
    localStorage.setItem('GUARDIAN_RESOLVED_IDS', JSON.stringify(newResolved));
  };

  const handleUndo = (id) => {
    const newResolved = resolvedIds.filter(rid => rid !== id);
    setResolvedIds(newResolved);
    localStorage.setItem('GUARDIAN_RESOLVED_IDS', JSON.stringify(newResolved));
  };

  if (!analysis) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="w-24 h-24 rounded-[32px] bg-bg-surface border border-border-light flex items-center justify-center mb-8 shadow-soft"
        >
          <span className="material-symbols-outlined text-text-muted text-[40px] fill-1">troubleshoot</span>
        </motion.div>
        <h3 className="text-[28px] font-black text-text-ink mb-3 tracking-tight">Audit Log Empty</h3>
        <p className="text-[16px] text-text-body max-w-sm mb-10 leading-relaxed">
          Upload your latest financial statements to generate a comprehensive audit of leaks and opportunities.
        </p>
      </div>
    );
  }

  const insightFindings = (analysis.insight_findings || []).map(f => ({ ...f, type: 'insight' }));
  const rewardFindings = (analysis.reward_findings || []).map(f => ({ 
    ...f, 
    type: 'reward',
    rupee_impact: f.total_missed_monthly,
    explanation: f.summary,
    action: "Switch to the recommended card in the Reward Optimiser."
  }));
  const behaviouralFindings = (analysis.budget_goals_report?.behavioural_goal_impacts || []).map(f => ({ 
    ...f, 
    type: 'behavioural',
    title: f.behaviour,
    explanation: f.suggestion,
    severity: 'medium'
  }));

  const allFindings = [...insightFindings, ...rewardFindings, ...behaviouralFindings].map((f, i) => ({ ...f, id: f.id || `f-${i}` }));
  
  const activeFindings = allFindings.filter(f => !resolvedIds.includes(f.id || f.merchant || f.title));
  const resolvedFindings = allFindings.filter(f => resolvedIds.includes(f.id || f.merchant || f.title));
  
  const filteredFindings = activeFilter === 'all' ? activeFindings : activeFindings.filter(f => f.type === activeFilter);
  const filteredResolved = activeFilter === 'all' ? resolvedFindings : resolvedFindings.filter(f => f.type === activeFilter);

  return (
    <div className="flex-1 flex flex-col pb-24 px-4 sm:px-0">
      
      {/* Header Info */}
      <div className="mt-6 mb-12">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center text-white shadow-glow">
            <span className="material-symbols-outlined text-[18px] fill-1">shield_with_heart</span>
          </div>
          <p className="text-[12px] text-text-muted uppercase tracking-[0.2em] font-black">Audit Intelligence</p>
        </div>
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-8">
          <h2 className="text-[42px] font-black text-text-ink tracking-tight leading-none">
            {filteredFindings.length} Insights Detected
          </h2>
          <div className="flex flex-wrap gap-2">
            {['all', 'insight', 'reward', 'behavioural'].map(f => (
              <button
                key={f}
                onClick={() => setActiveFilter(f)}
                className={`px-5 py-2.5 rounded-[18px] text-[11px] font-black uppercase tracking-widest transition-all border ${
                  activeFilter === f 
                    ? 'bg-text-ink text-white border-text-ink shadow-card' 
                    : 'bg-white text-text-muted border-border-light hover:border-accent/30 hover:text-text-ink'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-[1000px]">
        <AnimatePresence mode="popLayout">
          {filteredFindings.length === 0 ? (
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="py-24 text-center bg-bg-surface rounded-[40px] border border-border-light shadow-soft"
            >
              <p className="text-[14px] text-text-muted font-bold italic">No findings match this audit category.</p>
            </motion.div>
          ) : (
            <div className="flex flex-col">
              {filteredFindings.sort((a,b) => {
                 const rank = { high: 0, medium: 1, low: 2 };
                 return (rank[a.severity] || 2) - (rank[b.severity] || 2);
              }).map((f, i) => (
                <FindingCard key={`${activeFilter}-${i}`} finding={f} onResolve={handleResolve} />
              ))}
            </div>
          )}
        </AnimatePresence>

        {/* Resolved Section */}
        <div className="mt-16 bg-bg-subtle rounded-[40px] p-10 border border-border-light">
          <button 
            onClick={() => setIsResolvedOpen(!isResolvedOpen)}
            className="flex items-center justify-between w-full group"
          >
            <div className="flex items-center gap-5">
               <div className="w-12 h-12 rounded-2xl bg-white flex items-center justify-center text-status-success shadow-soft border border-border-light">
                  <span className="material-symbols-outlined text-[24px] fill-1">verified_user</span>
               </div>
               <div className="text-left">
                  <p className="text-[16px] font-black text-text-ink">Resolved History</p>
                  <p className="text-[11px] text-text-muted uppercase font-black tracking-widest mt-0.5">Audit Archive</p>
               </div>
            </div>
            <div className={`w-10 h-10 rounded-full bg-white flex items-center justify-center border border-border-light shadow-soft transition-transform duration-300 ${isResolvedOpen ? 'rotate-180' : ''}`}>
              <span className="material-symbols-outlined text-[24px] text-text-muted">expand_more</span>
            </div>
          </button>
          
          <AnimatePresence>
            {isResolvedOpen && (
              <motion.div 
                initial={{ height: 0, opacity: 0 }} 
                animate={{ height: 'auto', opacity: 1 }} 
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="pt-10 space-y-6">
                  {filteredResolved.length > 0 ? filteredResolved.map((f, i) => (
                    <FindingCard key={`resolved-${i}`} finding={f} isResolved={true} onUndo={handleUndo} />
                  )) : (
                    <p className="text-[13px] text-text-muted font-bold italic text-center py-10 opacity-50">No resolved findings in this category.</p>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
