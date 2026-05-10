import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { getUserId } from '../utils/auth';
import { API_BASE_URL } from '../config';

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } }
};

// Animated Number Component
const AnimatedNumber = ({ value, prefix = '', suffix = '' }) => {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let start = 0;
    const end = parseFloat(value);
    if (isNaN(end)) return;
    
    const duration = 1500;
    const startTime = performance.now();

    const animate = (currentTime) => {
      const elapsedTime = currentTime - startTime;
      const progress = Math.min(elapsedTime / duration, 1);
      const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setDisplayValue(Math.floor(easeProgress * end));

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setDisplayValue(end);
      }
    };

    requestAnimationFrame(animate);
  }, [value]);

  return <span>{prefix}{displayValue.toLocaleString('en-IN')}{suffix}</span>;
};

// SVG Arc Component for Health Score
const HealthScoreArc = ({ score, colorClass }) => {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - ((score || 0) / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center">
      <svg width="72" height="72" className="-rotate-90 shrink-0">
        <circle cx="36" cy="36" r={radius} stroke="#F1F5F9" strokeWidth="5" fill="none" />
        <motion.circle
          cx="36"
          cy="36"
          r={radius}
          className={colorClass}
          stroke="currentColor"
          strokeWidth="5"
          fill="none"
          strokeLinecap="round"
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.8, ease: [0.16, 1, 0.3, 1], delay: 0.5 }}
          strokeDasharray={circumference}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
         <p className={`text-[16px] font-mono font-black ${colorClass.replace('text-', 'text-opacity-100 text-')}`}>{score}</p>
      </div>
    </div>
  );
};

export default function Dashboard() {
  const [analysis, setAnalysis] = useState(null);
  const [profile, setProfile] = useState({ monthly_income: 0, goals: [] });

  useEffect(() => {
    const stored = sessionStorage.getItem('GUARDIAN_ANALYSIS');
    if (stored) setAnalysis(JSON.parse(stored));
    fetch(`${API_BASE_URL}/api/user/${getUserId()}/context`)
      .then(r => r.json())
      .then(data => setProfile(data))
      .catch(() => {});
  }, []);

  if (!analysis) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="w-24 h-24 rounded-[32px] bg-bg-surface border border-border-light flex items-center justify-center mb-8 shadow-soft"
        >
          <span className="material-symbols-outlined text-accent text-[40px] fill-1">shield_with_heart</span>
        </motion.div>
        <h3 className="text-[28px] font-black text-text-ink mb-3 tracking-tight">Guardian Initialization</h3>
        <p className="text-[16px] text-text-body max-w-md mb-10 leading-relaxed font-medium opacity-70">
          Upload your financial statements to activate the Guardian engine and receive deep behavioral insights.
        </p>
        <button 
          onClick={() => document.querySelector('[data-upload-trigger]')?.click()}
          className="bg-text-ink text-white px-10 py-4.5 rounded-[20px] font-black text-[14px] shadow-card hover:bg-accent transition-all active:scale-95 uppercase tracking-widest"
        >
          Begin Audit
        </button>
      </div>
    );
  }

  const budgetReport = analysis?.budget_goals_report || analysis?.financial_consultant_report || {};
  const raw = budgetReport.raw || {};
  const forecast = raw.budget_forecast || { by_category: {}, total: 0 };
  const liveIncome = profile.monthly_income || 0;
  const liveGoals = profile.goals || [];
  const hasLiveProfile = liveIncome > 0 && liveGoals.length > 0;
  const hasFullReport = !budgetReport.error && budgetReport.goal_cards?.length > 0;
  // Only show "Context Required" if user truly has no profile
  const isBudgetError = !hasLiveProfile && !hasFullReport;
  const computedSurplus = liveIncome - (forecast.total || 0);
  const computedHealth = computedSurplus > liveIncome * 0.3 ? 'strong' : computedSurplus > 0 ? 'tight' : 'negative';
  const budgetSummary = hasFullReport ? (budgetReport.budget_summary || {}) : {
    forecasted_surplus: computedSurplus,
    surplus_health: computedHealth,
    one_line_verdict: hasLiveProfile ? `₹${Math.round(computedSurplus).toLocaleString()} monthly surplus detected.` : ''
  };
  const categories = Object.entries(forecast.by_category)
    .filter(([cat]) => !['transfer', 'investment'].includes(cat))
    .map(([cat, val]) => ({ category: cat, monthly_spend: val, pct_of_total: (val / (forecast.total || 1)) * 100 }))
    .sort((a, b) => b.monthly_spend - a.monthly_spend);
  
  const reward = analysis?.reward_findings?.[0] || {};
  const findings = analysis?.ranked_findings || [];
  const totalFindings = analysis?.findings_count || 0;
  const highCount = findings.filter(f => f.severity === 'high').length;
  const medCount = findings.filter(f => f.severity === 'medium').length;

  const getHealthColor = (score) => {
    if (score >= 80) return 'text-status-success';
    if (score >= 50) return 'text-status-warning';
    return 'text-status-danger';
  };

  return (
    <div className="flex-1 flex flex-col min-h-full pb-16 px-4 sm:px-0">
      
      {/* Page Header */}
      <section className="mt-4 mb-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8">
          <div className="max-w-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center text-white shadow-glow">
                <span className="material-symbols-outlined text-[16px] fill-1">insights</span>
              </div>
              <p className="text-[12px] text-text-muted uppercase tracking-[0.25em] font-black">Strategic Intelligence</p>
            </div>
            <h2 className="text-[32px] font-black text-text-ink tracking-tight leading-[1.05] mb-2">
              Portfolio Health Verdict
            </h2>
            <p className="text-[13px] text-text-body font-bold leading-relaxed opacity-60 max-w-xl">
              {(analysis.executive_summary && !analysis.executive_summary.toLowerCase().includes('provide income'))
                ? analysis.executive_summary
                : hasLiveProfile
                  ? `₹${Math.round(computedSurplus).toLocaleString()} monthly surplus detected across ${Object.keys(forecast.by_category).length} spending categories.`
                  : "Automated analysis complete across 3 concurrent AI intelligence nodes."
              }
            </p>
          </div>
          
          <div className="flex items-center gap-4 bg-white border border-border-light rounded-xl p-2.5 shadow-soft pr-6 group hover:border-accent/30 transition-all cursor-default">
             <HealthScoreArc score={analysis.health_score} colorClass={getHealthColor(analysis.health_score)} />
             <div>
                <p className="text-[11px] text-text-muted uppercase font-black tracking-widest mb-1.5 opacity-60">Composite Grade</p>
                <p className="text-[18px] font-black text-text-ink leading-none tracking-tight">
                  {analysis.health_score >= 80 ? 'Excellent' : analysis.health_score >= 50 ? 'Stabilized' : 'High Risk'}
                </p>
             </div>
          </div>
        </div>

        {/* Primary Analysis Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Main Hero: Surplus Strategy */}
          <motion.div 
            variants={itemVariants}
            initial="hidden" animate="show"
            className="lg:col-span-6 bg-text-ink text-white rounded-[28px] p-6 shadow-card relative overflow-hidden group min-h-[300px] flex flex-col justify-between"
          >
            {/* Glossy Mesh Gradients */}
            <div className="absolute top-0 right-0 w-full h-full bg-[radial-gradient(circle_at_top_right,rgba(var(--color-accent-rgb),0.25),transparent_60%)] pointer-events-none" />
            <div className="absolute -bottom-40 -left-40 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[120px]" />
            
            <div className="relative z-10 h-full flex flex-col">
               {isBudgetError ? (
                <div className="flex-1 flex flex-col justify-center items-center text-center max-w-sm mx-auto py-6">
                   <div className="w-16 h-16 rounded-[24px] bg-white/5 flex items-center justify-center mb-6 border border-white/10 shadow-inner">
                      <span className="material-symbols-outlined text-accent text-[28px] fill-1">account_balance_wallet</span>
                   </div>
                   <h3 className="text-[22px] font-black mb-3 tracking-tight">Context Required</h3>
                   <p className="text-[13px] text-white/60 font-bold mb-8 leading-relaxed">
                     Guardian needs your income and goals to calculate your monthly surplus and reaching-date projections.
                   </p>
                   <Link to="/budget" className="bg-white text-text-ink px-8 py-3.5 rounded-[16px] text-[12px] font-black uppercase tracking-widest hover:bg-accent hover:text-white transition-all shadow-glow active:scale-95">
                      Set Income & Goals
                   </Link>
                </div>
              ) : (
                <>
                  <div className="flex justify-between items-start mb-8">
                    <div>
                      <div className="flex items-center gap-3 mb-5">
                        <div className="w-2.5 h-2.5 rounded-full bg-accent shadow-glow animate-pulse" />
                        <p className="text-[13px] font-black uppercase tracking-[0.2em] text-white/40">Projected Monthly Surplus</p>
                      </div>
                      <h3 className="text-[56px] font-mono font-black leading-none tracking-tighter shadow-glow-lg">
                        <AnimatedNumber value={computedSurplus} prefix="₹" />
                      </h3>
                    </div>
                    <div className="bg-white/5 backdrop-blur-2xl px-5 py-3 rounded-2xl border border-white/10 text-right shadow-card">
                       <p className="text-[11px] uppercase font-black text-white/30 mb-2 tracking-widest">Surplus Health</p>
                       <p className="text-[14px] font-black text-accent tracking-widest">{computedHealth.toUpperCase()}</p>
                    </div>
                  </div>

                  {/* Goal Progress Snapshots */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                    {liveGoals.map(g => ({
                      goal_name: g.name,
                      progress_pct: Math.round(((g.saved_amount || 0) / g.target_amount) * 100)
                    })).slice(0, 3).map((goal, idx) => (
                      <div key={idx} className="bg-white/5 backdrop-blur-xl px-5 py-4 rounded-2xl border border-white/5 group-hover:bg-white/10 transition-all hover:border-white/20 shadow-soft">
                        <div className="flex justify-between items-start mb-5">
                           <p className="text-[11px] uppercase font-black text-white/40 truncate pr-3 tracking-[0.1em]">{goal.goal_name}</p>
                           <span className="text-[13px] font-mono font-black text-accent">{goal.progress_pct}%</span>
                        </div>
                        <div className="w-full bg-white/5 h-2.5 rounded-full overflow-hidden border border-white/5 p-1">
                           <motion.div 
                             initial={{ width: 0 }}
                             animate={{ width: `${goal.progress_pct}%` }}
                             className="bg-accent h-full rounded-full shadow-glow"
                           />
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {!isBudgetError && (
              <div className="relative z-10 flex flex-col sm:flex-row justify-between items-end gap-6 pt-6 border-t border-white/10">
                 <div className="max-w-lg">
                   <p className="text-[13px] text-white/90 leading-relaxed font-bold italic opacity-80">
                     "{budgetSummary.one_line_verdict || "Guardian is currently forecasting your next month's cashflow based on historical patterns."}"
                   </p>
                 </div>
                 <Link to="/budget" className="bg-white text-text-ink px-6 py-3 rounded-xl text-[12px] font-black uppercase tracking-widest hover:bg-accent hover:text-white transition-all shadow-glow active:scale-95 flex items-center gap-3 shrink-0">
                    Strategy Hub <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
                 </Link>
              </div>
            )}
          </motion.div>

          {/* Right Action Column */}
          <div className="lg:col-span-6 grid grid-cols-1 sm:grid-cols-2 gap-6">
            {/* Risk Card */}
            <motion.div variants={itemVariants} className="bg-bg-surface border border-border-light rounded-[24px] p-5 shadow-soft hover:shadow-card transition-all flex flex-col h-full group overflow-hidden relative">
              <div className="absolute top-0 right-0 w-40 h-40 bg-status-danger/5 rounded-full blur-3xl -mr-20 -mt-20" />
              <div className="flex justify-between items-start mb-6 relative z-10">
                <p className="text-[13px] text-text-muted uppercase font-black tracking-[0.2em]">Risk Exposure</p>
                <div className="w-9 h-9 rounded-xl bg-status-danger/10 text-status-danger flex items-center justify-center shadow-soft border border-status-danger/10">
                  <span className="material-symbols-outlined text-[20px] fill-1">verified_user</span>
                </div>
              </div>
              <div className="flex items-baseline gap-3 mb-4 relative z-10">
                <h4 className="text-[32px] font-mono font-black text-text-ink leading-none tracking-tighter">
                  <AnimatedNumber value={analysis.findings_count} />
                </h4>
                <span className="text-[12px] text-text-muted font-black tracking-widest uppercase opacity-60">Insights</span>
              </div>
              <div className="flex gap-2 h-4 rounded-full overflow-hidden bg-bg-subtle mb-6 border border-border-light p-1 relative z-10 shadow-inner">
                 <div className="bg-status-danger h-full rounded-full shadow-glow-danger" style={{ width: `${totalFindings ? (highCount/totalFindings)*100 : 0}%` }} />
                 <div className="bg-status-warning h-full rounded-full" style={{ width: `${totalFindings ? (medCount/totalFindings)*100 : 0}%` }} />
                 <div className="bg-status-success h-full flex-1 rounded-full opacity-30" />
              </div>
              <Link to="/findings" className="mt-auto w-full py-2.5 bg-bg-subtle hover:bg-text-ink text-text-ink hover:text-white text-[11px] font-black uppercase tracking-widest rounded-xl transition-all flex items-center justify-center gap-2 border border-border-light group-hover:border-transparent active:scale-95 shadow-soft">
                Audit Log <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
              </Link>
            </motion.div>

            {/* Reward Card */}
            <motion.div variants={itemVariants} className="bg-bg-surface border border-border-light rounded-[24px] p-5 shadow-soft hover:shadow-card transition-all flex flex-col h-full group overflow-hidden relative">
               <div className="absolute top-0 right-0 w-40 h-40 bg-accent/5 rounded-full blur-3xl -mr-20 -mt-20" />
               <div className="flex justify-between items-start mb-6 relative z-10">
                <p className="text-[13px] text-text-muted uppercase font-black tracking-[0.2em]">Portfolio Yield</p>
                <div className="w-9 h-9 rounded-xl bg-accent/10 text-accent flex items-center justify-center shadow-soft border border-accent/10">
                  <span className="material-symbols-outlined text-[20px] fill-1">auto_awesome</span>
                </div>
              </div>
              <div className="flex items-baseline gap-3 mb-2 relative z-10">
                <h4 className="text-[32px] font-mono font-black text-accent leading-none tracking-tighter">
                  ₹<AnimatedNumber value={reward.total_missed_monthly || analysis.total_monthly_at_risk || 0} />
                </h4>
                <span className="text-[12px] text-text-muted font-black tracking-widest uppercase opacity-60">Leaking</span>
              </div>
              <p className="text-[11px] text-text-body font-bold mb-4 opacity-60 leading-relaxed relative z-10">
                {reward?.top_pick?.name 
                  ? `Guardian identified ${reward.top_pick.name} as your optimal node for this pattern.` 
                  : `Untapped strategic value detected across ${reward.category_breakdown?.length || 0} distinct spending nodes.`}
              </p>
              <Link to="/rewards" className="mt-auto w-full py-2.5 bg-accent text-white text-[11px] font-black uppercase tracking-widest rounded-xl transition-all flex items-center justify-center gap-2 shadow-glow hover:shadow-glow-lg active:scale-95">
                Optimize Stack
              </Link>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Secondary Data Layer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-4">
        
        {/* Behavioral Audit */}
        <div className="lg:col-span-7 space-y-6">
          <div className="flex items-center justify-between mb-2 px-4">
             <h4 className="text-[18px] font-black text-text-ink tracking-tight">Behavioral Friction Analysis</h4>
             <div className="flex items-center gap-3 bg-bg-surface border border-border-light px-5 py-2 rounded-2xl shadow-soft">
                <span className="w-2 h-2 rounded-full bg-status-danger animate-pulse" />
                <span className="text-[11px] text-text-muted uppercase font-black tracking-widest">Active Leaks</span>
             </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {budgetReport.behavioural_goal_impacts?.length > 0 ? (
              budgetReport.behavioural_goal_impacts.map((impact, idx) => (
                <motion.div 
                  key={idx} 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.15, duration: 0.8 }}
                  className="bg-white border border-border-light rounded-[24px] p-6 shadow-soft group hover:border-status-danger/40 transition-all border-l-[6px] border-l-status-danger relative overflow-hidden"
                >
                  <div className="absolute top-0 right-0 w-32 h-32 bg-status-danger/5 rounded-full blur-3xl -mr-16 -mt-16" />
                  <div className="flex items-center gap-4 mb-5 relative z-10">
                     <div className="w-12 h-12 rounded-xl bg-status-danger/10 text-status-danger flex flex-col items-center justify-center leading-none shadow-inner border border-status-danger/10">
                       <span className="text-[16px] font-black">-{impact.days_cost}</span>
                       <span className="text-[10px] font-black uppercase mt-1 opacity-60">days</span>
                     </div>
                     <div>
                        <h5 className="text-[14px] font-black text-text-ink tracking-tight">{impact.behaviour}</h5>
                        <p className="text-[12px] text-text-muted font-black uppercase tracking-widest mt-1.5 opacity-60">{impact.goal_name}</p>
                     </div>
                  </div>
                  <p className="text-[12px] text-text-body leading-relaxed font-bold opacity-80 relative z-10">
                    {impact.suggestion}
                  </p>
                </motion.div>
              ))
            ) : (
              <div className="col-span-2 py-12 bg-bg-surface border border-dashed border-border-light rounded-[24px] flex flex-col items-center justify-center text-center px-8 shadow-inner">
                 <div className="w-14 h-14 rounded-2xl bg-bg-subtle flex items-center justify-center mb-5 border border-border-light">
                    <span className="material-symbols-outlined text-text-muted text-[28px] opacity-20 fill-1">verified</span>
                 </div>
                 <h5 className="text-[14px] font-black text-text-ink mb-2">Optimal Behavior Patterns</h5>
                 <p className="text-[12px] text-text-muted font-bold leading-relaxed max-w-sm opacity-60">
                   Guardian analyzed your lifestyle spending and detected zero friction points affecting your strategic goal timelines.
                 </p>
              </div>
            )}
          </div>
        </div>

        {/* Forecast Allocation */}
        <div className="lg:col-span-5 space-y-6">
          <div className="flex items-center justify-between mb-2 px-4">
             <h4 className="text-[18px] font-black text-text-ink tracking-tight">Projected Exposure</h4>
             <span className="text-[12px] text-text-muted uppercase font-black tracking-widest opacity-60">Weighted Allocation</span>
          </div>

          <div className="bg-bg-surface border border-border-light rounded-[28px] p-8 shadow-soft relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-48 h-48 bg-accent/5 rounded-full blur-[80px]" />
            <div className="flex items-end justify-between gap-6 h-52 mb-8 pt-6 relative z-10">
              {categories.length > 0 ? (
                categories.slice(0, 4).map((c, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center group/bar h-full">
                    <div className="w-full relative flex flex-col justify-end h-full">
                      <motion.div 
                        initial={{ height: 0 }}
                        animate={{ height: `${c.pct_of_total}%` }}
                        transition={{ duration: 1.8, ease: [0.16, 1, 0.3, 1], delay: i * 0.2 }}
                        className={`w-full rounded-xl transition-all group-hover/bar:scale-[1.05] cursor-pointer relative z-10 border border-white/20 shadow-soft ${
                          i === 0 ? 'bg-accent shadow-glow' : i === 1 ? 'bg-text-ink' : i === 2 ? 'bg-status-warning' : 'bg-bg-subtle'
                        }`}
                      />
                      {/* Tooltip */}
                      <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-full mb-4 opacity-0 group-hover/bar:opacity-100 transition-all scale-90 group-hover/bar:scale-100 whitespace-nowrap bg-text-ink text-white text-[11px] font-black px-4 py-2 rounded-xl z-20 shadow-card border border-white/10">
                        ₹{Math.round(c.monthly_spend).toLocaleString()} <span className="text-accent ml-2">{c.pct_of_total.toFixed(1)}%</span>
                      </div>
                    </div>
                    <p className="text-[10px] text-text-muted font-black uppercase tracking-[0.15em] mt-6 truncate w-full text-center group-hover/bar:text-text-ink transition-colors duration-300">
                      {c.category.replace('_', ' ')}
                    </p>
                  </div>
                ))
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-center">
                  <div className="w-14 h-14 rounded-full bg-bg-subtle flex items-center justify-center mb-6">
                    <span className="material-symbols-outlined text-[28px] text-text-muted opacity-30 animate-pulse">monitoring</span>
                  </div>
                  <p className="text-text-muted text-[13px] font-black uppercase tracking-[0.3em] italic opacity-30">Awaiting Telemetry</p>
                </div>
              )}
            </div>
            <div className="pt-6 border-t border-border-light flex justify-between items-center relative z-10">
               <span className="text-[11px] text-text-muted font-black uppercase tracking-widest opacity-60">Total Forecasted Volume</span>
               <span className="text-[18px] font-mono font-black text-text-ink tracking-tighter">₹{Math.round(forecast.total || 0).toLocaleString()}</span>
            </div>
          </div>
        </div>

      </div>

      {/* Strategic Action Center */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-4 px-4">
           <h4 className="text-[18px] font-black text-text-ink tracking-tight">Strategic Action Center</h4>
           <span className="text-[12px] text-text-muted uppercase font-black tracking-widest opacity-60">Intelligence Hub</span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card Optimizer Teaser */}
          <Link to="/rewards" className="bg-bg-surface border border-border-light rounded-[24px] p-6 shadow-soft hover:shadow-card hover:border-accent/40 transition-all group flex flex-col justify-between min-h-[220px]">
            <div>
              <div className="w-10 h-10 rounded-xl bg-accent/10 text-accent flex items-center justify-center mb-4">
                <span className="material-symbols-outlined fill-1">credit_card</span>
              </div>
              <h5 className="text-[16px] font-black text-text-ink tracking-tight mb-2">Reward Optimizer</h5>
              <p className="text-[13px] text-text-body font-bold opacity-70 leading-relaxed">
                {reward?.top_pick?.name ? `Guardian identified ${reward.top_pick.name} could save you ₹${Math.round(reward.total_missed_annual || 0).toLocaleString()}/yr based on your actual spend.` : "Discover the exact credit card that maximizes your unique spending habits."}
              </p>
            </div>
            <div className="flex items-center gap-2 text-[12px] font-black uppercase tracking-widest text-accent mt-6 group-hover:translate-x-1 transition-transform">
              Explore Cards <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </div>
          </Link>

          {/* Goal Agent Teaser */}
          <Link to="/budget" className="bg-bg-surface border border-border-light rounded-[24px] p-6 shadow-soft hover:shadow-card hover:border-text-ink/40 transition-all group flex flex-col justify-between min-h-[220px]">
            <div>
              <div className="w-10 h-10 rounded-xl bg-text-ink/10 text-text-ink flex items-center justify-center mb-4">
                <span className="material-symbols-outlined fill-1">flag</span>
              </div>
              <h5 className="text-[16px] font-black text-text-ink tracking-tight mb-2">Budget & Goals Agent</h5>
              <p className="text-[13px] text-text-body font-bold opacity-70 leading-relaxed">
                Visualize how your daily spending patterns impact your timeline for {liveGoals?.length > 0 ? liveGoals[0].name : "your long-term financial goals"}.
              </p>
            </div>
            <div className="flex items-center gap-2 text-[12px] font-black uppercase tracking-widest text-text-ink mt-6 group-hover:translate-x-1 transition-transform">
              Visualize Progress <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </div>
          </Link>

          {/* Chatbot Teaser */}
          <Link to="/chat" className="bg-bg-surface border border-border-light rounded-[24px] p-6 shadow-soft hover:shadow-card hover:border-[#0A66C2]/40 transition-all group flex flex-col justify-between min-h-[220px]">
            <div>
              <div className="w-10 h-10 rounded-xl bg-[#0A66C2]/10 text-[#0A66C2] flex items-center justify-center mb-4">
                <span className="material-symbols-outlined fill-1">chat_bubble</span>
              </div>
              <h5 className="text-[16px] font-black text-text-ink tracking-tight mb-2">Ask Guardian</h5>
              <p className="text-[13px] text-text-body font-bold opacity-70 leading-relaxed">
                Have specific questions? Ask Guardian to analyze your top categories, explain financial concepts, or compare cards.
              </p>
            </div>
            <div className="flex items-center gap-2 text-[12px] font-black uppercase tracking-widest text-[#0A66C2] mt-6 group-hover:translate-x-1 transition-transform">
              Start Conversation <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
