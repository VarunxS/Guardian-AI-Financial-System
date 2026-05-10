import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import UploadModal from '../components/UploadModal';

export default function BudgetGoals() {
  const [analysis, setAnalysis] = useState(null);
  const [profile, setProfile] = useState({ monthly_income: 0, goals: [] });
  const [loading, setLoading] = useState(true);
  const [editGoal, setEditGoal] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [status, setStatus] = useState({ type: '', msg: '' });

  useEffect(() => {
    const stored = sessionStorage.getItem('GUARDIAN_ANALYSIS');
    if (stored) setAnalysis(JSON.parse(stored));
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/user/user_123/context');
      const data = await res.json();
      setProfile(data);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const showToast = (type, msg) => {
    setStatus({ type, msg });
    setTimeout(() => setStatus({ type: '', msg: '' }), 3000);
  };

  const handleUpdateGoal = async (e) => {
    e.preventDefault();
    try {
      await fetch('http://localhost:8000/api/goals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'user_123',
          goal_id: editGoal.goal_id,
          name: editForm.name,
          target_amount: parseFloat(editForm.target) || 0,
          saved_amount: parseFloat(editForm.saved) || 0,
          priority: editForm.priority || 'Medium'
        })
      });
      setEditGoal(null);
      fetchProfile();
      showToast('success', 'Goal updated');
    } catch { showToast('error', 'Failed to update goal'); }
  };

  const handleDeleteGoal = async (goalId) => {
    try {
      await fetch(`http://localhost:8000/api/goals/${goalId}`, { method: 'DELETE' });
      setEditGoal(null);
      fetchProfile();
      showToast('success', 'Goal removed');
    } catch { showToast('error', 'Failed to remove goal'); }
  };

  const openEdit = (goal) => {
    setEditGoal(goal);
    setEditForm({
      name: goal.name,
      target: goal.target_amount,
      saved: goal.saved_amount || 0,
      priority: goal.surplus_pct >= 0.5 ? 'High' : goal.surplus_pct >= 0.3 ? 'Medium' : 'Low'
    });
  };

  // Data extraction
  const liveGoals = profile.goals || [];
  const liveIncome = profile.monthly_income || 0;
  const hasProfile = liveIncome > 0 && liveGoals.length > 0;

  // Handle re-running the agent
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const handleRunAgent = async () => {
    if (!hasAnalysisData) {
      setIsUploadOpen(true);
      return;
    }

    const apiKey = localStorage.getItem('GUARDIAN_API_KEY');
    if (!apiKey) {
      showToast('error', 'Please configure your API Key in Settings first.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/goals/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'user_123',
          api_key: apiKey,
          budget_forecast: forecast,
          behavioural_impacts: analysis?.budget_goals_report?.raw?.behavioural_impacts || []
        })
      });

      if (!res.ok) throw new Error('Analysis failed');

      const report = await res.json();
      
      // Update session storage and state
      const updatedAnalysis = { ...analysis, budget_goals_report: report };
      sessionStorage.setItem('GUARDIAN_ANALYSIS', JSON.stringify(updatedAnalysis));
      setAnalysis(updatedAnalysis);
      showToast('success', 'Strategy updated');
    } catch (err) {
      showToast('error', 'Failed to run agent');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveIncome = async () => {
    try {
      await fetch('http://localhost:8000/api/user/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'user_123', monthly_income: parseFloat(profile.monthly_income) || 0 })
      });
      showToast('success', 'Monthly income updated');
      fetchProfile();
    } catch (err) {
      showToast('error', 'Failed to update income');
    }
  };

  // Use analysis data even if budget_goals_report had "missing_profile" error
  const report = analysis?.budget_goals_report || {};
  const raw = report.raw || {};
  const forecast = raw.budget_forecast || analysis?.budget_goals_report?.raw?.budget_forecast || { by_category: {}, total: 0 };
  const hasAnalysisData = !!analysis && (analysis.insight_findings?.length > 0 || analysis.reward_findings?.length > 0 || Object.keys(forecast.by_category || {}).length > 0);

  // If budget report ran successfully (no error), use its goal_cards
  const hasFullReport = !!report && !report.error && report.goal_cards?.length > 0;
  const goalCards = hasFullReport ? report.goal_cards : [];
  const impacts = report.behavioural_goal_impacts || [];
  const budgetSummary = report.budget_summary || {};

  // Compute client-side metrics when we have analysis forecast + live profile
  const forecastTotal = forecast.total || 0;
  const computedSurplus = hasProfile ? liveIncome - forecastTotal : 0;
  const surplusHealth = computedSurplus > liveIncome * 0.3 ? 'strong' : computedSurplus > 0 ? 'tight' : 'negative';

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-3 border-accent/20 border-t-accent rounded-full animate-spin" />
          <p className="text-[13px] text-text-muted font-bold">Loading Strategy Engine...</p>
        </div>
      </div>
    );
  }


  // Calculate base math and fallback text for all goals
  const computedGoals = liveGoals.map(goal => {
    const progress = Math.round(((goal.saved_amount || 0) / goal.target_amount) * 100);
    const remaining = goal.target_amount - (goal.saved_amount || 0);
    const contribution = computedSurplus * (goal.surplus_pct || 0.3);
    const paceMonths = contribution > 0 ? remaining / contribution : 9999;
    const priority = goal.surplus_pct >= 0.5 ? 'High' : goal.surplus_pct >= 0.3 ? 'Medium' : 'Low';
    
    // Compute dynamic fallback tip
    let maxCat = '';
    let maxVal = 0;
    const discretionaryCategories = ['food_dining', 'shopping', 'entertainment', 'streaming', 'subscription', 'travel', 'other'];
    if (forecast && forecast.by_category) {
      for (const [cat, val] of Object.entries(forecast.by_category)) {
        if (discretionaryCategories.includes(cat) && val > maxVal) {
          maxVal = val;
          maxCat = cat;
        }
      }
    }
    
    const fallbackTips = [];
    if (maxVal > 500) {
      const saving = Math.round(maxVal * 0.3);
      fallbackTips.push(`Decrease ${maxCat.replace('_', ' ')} spending by ₹${saving.toLocaleString()}/mo to reach this goal faster.`);
    } else {
      fallbackTips.push("Identify unused subscriptions or small recurring expenses to cut and reallocate here.");
    }

    return {
      goal_id: goal.goal_id, goal_name: goal.name, progress_pct: progress,
      remaining_amount: remaining, current_pace_months: Math.round(paceMonths * 10) / 10,
      balanced_months: Math.round(paceMonths * 0.7 * 10) / 10,
      conservative_months: Math.round(paceMonths * 0.5 * 10) / 10,
      monthly_contribution: Math.round(contribution),
      biggest_lever_sentence: `Allocating ${Math.round((goal.surplus_pct || 0.3) * 100)}% of surplus to this goal.`,
      motivation_line: remaining < 50000 ? "Almost there — stay focused!" : "Consistent effort will get you there.",
      acceleration_tips: fallbackTips,
      priority, isFromReport: false, _raw: goal
    };
  });

  // If a full report exists, inject the AI-generated text AND math over the base computation
  const displayGoals = hasFullReport ? computedGoals.map(cg => {
    const reportGoal = goalCards.find(gc => gc.goal_id === cg.goal_id || gc.goal_name === cg.goal_name);
    if (reportGoal) {
      return {
        ...cg,
        current_pace_months: reportGoal.current_pace_months ?? cg.current_pace_months,
        balanced_months: reportGoal.balanced_months ?? cg.balanced_months,
        conservative_months: reportGoal.conservative_months ?? cg.conservative_months,
        biggest_lever_sentence: reportGoal.biggest_lever_sentence || cg.biggest_lever_sentence,
        motivation_line: reportGoal.motivation_line || cg.motivation_line,
        acceleration_tips: (reportGoal.acceleration_tips && reportGoal.acceleration_tips.length > 0) ? reportGoal.acceleration_tips : cg.acceleration_tips,
        isFromReport: true
      };
    }
    return cg;
  }) : computedGoals;

  const displaySurplus = hasFullReport ? (budgetSummary.forecasted_surplus || 0) : computedSurplus;
  const displayHealth = hasFullReport ? (budgetSummary.surplus_health || 'unknown') : surplusHealth;
  const displayVerdict = hasFullReport
    ? (budgetSummary.one_line_verdict || "Financial Trajectory & Goal Optimization")
    : hasAnalysisData
      ? `Your surplus is ₹${Math.round(computedSurplus).toLocaleString()}/mo — ${computedSurplus > 0 ? 'goals are achievable' : 'spending exceeds income'}.`
      : "Upload a statement to unlock spend forecasts and optimization.";

  return (
    <div className="flex-1 flex flex-col min-w-0 pb-16 px-4 sm:px-0">
      {/* Toast */}
      <AnimatePresence>
        {status.msg && (
          <motion.div initial={{ y: -50, opacity: 0 }} animate={{ y: 20, opacity: 1 }} exit={{ y: -50, opacity: 0 }}
            className={`fixed top-0 left-1/2 -translate-x-1/2 z-[100] px-6 py-3 rounded-2xl shadow-card border font-bold text-[13px] flex items-center gap-3 ${
              status.type === 'success' ? 'bg-status-success/10 border-status-success/20 text-status-success' : 'bg-status-danger/10 border-status-danger/20 text-status-danger'
            }`}>
            <span className="material-symbols-outlined text-[20px]">{status.type === 'success' ? 'check_circle' : 'error'}</span>
            {status.msg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="mt-4 mb-8 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center text-white shadow-glow">
              <span className="material-symbols-outlined text-[18px] fill-1">track_changes</span>
            </div>
            <p className="text-[12px] text-text-muted uppercase tracking-[0.2em] font-black">Strategy Hub</p>
          </div>
          <h2 className="text-[28px] font-black text-text-ink tracking-tight leading-[1.1] max-w-3xl">{displayVerdict}</h2>
        </div>

        <div className="flex items-center gap-3">
           <button 
             onClick={() => setEditGoal({ isNew: true })}
             className="h-14 px-6 bg-bg-surface border border-border-light text-text-ink rounded-2xl font-bold text-[14px] shadow-soft hover:bg-bg-subtle transition-all flex items-center gap-2"
           >
             <span className="material-symbols-outlined text-[20px]">add_circle</span>
             Add Goal
           </button>
           <button 
             onClick={handleRunAgent}
             className="h-14 px-8 bg-accent hover:bg-accent-hover text-white rounded-2xl font-bold text-[15px] shadow-glow flex items-center gap-3 transition-all active:scale-95"
           >
             <span className="material-symbols-outlined text-[24px] fill-1">bolt</span>
             Start Goal Agent
           </button>
        </div>
      </div>

      {report && report.error && (
        <div className="mb-8 bg-status-danger/10 border border-status-danger/20 p-4 rounded-xl flex items-start gap-3 text-status-danger shadow-soft">
          <span className="material-symbols-outlined text-[20px] shrink-0">warning</span>
          <div>
            <p className="text-[13px] font-bold mb-1">Guardian AI Error</p>
            <p className="text-[12px] opacity-80 break-words">{report.error}</p>
          </div>
        </div>
      )}

      {!hasAnalysisData && hasProfile && (
        <div className="mb-12 p-10 border-2 border-dashed border-border-light rounded-[40px] text-center bg-bg-subtle/30">
          <div className="w-16 h-16 rounded-3xl bg-bg-surface border border-border-light flex items-center justify-center mx-auto mb-6 shadow-soft">
             <span className="material-symbols-outlined text-accent text-[28px] fill-1">insights</span>
          </div>
          <h4 className="text-[20px] font-bold text-text-ink mb-2">Awaiting Intelligence Sync</h4>
          <p className="text-[14px] text-text-body max-w-md mx-auto mb-8 opacity-70">
            Your profile is ready. Now upload your statement to allow Guardian to calculate forecasts and goal timelines.
          </p>
          <button 
            onClick={() => setIsUploadOpen(true)}
            className="h-14 px-10 bg-text-ink text-white rounded-2xl font-bold text-[15px] hover:bg-accent transition-all shadow-card"
          >
            Execute Statement Analysis
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Goals Column */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <div className="flex justify-between items-center px-2">
            <h3 className="text-[20px] font-black text-text-ink">Active Objectives</h3>
            <span className="text-[11px] text-text-muted uppercase font-black tracking-widest">{displayGoals.length} Goals</span>
          </div>

          <div className="grid grid-cols-1 gap-8">
            {displayGoals.length === 0 ? (
              <motion.div 
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="py-20 px-10 bg-bg-surface border border-border-light rounded-[40px] shadow-soft text-center flex flex-col items-center justify-center relative overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-b from-accent/5 to-transparent pointer-events-none" />
                
                <div className="w-24 h-24 rounded-[32px] bg-bg-subtle border border-border-light flex items-center justify-center mb-8 shadow-soft relative z-10">
                   <span className="material-symbols-outlined text-accent text-[40px] fill-1">architecture</span>
                </div>
                
                <h4 className="text-[28px] font-black text-text-ink mb-4 tracking-tight relative z-10">Objective Architecture Idle</h4>
                <p className="text-[16px] text-text-body max-w-md mb-12 leading-relaxed opacity-70 relative z-10">
                   Your strategic forecasting engine is ready. Define your financial objectives or sync your statements to map out your trajectory.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-2xl relative z-10">
                   <button 
                     onClick={() => setEditGoal({ isNew: true })}
                     className="p-8 bg-bg-subtle border border-border-light rounded-[32px] text-left hover:border-accent/30 hover:bg-white transition-all group"
                   >
                      <div className="w-12 h-12 rounded-2xl bg-white flex items-center justify-center text-accent mb-6 shadow-soft group-hover:scale-110 transition-transform">
                         <span className="material-symbols-outlined text-[24px]">add_circle</span>
                      </div>
                      <h5 className="text-[18px] font-bold text-text-ink mb-2">Add First Goal</h5>
                      <p className="text-[13px] text-text-muted font-medium leading-relaxed">Define a target like a New Home, Car, or Emergency Fund.</p>
                   </button>

                   <button 
                     onClick={() => setIsUploadOpen(true)}
                     className="p-8 bg-bg-subtle border border-border-light rounded-[32px] text-left hover:border-accent/30 hover:bg-white transition-all group"
                   >
                      <div className="w-12 h-12 rounded-2xl bg-white flex items-center justify-center text-status-success mb-6 shadow-soft group-hover:scale-110 transition-transform">
                         <span className="material-symbols-outlined text-[24px]">sync</span>
                      </div>
                      <h5 className="text-[18px] font-bold text-text-ink mb-2">Sync Intelligence</h5>
                      <p className="text-[13px] text-text-muted font-medium leading-relaxed">Upload statements to calculate your surplus and timelines.</p>
                   </button>
                </div>
              </motion.div>
            ) : (
              displayGoals.map((goal, idx) => (
              <motion.div key={goal.goal_id || idx} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="bg-bg-surface border border-border-light rounded-[24px] p-7 shadow-soft hover:shadow-card transition-all group overflow-hidden relative">
                <div className="absolute top-0 right-0 w-[40%] h-full bg-gradient-to-l from-accent/5 to-transparent pointer-events-none" />
                <div className="relative z-10">
                  <div className="flex justify-between items-start mb-6">
                    <div>
                      <h4 className="text-[20px] font-black text-text-ink mb-2 tracking-tight">{goal.goal_name}</h4>
                      <p className="text-[15px] text-text-body font-medium italic opacity-70">"{goal.motivation_line}"</p>
                    </div>
                    <div className="flex items-center gap-3">
                      {/* Edit Button */}
                      <button onClick={() => openEdit(goal._raw || { goal_id: goal.goal_id, name: goal.goal_name, target_amount: goal.remaining_amount / (1 - (goal.progress_pct || 0) / 100) || 100000, saved_amount: 0, surplus_pct: 0.3 })}
                        className="w-10 h-10 rounded-xl bg-bg-subtle border border-border-light flex items-center justify-center text-text-muted hover:text-accent hover:border-accent/30 transition-all">
                        <span className="material-symbols-outlined text-[18px]">edit</span>
                      </button>
                      <div className="bg-bg-subtle border border-border-light px-6 py-3 rounded-[16px] text-right shadow-soft">
                        <p className="text-[22px] font-mono font-black text-text-ink leading-none">{goal.progress_pct}%</p>
                        <p className="text-[10px] text-text-muted uppercase font-black tracking-widest mt-2">Progress</p>
                      </div>
                    </div>
                  </div>

                  <div className="w-full h-5 bg-bg-subtle rounded-full overflow-hidden mb-10 border border-border-light p-1">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${goal.progress_pct}%` }}
                      transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
                      className="h-full bg-accent rounded-full shadow-glow relative">
                      <div className="absolute inset-0 bg-gradient-to-r from-white/30 via-white/10 to-transparent" />
                    </motion.div>
                  </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="p-5 rounded-[20px] bg-bg-subtle border border-border-light">
                        <p className="text-[11px] text-text-muted uppercase font-black tracking-widest mb-2">Current Pace</p>
                        <p className="text-[18px] font-mono font-black text-text-ink">
                          {goal.current_pace_months >= 999 ? "∞" : `${goal.current_pace_months}m`}
                        </p>
                      </div>
                      <div className="p-5 rounded-[20px] bg-status-warning/5 border border-status-warning/10">
                        <p className="text-[11px] text-status-warning uppercase font-black tracking-widest mb-2">Balanced</p>
                        <p className="text-[18px] font-mono font-black text-status-warning">
                          {goal.balanced_months >= 999 ? "Unlikely" : `${goal.balanced_months}m`}
                        </p>
                      </div>
                      <div className="p-5 rounded-[20px] bg-status-success/5 border border-status-success/10">
                        <p className="text-[11px] text-status-success uppercase font-black tracking-widest mb-2">Optimized</p>
                        <p className="text-[18px] font-mono font-black text-status-success">
                          {goal.conservative_months >= 999 ? "Needs Cut" : `${goal.conservative_months}m`}
                        </p>
                      </div>
                    </div>

                  <div className="mt-8 pt-5 border-t border-border-light flex flex-col gap-4">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent shrink-0">
                        <span className="material-symbols-outlined text-[20px] fill-1">bolt</span>
                      </div>
                      <p className="text-[14px] text-text-body font-bold max-w-md leading-relaxed">
                        <span className="text-text-ink uppercase tracking-wider text-[11px] font-black mr-2">Strategy:</span> {goal.biggest_lever_sentence}
                      </p>
                    </div>
                    {goal.acceleration_tips && goal.acceleration_tips.length > 0 && (
                      <div className="flex flex-col gap-2 pl-14">
                        {goal.acceleration_tips.map((tip, tIdx) => (
                          <div key={tIdx} className="flex items-start gap-3 bg-bg-canvas/50 p-3 rounded-xl border border-border-light/50">
                            <span className="material-symbols-outlined text-status-success text-[18px] mt-0.5 shrink-0">trending_up</span>
                            <p className="text-[13px] text-text-body font-medium leading-relaxed">{tip}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))
          )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          {/* Intel Card */}
          <div className="bg-text-ink text-white rounded-[24px] p-7 shadow-card relative overflow-hidden">
            <div className="absolute top-0 right-0 w-40 h-40 bg-accent/20 blur-3xl rounded-full" />
            <div className="flex items-center gap-3 mb-6">
              <span className="material-symbols-outlined text-accent text-[32px] fill-1">auto_awesome</span>
              <h4 className="text-[12px] font-black uppercase tracking-[0.2em] text-white/50">Guardian Intel</h4>
            </div>
            <p className="text-[18px] font-bold leading-[1.3] mb-10 tracking-tight">
              {hasFullReport ? (report.top_recommendation || "Maintain surplus to hit goals.") : `₹${Math.round(displaySurplus).toLocaleString()} available monthly towards your ${liveGoals.length} goal${liveGoals.length > 1 ? 's' : ''}.`}
            </p>
            <div className="flex justify-between items-center pt-8 border-t border-white/10">
              <div>
                <p className="text-[10px] text-white/40 uppercase font-black tracking-widest mb-1">Monthly Surplus</p>
                <p className="text-[18px] font-mono font-black text-accent">₹{Math.round(displaySurplus).toLocaleString()}</p>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-white/40 uppercase font-black tracking-widest mb-1">Health</p>
                <p className={`text-[18px] font-bold uppercase ${displayHealth === 'strong' ? 'text-status-success' : displayHealth === 'tight' ? 'text-status-warning' : 'text-status-danger'}`}>
                  {displayHealth}
                </p>
              </div>
            </div>
          </div>

          {/* Forecast */}
          {Object.keys(forecast.by_category || {}).length > 0 && (
            <div className="bg-bg-surface border border-border-light rounded-[24px] p-7 shadow-soft">
              <h4 className="text-[16px] font-black text-text-ink mb-10 flex items-center justify-between">
                Spend Forecast
                <span className="text-[11px] text-text-muted font-bold uppercase tracking-widest">Next Month</span>
              </h4>
              <div className="space-y-8">
                {Object.entries(forecast.by_category).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([cat, val], i) => (
                  <div key={i} className="space-y-3">
                    <div className="flex justify-between items-center text-[13px] font-bold">
                      <span className="text-text-body capitalize">{cat.replace('_', ' ')}</span>
                      <span className="font-mono text-text-ink">₹{Math.round(val).toLocaleString()}</span>
                    </div>
                    <div className="w-full h-2 bg-bg-subtle rounded-full overflow-hidden border border-border-light p-0.5">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(val / (forecast.total || 1)) * 100}%` }}
                        className={`h-full rounded-full ${i === 0 ? 'bg-accent shadow-glow' : 'bg-text-ink/10'}`} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-8 pt-6 border-t border-border-light">
                <div className="flex justify-between items-center">
                  <span className="text-[11px] text-text-muted font-black uppercase tracking-widest">Savings Rate</span>
                  <span className="text-[18px] font-mono font-black text-status-success">
                    {Math.round((displaySurplus / (liveIncome || 1)) * 100)}%
                  </span>
                </div>
              </div>
            </div>
          )}

          {displayGoals.length > 0 && impacts.length === 0 && (
            <div className="p-8 bg-bg-subtle border border-border-dashed border-border-light rounded-[32px] text-center">
               <span className="material-symbols-outlined text-text-muted text-[32px] mb-4 opacity-30">psychology</span>
               <p className="text-[13px] text-text-muted font-bold italic px-4">Behavioral insights will appear after your next intelligence sync.</p>
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal for running the agent */}
      <UploadModal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} />

      {/* Edit/Add Goal Modal */}
      <AnimatePresence>
        {(editGoal || editGoal?.isNew) && (
          <div className="fixed inset-0 z-[110] flex items-center justify-center p-6">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setEditGoal(null)} className="absolute inset-0 bg-text-ink/40 backdrop-blur-md" />
            <motion.form onSubmit={editGoal?.isNew ? async (e) => {
              e.preventDefault();
              try {
                await fetch('http://localhost:8000/api/goals', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    user_id: 'user_123',
                    name: editForm.name,
                    target_amount: parseFloat(editForm.target) || 0,
                    saved_amount: parseFloat(editForm.saved) || 0,
                    priority: editForm.priority || 'Medium'
                  })
                });
                setEditGoal(null);
                setEditForm({});
                fetchProfile();
                showToast('success', 'Goal added');
              } catch { showToast('error', 'Failed to add goal'); }
            } : handleUpdateGoal}
              initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-md bg-bg-surface border border-border-light rounded-[24px] p-7 shadow-2xl space-y-6">
              <h3 className="text-[20px] font-bold text-text-ink mb-2">{editGoal?.isNew ? 'Create New Goal' : 'Edit Goal'}</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-[12px] font-bold text-text-ink uppercase tracking-wider mb-2">Goal Name</label>
                  <input required value={editForm.name || ''} onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                    placeholder="e.g. New Macbook"
                    className="w-full h-12 bg-bg-subtle border border-border-mid rounded-xl px-4 outline-none focus:border-accent font-medium text-[14px]" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[12px] font-bold text-text-ink uppercase tracking-wider mb-2">Target (₹)</label>
                    <input required type="number" value={editForm.target || ''} onChange={e => setEditForm({ ...editForm, target: e.target.value })}
                      placeholder="0"
                      className="w-full h-12 bg-bg-subtle border border-border-mid rounded-xl px-4 outline-none focus:border-accent font-mono text-[14px]" />
                  </div>
                  <div>
                    <label className="block text-[12px] font-bold text-text-ink uppercase tracking-wider mb-2">Saved (₹)</label>
                    <input type="number" value={editForm.saved || ''} onChange={e => setEditForm({ ...editForm, saved: e.target.value })}
                      placeholder="0"
                      className="w-full h-12 bg-bg-subtle border border-border-mid rounded-xl px-4 outline-none focus:border-accent font-mono text-[14px]" />
                  </div>
                </div>
                <div>
                  <label className="block text-[12px] font-bold text-text-ink uppercase tracking-wider mb-2">Priority</label>
                  <div className="flex gap-2">
                    {['Low', 'Medium', 'High'].map(p => (
                      <button key={p} type="button" onClick={() => setEditForm({ ...editForm, priority: p })}
                        className={`flex-1 h-10 rounded-xl text-[11px] font-black uppercase tracking-widest border transition-all ${
                          (editForm.priority || 'Medium') === p ? 'bg-accent text-white border-accent shadow-glow' : 'bg-bg-subtle text-text-muted border-border-mid hover:border-accent/30'
                        }`}>{p}</button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex gap-4 pt-4">
                {!editGoal?.isNew && (
                  <button type="button" onClick={() => handleDeleteGoal(editGoal.goal_id)}
                    className="h-12 px-6 border border-status-danger/20 text-status-danger font-bold rounded-2xl hover:bg-status-danger hover:text-white transition-all text-[13px]">
                    Delete
                  </button>
                )}
                <button type="button" onClick={() => { setEditGoal(null); setEditForm({}); }}
                  className="flex-1 h-12 bg-bg-subtle text-text-ink font-bold rounded-2xl hover:bg-bg-hover transition-all">Cancel</button>
                <button type="submit"
                  className="flex-1 h-12 bg-accent text-white font-bold rounded-2xl shadow-glow hover:bg-accent-hover transition-all">
                  {editGoal?.isNew ? 'Create Goal' : 'Save Changes'}
                </button>
              </div>
            </motion.form>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
