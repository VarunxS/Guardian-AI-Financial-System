import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_BASE_URL } from '../config';
import { fetchStoredProviderConfig } from '../utils/providerConfig';

const TIER_COLORS = {
  super_premium: { bg: 'bg-gradient-to-br from-amber-500 to-yellow-600', text: 'text-amber-600', label: 'Super Premium', badge: 'bg-amber-100 text-amber-700 border-amber-200' },
  premium: { bg: 'bg-gradient-to-br from-violet-500 to-purple-600', text: 'text-violet-600', label: 'Premium', badge: 'bg-violet-100 text-violet-700 border-violet-200' },
  mid_range: { bg: 'bg-gradient-to-br from-sky-500 to-blue-600', text: 'text-sky-600', label: 'Mid-Range', badge: 'bg-sky-100 text-sky-700 border-sky-200' },
  entry: { bg: 'bg-gradient-to-br from-emerald-500 to-green-600', text: 'text-emerald-600', label: 'Entry', badge: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
};

const FILTERS = [
  { id: 'all', label: 'All Cards' },
  { id: 'super_premium', label: 'Super Premium' },
  { id: 'premium', label: 'Premium' },
  { id: 'mid_range', label: 'Mid-Range' },
  { id: 'entry', label: 'Entry' },
  { id: 'no_fee', label: 'No Fee' },
];

export default function CardExplorer() {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [selectedCard, setSelectedCard] = useState(null);
  const [liveData, setLiveData] = useState(null);
  const [liveLoading, setLiveLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/cards`)
      .then(r => r.json())
      .then(data => { setCards(data.cards || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = cards.filter(c => {
    const matchesSearch = !search || c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.issuer?.toLowerCase().includes(search.toLowerCase()) ||
      c.best_for?.some(b => b.toLowerCase().includes(search.toLowerCase()));
    const matchesFilter = filter === 'all' || (filter === 'no_fee' ? c.annual_fee === 0 : c.tier === filter);
    return matchesSearch && matchesFilter;
  });

  const handleExplore = async (card) => {
    setSelectedCard(card);
    setLiveData(null);
    setLiveLoading(true);
    try {
      const config = await fetchStoredProviderConfig();
      const res = await fetch(`${API_BASE_URL}/api/card-explore`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ card_id: card.id, api_key: config.api_key })
      });
      const data = await res.json();
      setLiveData(data);
    } catch (e) { console.error(e); }
    setLiveLoading(false);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-8 h-8 border-3 border-accent/20 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col pb-16">
      {/* Search + Filters */}
      <div className="mb-8">
        <div className="relative mb-6">
          <span className="material-symbols-outlined absolute left-5 top-1/2 -translate-y-1/2 text-text-muted text-[20px]">search</span>
          <input
            type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search cards by name, bank, or feature..."
            className="w-full h-14 bg-bg-subtle border border-border-light rounded-2xl pl-14 pr-6 text-[14px] font-medium text-text-ink outline-none focus:border-accent focus:ring-4 focus:ring-accent/5 transition-all"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {FILTERS.map(f => (
            <button key={f.id} onClick={() => setFilter(f.id)}
              className={`px-5 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest border transition-all ${filter === f.id ? 'bg-text-ink text-white border-text-ink shadow-card' : 'bg-bg-subtle text-text-muted border-border-light hover:border-text-ink/20'}`}
            >{f.label}</button>
          ))}
        </div>
      </div>

      {/* Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
        {filtered.map((card, i) => {
          const tier = TIER_COLORS[card.tier] || TIER_COLORS.entry;
          return (
            <motion.div key={card.id}
              initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04, duration: 0.5 }}
              className="bg-bg-surface border border-border-light rounded-[28px] overflow-hidden shadow-soft hover:shadow-card hover:border-accent/20 transition-all group cursor-pointer"
              onClick={() => handleExplore(card)}
            >
              {/* Card Header Image */}
              <div className="bg-bg-subtle h-72 relative overflow-hidden flex items-center justify-center p-6 border-b border-border-light">
                <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/5 z-0" />
                <img src={card.image_url} alt={card.name} className="relative z-10 w-full h-full object-contain drop-shadow-[0_15px_25px_rgba(0,0,0,0.25)] group-hover:scale-110 group-hover:-translate-y-2 transition-all duration-500" onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }} />
                <div className="absolute inset-0 hidden items-center justify-center text-text-muted text-[12px] font-bold z-0">Image Unavailable</div>
              </div>

              {/* Card Body */}
              <div className="p-6">
                <h3 className="text-[18px] font-black text-text-ink tracking-tight mb-1 truncate">{card.name}</h3>
                <p className="text-[12px] font-bold text-text-muted mb-4">{card.issuer} · {card.card_network || 'Visa'}</p>
                <div className="flex items-center gap-2 mb-5">
                  <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-lg border ${tier.badge}`}>{tier.label}</span>
                  {card.annual_fee === 0 && <span className="text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-lg bg-status-success/10 text-status-success border border-status-success/20">Free</span>}
                </div>

                <div className="grid grid-cols-2 gap-4 mb-5">
                  <div>
                    <p className="text-[10px] text-text-muted uppercase font-black tracking-widest mb-1">Annual Fee</p>
                    <p className="text-[18px] font-mono font-black text-text-ink">{card.annual_fee === 0 ? 'FREE' : `₹${card.annual_fee.toLocaleString()}`}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-text-muted uppercase font-black tracking-widest mb-1">Base Rate</p>
                    <p className="text-[18px] font-mono font-black text-accent">{card.reward_rate_base}%</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1.5 mb-5">
                  {(card.best_for || []).slice(0, 3).map((tag, j) => (
                    <span key={j} className="text-[10px] font-bold text-text-muted bg-bg-subtle px-2.5 py-1 rounded-lg border border-border-light capitalize">{tag}</span>
                  ))}
                </div>

                <button className="w-full py-3 bg-bg-subtle hover:bg-text-ink text-text-ink hover:text-white text-[11px] font-black uppercase tracking-widest rounded-xl transition-all border border-border-light group-hover:border-transparent flex items-center justify-center gap-2">
                  Explore <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </button>
              </div>
            </motion.div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center text-center py-20">
          <span className="material-symbols-outlined text-[48px] text-text-muted opacity-20 mb-4">search_off</span>
          <p className="text-[16px] font-bold text-text-ink mb-2">No cards found</p>
          <p className="text-[13px] text-text-muted">Try adjusting your search or filters.</p>
        </div>
      )}

      {/* Deep Dive Panel */}
      <AnimatePresence>
        {selectedCard && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-6">
            <div className="absolute inset-0 bg-text-ink/50 backdrop-blur-md" onClick={() => setSelectedCard(null)} />
            <motion.div
              initial={{ y: 100, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 100, opacity: 0 }}
              className="relative w-full max-w-3xl max-h-[90vh] bg-bg-surface border border-border-light rounded-t-[32px] sm:rounded-[32px] shadow-2xl overflow-y-auto"
            >
              {/* Deep dive header */}
              <div className="p-8 sm:p-10 relative overflow-hidden bg-bg-surface border-b border-border-light flex flex-col md:flex-row items-center gap-8 md:gap-12">
                <div className="absolute inset-0 bg-gradient-to-br from-bg-subtle to-bg-canvas opacity-50 z-0" />
                <button onClick={() => setSelectedCard(null)} className="absolute top-5 right-5 w-10 h-10 bg-white border border-border-light shadow-soft rounded-full flex items-center justify-center text-text-ink hover:bg-bg-subtle hover:scale-105 transition-all z-20">
                  <span className="material-symbols-outlined text-[20px]">close</span>
                </button>
                
                <div className="w-full md:w-2/5 flex-shrink-0 relative z-10 flex justify-center">
                   <img src={selectedCard.image_url} alt={selectedCard.name} className="w-full max-w-[340px] h-auto object-contain drop-shadow-[0_20px_40px_rgba(0,0,0,0.3)] rounded-xl" onError={(e) => { e.target.style.display = 'none'; }} />
                </div>
                
                <div className="relative z-10 w-full md:w-3/5">
                  <div className="flex items-center gap-3 mb-4">
                    <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-lg border ${(TIER_COLORS[selectedCard.tier] || TIER_COLORS.entry).badge}`}>{(TIER_COLORS[selectedCard.tier] || TIER_COLORS.entry).label}</span>
                    <span className="text-[11px] font-black text-text-muted uppercase tracking-widest">{selectedCard.issuer} · {selectedCard.card_network}</span>
                  </div>
                  <h3 className="text-text-ink text-[32px] sm:text-[40px] font-black tracking-tight mb-4 leading-[1.1]">{selectedCard.name}</h3>
                  <p className="text-text-body text-[15px] font-medium leading-relaxed max-w-lg">{selectedCard.description}</p>
                </div>
              </div>

              <div className="p-8 sm:p-10 space-y-8">
                {/* Key Stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {[
                    { label: 'Annual Fee', val: selectedCard.annual_fee === 0 ? 'FREE' : `₹${selectedCard.annual_fee.toLocaleString()}` },
                    { label: 'Base Rate', val: `${selectedCard.reward_rate_base}%` },
                    { label: 'Forex Markup', val: selectedCard.forex_markup === 0 ? 'ZERO' : `${selectedCard.forex_markup}%` },
                    { label: 'Reward Type', val: selectedCard.reward_type || 'Points' },
                  ].map((s, i) => (
                    <div key={i} className="bg-bg-subtle border border-border-light rounded-2xl p-4">
                      <p className="text-[10px] text-text-muted uppercase font-black tracking-widest mb-2">{s.label}</p>
                      <p className="text-[16px] font-mono font-black text-text-ink">{s.val}</p>
                    </div>
                  ))}
                </div>

                {/* Category Rates */}
                <div>
                  <h4 className="text-[13px] font-black text-text-ink uppercase tracking-widest mb-4 flex items-center gap-2">
                    <span className="material-symbols-outlined text-accent text-[18px] fill-1">percent</span> Reward Rates
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {Object.entries(selectedCard.reward_rate_per_category || {}).sort((a, b) => b[1] - a[1]).map(([cat, rate]) => (
                      <div key={cat} className="flex justify-between items-center bg-bg-subtle border border-border-light rounded-xl px-4 py-3">
                        <span className="text-[12px] font-bold text-text-ink capitalize">{cat}</span>
                        <span className={`text-[14px] font-mono font-black ${rate >= 5 ? 'text-accent' : rate >= 3 ? 'text-status-warning' : 'text-text-muted'}`}>{rate}%</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Lounge + Milestones */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {selectedCard.lounge_access && (
                    <div>
                      <h4 className="text-[13px] font-black text-text-ink uppercase tracking-widest mb-4 flex items-center gap-2">
                        <span className="material-symbols-outlined text-accent text-[18px] fill-1">airline_seat_individual_suite</span> Lounge Access
                      </h4>
                      <div className="bg-bg-subtle border border-border-light rounded-2xl p-5 space-y-3">
                        <div className="flex justify-between"><span className="text-[12px] font-bold text-text-muted">Domestic</span><span className="text-[12px] font-black text-text-ink">{selectedCard.lounge_access.domestic}</span></div>
                        <div className="flex justify-between"><span className="text-[12px] font-bold text-text-muted">International</span><span className="text-[12px] font-black text-text-ink">{selectedCard.lounge_access.international}</span></div>
                        <div className="flex justify-between"><span className="text-[12px] font-bold text-text-muted">Program</span><span className="text-[12px] font-black text-text-ink">{selectedCard.lounge_access.program}</span></div>
                      </div>
                    </div>
                  )}
                  {(selectedCard.milestone_benefits || []).length > 0 && (
                    <div>
                      <h4 className="text-[13px] font-black text-text-ink uppercase tracking-widest mb-4 flex items-center gap-2">
                        <span className="material-symbols-outlined text-accent text-[18px] fill-1">emoji_events</span> Milestones
                      </h4>
                      <div className="space-y-3">
                        {selectedCard.milestone_benefits.map((m, i) => (
                          <div key={i} className="bg-bg-subtle border border-border-light rounded-2xl p-4">
                            <p className="text-[11px] text-text-muted font-black uppercase tracking-widest mb-1">Spend ₹{m.spend_threshold?.toLocaleString()}</p>
                            <p className="text-[13px] font-bold text-text-ink">{m.benefit}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Extra Details */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {selectedCard.joining_bonus && (
                    <div className="flex items-start gap-3 bg-accent/5 border border-accent/10 rounded-2xl p-4">
                      <span className="material-symbols-outlined text-accent text-[20px] fill-1 mt-0.5">redeem</span>
                      <div><p className="text-[10px] text-accent uppercase font-black tracking-widest mb-1">Joining Bonus</p><p className="text-[13px] font-bold text-text-ink">{selectedCard.joining_bonus}</p></div>
                    </div>
                  )}
                  {selectedCard.fuel_surcharge_waiver && selectedCard.fuel_surcharge_waiver !== 'None' && (
                    <div className="flex items-start gap-3 bg-bg-subtle border border-border-light rounded-2xl p-4">
                      <span className="material-symbols-outlined text-text-muted text-[20px] fill-1 mt-0.5">local_gas_station</span>
                      <div><p className="text-[10px] text-text-muted uppercase font-black tracking-widest mb-1">Fuel Waiver</p><p className="text-[13px] font-bold text-text-ink">{selectedCard.fuel_surcharge_waiver}</p></div>
                    </div>
                  )}
                </div>

                {/* Live Offers */}
                <div>
                  <h4 className="text-[13px] font-black text-text-ink uppercase tracking-widest mb-4 flex items-center gap-2">
                    <span className="material-symbols-outlined text-accent text-[18px] fill-1">bolt</span> Live Intelligence
                    {liveLoading && <div className="w-4 h-4 border-2 border-accent/20 border-t-accent rounded-full animate-spin ml-2" />}
                  </h4>
                  {liveLoading ? (
                    <div className="space-y-3">
                      {[1,2,3].map(i => <div key={i} className="h-20 bg-bg-subtle rounded-2xl animate-pulse border border-border-light" />)}
                    </div>
                  ) : liveData?.live_offers?.length > 0 ? (
                    <div className="space-y-3">
                      {liveData.live_offers.map((offer, i) => (
                        <a key={i} href={offer.url} target="_blank" rel="noopener noreferrer"
                          className="block bg-bg-subtle border border-border-light rounded-2xl p-5 hover:border-accent/30 transition-all group/offer">
                          <p className="text-[13px] font-bold text-text-ink mb-2 group-hover/offer:text-accent transition-colors">{offer.title}</p>
                          <p className="text-[12px] text-text-body leading-relaxed line-clamp-2 opacity-70">{offer.content?.slice(0, 200)}...</p>
                          {offer.published_date && <p className="text-[10px] text-text-muted mt-2 font-bold uppercase tracking-widest">{new Date(offer.published_date).toLocaleDateString()}</p>}
                        </a>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-bg-subtle border border-dashed border-border-light rounded-2xl p-6 text-center">
                      <p className="text-[12px] text-text-muted font-bold">{liveData ? 'No live offers found for this card.' : 'Configure your API key in Settings to fetch live offers.'}</p>
                    </div>
                  )}
                </div>

                {/* Eligibility */}
                {selectedCard.eligibility && (
                  <div className="bg-bg-subtle border border-border-light rounded-2xl p-5 flex items-center gap-3">
                    <span className="material-symbols-outlined text-text-muted text-[20px]">person_check</span>
                    <div>
                      <p className="text-[10px] text-text-muted uppercase font-black tracking-widest mb-0.5">Eligibility</p>
                      <p className="text-[13px] font-bold text-text-ink">{selectedCard.eligibility}</p>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
