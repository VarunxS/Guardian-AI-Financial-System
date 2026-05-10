import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CardExplorer from '../components/CardExplorer';

// Animated Number Component
const AnimatedNumber = ({ value, prefix = '', suffix = '' }) => {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const end = parseFloat(value);
    if (isNaN(end)) return;
    
    const duration = 1200;
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

// Category icon mapping
const CATEGORY_ICONS = {
  food_dining: 'restaurant',
  groceries: 'local_grocery_store',
  travel: 'flight',
  shopping: 'shopping_bag',
  fuel: 'local_gas_station',
  entertainment: 'movie',
  streaming: 'play_circle',
  health: 'health_and_safety',
  subscription: 'subscriptions',
  other: 'category',
};

export default function RewardOptimiser() {
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState('rewards');

  useEffect(() => {
    const stored = sessionStorage.getItem('GUARDIAN_ANALYSIS');
    if (stored) {
      const analysis = JSON.parse(stored);
      if (analysis.reward_findings?.length > 0) {
        setData(analysis.reward_findings[0]);
      }
    }
  }, []);

  const TABS = [
    { id: 'rewards', label: 'My Rewards', icon: 'bolt' },
    { id: 'explore', label: 'Explore Cards', icon: 'search' },
  ];

  const topPick = data?.top_pick || {};
  const missedRewards = data?.missed_rewards || [];
  const runnerUps = data?.runner_ups || [];
  const spendingProfile = data?.spending_profile || [];

  return (
    <div className="flex-1 flex flex-col pb-24 px-4 sm:px-0">
      
      {/* Page Header */}
      <div className="mt-6 mb-8">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center text-white shadow-glow">
            <span className="material-symbols-outlined text-[18px] fill-1">stars</span>
          </div>
          <p className="text-[12px] text-text-muted uppercase tracking-[0.2em] font-black">Value Intelligence</p>
        </div>
        <h2 className="text-[42px] font-black text-text-ink tracking-tight leading-[1.1] mb-8">
          Card Intelligence
        </h2>

        {/* Tab Navigation */}
        <div className="flex gap-2 bg-bg-subtle border border-border-light rounded-2xl p-1.5 w-fit">
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-6 py-3 rounded-xl text-[12px] font-black uppercase tracking-widest transition-all ${
                activeTab === tab.id ? 'bg-text-ink text-white shadow-card' : 'text-text-muted hover:text-text-ink'
              }`}
            >
              <span className="material-symbols-outlined text-[18px] fill-1">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'explore' ? (
        <CardExplorer />
      ) : !data ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
          <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            className="w-24 h-24 rounded-[32px] bg-bg-surface border border-border-light flex items-center justify-center mb-8 shadow-soft">
            <span className="material-symbols-outlined text-accent text-[40px] fill-1">diamond</span>
          </motion.div>
          <h3 className="text-[28px] font-bold text-text-ink mb-3 tracking-tight">Optimizer Idle</h3>
          <p className="text-[16px] text-text-body max-w-md mb-10 leading-relaxed">
            Upload your latest statements to let Guardian analyze your spending and recommend the perfect credit card for you.
          </p>
          <button onClick={() => document.querySelector('[data-upload-trigger]')?.click()}
            className="bg-text-ink text-white px-8 py-4 rounded-2xl font-bold text-[15px] shadow-card hover:bg-accent transition-all active:scale-95">
            Initialize Reward Scan
          </button>
        </div>
      ) : (

      <div className="space-y-8">

        {/* ═══ HERO — Top Card Recommendation ═══ */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="bg-bg-surface border border-border-light rounded-[32px] overflow-hidden shadow-soft"
        >
          <div className="flex flex-col lg:flex-row">
            {/* Card Image Side */}
            <div className="lg:w-2/5 bg-bg-subtle p-8 lg:p-12 flex flex-col items-center justify-center border-b lg:border-b-0 lg:border-r border-border-light relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent" />
              <p className="text-[10px] text-accent uppercase font-black tracking-[0.25em] mb-6 relative z-10">🏆 Your Best Match</p>
              <img 
                src={topPick.image_url || '/assets/cards/generic.png'} 
                alt={topPick.name} 
                className="w-full max-w-[320px] h-auto object-contain drop-shadow-[0_20px_40px_rgba(0,0,0,0.25)] rounded-xl relative z-10 hover:scale-105 transition-transform duration-500"
                onError={(e) => { e.target.src = '/assets/cards/generic.png'; }}
              />
              <div className="mt-8 text-center relative z-10">
                <p className="text-[10px] text-text-muted uppercase font-black tracking-widest mb-1">Net Annual Value</p>
                <p className="text-[36px] font-mono font-black text-accent leading-none">
                  <AnimatedNumber value={topPick.net_annual_value || 0} prefix="₹" />
                </p>
              </div>
            </div>

            {/* Card Details Side */}
            <div className="lg:w-3/5 p-8 lg:p-12">
              <div className="flex items-center gap-3 mb-2">
                <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-lg border ${
                  topPick.tier === 'super_premium' ? 'bg-amber-100 text-amber-700 border-amber-200' :
                  topPick.tier === 'premium' ? 'bg-violet-100 text-violet-700 border-violet-200' :
                  'bg-sky-100 text-sky-700 border-sky-200'
                }`}>
                  {topPick.tier?.replace('_', ' ')}
                </span>
                <span className="text-[11px] font-bold text-text-muted">{topPick.issuer} · {topPick.card_network}</span>
              </div>
              <h3 className="text-[32px] font-black text-text-ink tracking-tight mb-2 leading-tight">{topPick.name}</h3>
              
              {/* Stats Row */}
              <div className="grid grid-cols-3 gap-4 mt-6 mb-8">
                <div className="bg-bg-subtle rounded-2xl p-4 border border-border-light">
                  <p className="text-[10px] text-text-muted uppercase font-black tracking-widest mb-1">Monthly Reward</p>
                  <p className="text-[20px] font-mono font-black text-accent">₹{(topPick.estimated_monthly_reward || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}</p>
                </div>
                <div className="bg-bg-subtle rounded-2xl p-4 border border-border-light">
                  <p className="text-[10px] text-text-muted uppercase font-black tracking-widest mb-1">Annual Fee</p>
                  <p className="text-[20px] font-mono font-black text-text-ink">{topPick.annual_fee === 0 ? 'FREE' : `₹${(topPick.annual_fee || 0).toLocaleString()}`}</p>
                </div>
                <div className="bg-bg-subtle rounded-2xl p-4 border border-border-light">
                  <p className="text-[10px] text-text-muted uppercase font-black tracking-widest mb-1">Reward Type</p>
                  <p className="text-[14px] font-black text-text-ink truncate">{topPick.reward_type}</p>
                </div>
              </div>

              {/* Why For You */}
              {topPick.why_for_you && (
                <div className="bg-accent/5 border border-accent/10 rounded-2xl p-6 mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined text-accent text-[20px] fill-1">psychology_alt</span>
                    <p className="text-[11px] text-accent uppercase font-black tracking-widest">Why This Card For You</p>
                  </div>
                  <p className="text-[15px] text-text-body font-medium leading-relaxed">{topPick.why_for_you}</p>
                </div>
              )}

              {/* Key Perks */}
              {(topPick.key_perks || []).length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {topPick.key_perks.slice(0, 5).map((perk, i) => (
                    <span key={i} className="flex items-center gap-1.5 text-[11px] font-bold text-text-body bg-bg-subtle px-3 py-2 rounded-xl border border-border-light">
                      <span className="material-symbols-outlined text-accent text-[14px] fill-1">verified</span>
                      {perk}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </motion.div>


        {/* ═══ MISSED REWARDS — Transaction Level ═══ */}
        {missedRewards.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="bg-bg-surface border border-border-light rounded-[32px] p-8 lg:p-10 shadow-soft"
          >
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-[24px] text-status-warning fill-1">currency_rupee</span>
                <h4 className="text-[20px] font-black text-text-ink tracking-tight">What You Missed</h4>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-text-muted uppercase font-black tracking-widest">Total Annual Value</p>
                <p className="text-[20px] font-mono font-black text-accent">₹{(data.total_missed_annual || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}</p>
              </div>
            </div>

            <div className="space-y-4">
              {missedRewards.map((txn, i) => (
                <motion.div 
                  key={i}
                  initial={{ opacity: 0, x: -10 }} 
                  animate={{ opacity: 1, x: 0 }} 
                  transition={{ delay: 0.15 + i * 0.05 }}
                  className="flex items-start gap-5 bg-bg-subtle border border-border-light rounded-2xl p-5 hover:border-accent/20 transition-all group"
                >
                  {/* Icon */}
                  <div className="w-12 h-12 rounded-2xl bg-bg-surface border border-border-light flex items-center justify-center flex-shrink-0 group-hover:border-accent/30 transition-all">
                    <span className="material-symbols-outlined text-[22px] text-text-muted fill-1">
                      {CATEGORY_ICONS[txn.category] || 'receipt_long'}
                    </span>
                  </div>

                  {/* Transaction Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <h5 className="text-[15px] font-black text-text-ink truncate">{txn.merchant}</h5>
                      <span className="text-[15px] font-mono font-black text-text-ink ml-4 flex-shrink-0">₹{txn.amount?.toLocaleString()}</span>
                    </div>
                    <p className="text-[11px] text-text-muted font-bold mb-2">
                      {txn.date} · {txn.reward_rate}% {txn.reward_type}
                    </p>
                    <div className="flex items-start gap-2 bg-accent/5 rounded-xl px-3 py-2 border border-accent/10">
                      <span className="material-symbols-outlined text-accent text-[16px] fill-1 mt-0.5 flex-shrink-0">arrow_forward</span>
                      <p className="text-[13px] text-text-body font-medium leading-snug">
                        {txn.what_you_missed || `₹${Math.round(txn.reward_earned || 0).toLocaleString()} in ${txn.reward_type}`}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}


        {/* ═══ SPENDING PROFILE + RUNNER-UPS ═══ */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          {/* Spending Breakdown */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="bg-bg-surface border border-border-light rounded-[32px] p-8 lg:p-10 shadow-soft"
          >
            <h4 className="text-[18px] font-black text-text-ink mb-8 flex items-center gap-3">
              <span className="material-symbols-outlined text-[22px] text-accent fill-1">pie_chart</span>
              Your Spending Profile
            </h4>
            <div className="space-y-5">
              {(topPick.category_rewards || []).filter(c => c.monthly_reward > 0).slice(0, 6).map((cat, i) => {
                const maxReward = Math.max(...(topPick.category_rewards || []).map(c => c.monthly_reward));
                return (
                  <div key={i}>
                    <div className="flex justify-between items-center mb-2">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-[18px] text-text-muted fill-1">
                          {CATEGORY_ICONS[cat.category] || 'category'}
                        </span>
                        <span className="text-[13px] font-bold text-text-ink capitalize">{cat.category.replace('_', ' ')}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-[13px] font-mono font-black text-text-ink">₹{Math.round(cat.monthly_spend).toLocaleString()}</span>
                        <span className="text-[11px] text-accent font-black ml-2">→ ₹{Math.round(cat.monthly_reward).toLocaleString()}</span>
                      </div>
                    </div>
                    <div className="w-full h-2 bg-bg-subtle rounded-full overflow-hidden border border-border-light">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(cat.monthly_reward / maxReward) * 100}%` }}
                        transition={{ delay: 0.3 + i * 0.05, duration: 0.6 }}
                        className={`h-full rounded-full ${i === 0 ? 'bg-accent' : 'bg-text-ink/15'}`}
                      />
                    </div>
                    <p className="text-[10px] text-text-muted font-bold mt-1">{cat.rate}% reward rate</p>
                  </div>
                );
              })}
            </div>
          </motion.div>

          {/* Runner-Ups */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="bg-bg-surface border border-border-light rounded-[32px] p-8 lg:p-10 shadow-soft"
          >
            <h4 className="text-[18px] font-black text-text-ink mb-8 flex items-center gap-3">
              <span className="material-symbols-outlined text-[22px] text-text-muted fill-1">trophy</span>
              Runner-Ups
            </h4>
            <div className="space-y-5">
              {runnerUps.map((card, i) => (
                <div key={i} className="flex items-center gap-5 bg-bg-subtle border border-border-light rounded-2xl p-5 hover:border-accent/20 transition-all">
                  <img 
                    src={card.image_url || '/assets/cards/generic.png'} 
                    alt={card.name}
                    className="w-20 h-14 object-contain rounded-lg flex-shrink-0"
                    onError={(e) => { e.target.src = '/assets/cards/generic.png'; }}
                  />
                  <div className="flex-1 min-w-0">
                    <h5 className="text-[15px] font-black text-text-ink truncate">{card.name}</h5>
                    <p className="text-[11px] text-text-muted font-bold mb-1">{card.issuer} · Fee: {card.annual_fee === 0 ? 'FREE' : `₹${card.annual_fee?.toLocaleString()}`}</p>
                    <p className="text-[12px] text-text-body font-medium leading-snug line-clamp-2">{card.one_liner}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-[10px] text-text-muted uppercase font-black tracking-widest">Net/Yr</p>
                    <p className="text-[18px] font-mono font-black text-text-ink">₹{Math.round(card.net_annual_value || 0).toLocaleString()}</p>
                  </div>
                </div>
              ))}
              {runnerUps.length === 0 && (
                <p className="text-[13px] text-text-muted font-bold text-center py-8">Run an analysis to see alternatives</p>
              )}
            </div>
          </motion.div>
        </div>

        {/* ═══ SUMMARY BANNER ═══ */}
        {data?.summary && (
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
            className="bg-text-ink text-white rounded-[32px] p-8 lg:p-10 shadow-card relative overflow-hidden"
          >
            <div className="absolute bottom-0 right-0 w-60 h-60 bg-accent/10 blur-[80px] rounded-full -mb-20 -mr-20" />
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-accent text-[24px] fill-1">auto_awesome</span>
              <p className="text-[11px] text-white/40 uppercase font-black tracking-widest">Guardian Insight</p>
            </div>
            <p className="text-[20px] font-bold leading-relaxed italic opacity-90 tracking-tight max-w-3xl relative z-10">
              "{data.summary}"
            </p>
          </motion.div>
        )}

      </div>
      )}
    </div>
  );
}
