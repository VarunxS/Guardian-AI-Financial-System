import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const PROVIDERS = {
    "google": {
        "label": "Google Gemini",
        "key_label": "Gemini API Key",
        "key_placeholder": "AIza••••••••••••••••••••••••••••••••••••",
        "key_link": "https://aistudio.google.com/app/apikey",
        "key_link_label": "Get API key →",
        "models": [
            { "id": "gemini-3-flash-preview", "label": "Gemini 3 Flash Preview", "desc": "Experimental model with state-of-the-art speed and 1M context.", "tags": ["Experimental", "Fast", "Free"] },
            { "id": "gemini-3.1-flash-lite-preview", "label": "Gemini 3.1 Flash-Lite", "desc": "Ultra-lightweight Gemini for high-throughput analysis.", "tags": ["Beta", "Lite"] },
            { "id": "gemini-2.5-flash-lite", "label": "Gemini 2.5 Flash-Lite", "desc": "Balanced performance and efficiency for daily tracking.", "tags": ["Stable"] }
        ]
    },
    "openai": {
        "label": "OpenAI",
        "key_label": "OpenAI API Key",
        "key_placeholder": "sk-proj-••••••••••••••••••••••",
        "key_link": "https://platform.openai.com/api-keys",
        "key_link_label": "Get API key →",
        "models": [
            { "id": "gpt-4o-mini", "label": "GPT-4o-mini", "desc": "Optimized for speed and efficiency. Best for subscription detection.", "tags": ["Reliable", "Fast"] },
            { "id": "gpt-5.4-nano", "label": "GPT-5.4 Nano", "desc": "Next-gen reasoning in a compact footprint.", "tags": ["Premium", "Reasoning"] },
            { "id": "gpt-4.1-mini", "label": "GPT-4.1 Mini", "desc": "Versatile model for general financial consulting.", "tags": ["Legacy"] }
        ]
    },
    "openrouter": {
        "label": "OpenRouter",
        "key_label": "OpenRouter API Key",
        "key_placeholder": "sk-or-v1-••••••••••••••••••••••••••••••••••••••••••••••••••",
        "key_link": "https://openrouter.ai/keys",
        "key_link_label": "Get API key →",
        "allow_custom": true,
        "models": [
            { "id": "google/gemini-3-flash-preview", "label": "Gemini 3 Flash", "desc": "Native Google experimental model via OpenRouter.", "tags": ["Free"] },
            { "id": "openai/gpt-4o-mini", "label": "GPT-4o-mini", "desc": "OpenAI's efficient model via OpenRouter.", "tags": ["Cheap"] },
            { "id": "nvidia/nemotron-3-nano-30b-a3b:free", "label": "Nvidia Nemotron (Free)", "desc": "Free Nvidia model, great for general summarization.", "tags": ["Free", "Privacy"] },
            { "id": "meta-llama/llama-3.1-70b-instruct", "label": "Llama 3.1 70B", "desc": "Meta's powerful open-source reasoning model.", "tags": ["Open Source"] }
        ]
    },
    "mistral": {
        "label": "Mistral AI",
        "key_label": "Mistral API Key",
        "key_placeholder": "••••••••••••••••••••••••••••••••",
        "key_link": "https://console.mistral.ai/api-keys/",
        "key_link_label": "Get API key →",
        "models": [
            { "id": "mistral-small-latest", "label": "Mistral Small", "desc": "Compact French engineering for local data privacy.", "tags": ["Efficient"] }
        ]
    }
};

export default function Settings() {
  const [selectedProvider, setSelectedProvider] = useState('google');
  const [selectedModel, setSelectedModel] = useState('gemini-3-flash-preview');
  const [customModel, setCustomModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [status, setStatus] = useState({ type: '', msg: '' });
  const [activeConfig, setActiveConfig] = useState(null);
  const [dbError, setDbError] = useState(null);
  const [isPurging, setIsPurging] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/settings/config/user_123');
      const data = await res.json();
      
      if (data.db_error) {
          setDbError(data.db_error);
      } else {
          setDbError(null);
      }

      if (data.configured) {
        setActiveConfig(data);
        setSelectedProvider(data.provider);
        
        const providerModels = PROVIDERS[data.provider]?.models || [];
        const isKnownModel = providerModels.some(m => m.id === data.model_id);
        
        if (data.provider === 'openrouter' && !isKnownModel) {
            setSelectedModel('custom');
            setCustomModel(data.model_id);
        } else {
            setSelectedModel(data.model_id);
        }
        
        setApiKey(data.api_key);
      }
    } catch (err) {
      console.error("Failed to fetch config", err);
    }
  };

  const handleSave = async () => {
    if (!apiKey) {
      showStatus('error', 'Please enter an API key');
      return;
    }

    const finalModel = selectedModel === 'custom' ? customModel : selectedModel;
    if (!finalModel) {
        showStatus('error', 'Please select or enter a model');
        return;
    }

    setIsVerifying(true);
    setStatus({ type: '', msg: '' });

    try {
      // 1. Verify Key
      const testRes = await fetch('http://localhost:8000/api/settings/test-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: selectedProvider, model_id: finalModel, api_key: apiKey })
      });
      
      if (!testRes.ok) throw new Error('Verification service unavailable');
      
      const testData = await testRes.json();

      if (!testData.valid) {
        showStatus('error', `Verification failed: ${testData.error}`);
        setIsVerifying(false);
        return;
      }

      // 2. Save Config
      const saveRes = await fetch('http://localhost:8000/api/settings/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'user_123',
          provider: selectedProvider,
          model_id: finalModel,
          api_key: apiKey,
          exa_api_key: ""
        })
      });

      if (!saveRes.ok) {
          const saveErr = await saveRes.json();
          throw new Error(saveErr.detail || 'Failed to save configuration');
      }

      showStatus('success', 'Configuration saved. Guardian is ready.');
      setDbError(null);
      fetchConfig();
    } catch (err) {
      showStatus('error', err.message);
    } finally {
      setIsVerifying(false);
    }
  };

  const handlePurge = async () => {
    const confirmed = window.confirm("⚠ CRITICAL ACTION: This will permanently delete all your financial goals, income history, and analysis data. This cannot be undone. Proceed?");
    if (!confirmed) return;

    setIsPurging(true);
    try {
      const res = await fetch('http://localhost:8000/api/user/purge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'user_123' })
      });
      
      if (!res.ok) throw new Error('Failed to purge data');

      sessionStorage.removeItem('GUARDIAN_ANALYSIS');
      localStorage.removeItem('GUARDIAN_INCOME');
      localStorage.removeItem('GUARDIAN_API_KEY');
      setApiKey('');
      setActiveConfig(null);
      
      showStatus('success', 'System purged. All personal data and API keys have been erased.');
      fetchConfig();
    } catch (err) {
      showStatus('error', err.message);
    } finally {
      setIsPurging(false);
    }
  };

  const showStatus = (type, msg) => {
    setStatus({ type, msg });
    if (type === 'success') {
        setTimeout(() => setStatus({ type: '', msg: '' }), 5000);
    }
  };

  const currentProvider = PROVIDERS[selectedProvider];
  const currentModelObj = currentProvider.models.find(m => m.id === selectedModel);

  return (
    <div className="flex-1 flex flex-col pb-24 px-4 sm:px-0">
      
      {/* Status Toast */}
      <AnimatePresence>
        {status.msg && (
          <motion.div 
            initial={{ y: -50, opacity: 0 }} animate={{ y: 20, opacity: 1 }} exit={{ y: -50, opacity: 0 }}
            className={`fixed top-0 left-1/2 -translate-x-1/2 z-[100] px-6 py-3 rounded-2xl shadow-card border font-bold text-[13px] flex items-center gap-3 ${
              status.type === 'success' ? 'bg-status-success/10 border-status-success/20 text-status-success' : 'bg-status-danger/10 border-status-danger/20 text-status-danger'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">{status.type === 'success' ? 'check_circle' : 'error'}</span>
            {status.msg}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-6 mb-8">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center text-white shadow-glow">
            <span className="material-symbols-outlined text-[18px] fill-1">settings</span>
          </div>
          <p className="text-[12px] text-text-muted uppercase tracking-[0.2em] font-black">Preferences</p>
        </div>
        <h2 className="text-[32px] font-black text-text-ink tracking-tight leading-none">
          BYOK Settings
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Main Panel */}
        <div className="lg:col-span-8 space-y-8">
          
          {dbError && (
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-orange-50 border border-orange-200 rounded-[24px] p-6 flex items-start gap-4">
                  <span className="material-symbols-outlined text-orange-600 mt-1">database_off</span>
                  <div>
                      <p className="text-orange-900 font-bold text-[14px]">Database Migration Required</p>
                      <p className="text-orange-700 text-[13px] mt-1 leading-relaxed">
                          The system detected that the <b>user_provider_config</b> table is missing in your Supabase instance.
                          Please run the updated SQL schema from <b>supabase_schema.sql</b> to enable persistence.
                      </p>
                  </div>
              </motion.div>
          )}

          <div className="bg-white border border-border-light rounded-[32px] p-8 shadow-soft relative overflow-hidden">
            {/* Background Accent */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-accent/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none" />

            {/* Provider Selection - Compact Icons */}
            <section className="mb-10 relative z-10">
              <label className="text-[11px] font-black text-text-muted uppercase tracking-widest block mb-4">AI Provider</label>
              <div className="grid grid-cols-4 gap-3">
                {Object.entries(PROVIDERS).map(([id, p]) => {
                  const isSelected = selectedProvider === id;
                  return (
                    <button 
                      key={id}
                      onClick={() => {
                          setSelectedProvider(id);
                          setSelectedModel(PROVIDERS[id].models[0].id);
                      }}
                      className={`py-3 px-2 rounded-xl text-center transition-all border-2 flex flex-col items-center gap-1.5 ${
                        isSelected 
                          ? 'bg-accent/5 border-accent text-accent shadow-glow' 
                          : 'bg-bg-subtle border-transparent text-text-muted hover:border-border-mid'
                      }`}
                    >
                      <span className="text-[12px] font-black tracking-tight">{p.label.split(' ')[0]}</span>
                      <div className={`w-1.5 h-1.5 rounded-full transition-all ${isSelected ? 'bg-accent scale-100' : 'bg-transparent scale-0'}`} />
                    </button>
                  );
                })}
              </div>
            </section>

            {/* Model & Key */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
               <section>
                  <label className="text-[11px] font-black text-text-muted uppercase tracking-widest block mb-3">Select Model</label>
                  <select 
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full h-14 bg-bg-subtle border border-border-mid rounded-2xl px-5 font-bold text-[14px] focus:border-accent outline-none appearance-none cursor-pointer hover:border-accent/30 transition-colors"
                    style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' fill=\'none\' viewBox=\'0 0 24 24\' stroke=\'%2364748b\'%3E%3Cpath stroke-linecap=\'round\' stroke-linejoin=\'round\' stroke-width=\'2\' d=\'M19 9l-7 7-7-7\'%3E%3C/path%3E%3C/svg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right 1.25rem center', backgroundSize: '1rem' }}
                  >
                    {currentProvider.models.map(m => (
                      <option key={m.id} value={m.id}>{m.label}</option>
                    ))}
                    {currentProvider.allow_custom && (
                        <option value="custom">Any OpenRouter Model...</option>
                    )}
                  </select>

                  <AnimatePresence mode="wait">
                    {currentModelObj && (
                        <motion.div key={selectedModel} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3 px-1">
                            <p className="text-[11px] text-text-muted leading-relaxed italic">{currentModelObj.desc}</p>
                            <div className="flex gap-2 mt-2">
                                {currentModelObj.tags?.map(t => (
                                    <span key={t} className="text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 bg-bg-subtle border border-border-mid rounded text-text-muted">{t}</span>
                                ))}
                            </div>
                        </motion.div>
                    )}
                  </AnimatePresence>

                  {selectedModel === 'custom' && (
                      <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-4">
                        <label className="text-[10px] font-black text-accent uppercase tracking-widest block mb-2">OpenRouter Model ID</label>
                        <input 
                            type="text"
                            value={customModel}
                            onChange={(e) => setCustomModel(e.target.value)}
                            placeholder="e.g. anthropic/claude-3-opus"
                            className="w-full h-12 bg-accent/5 border border-accent/20 rounded-xl px-4 font-mono text-[13px] focus:border-accent outline-none"
                        />
                      </motion.div>
                  )}
               </section>

               <section>
                  <div className="flex justify-between items-center mb-3">
                    <label className="text-[11px] font-black text-text-muted uppercase tracking-widest">{currentProvider.key_label}</label>
                    <a href={currentProvider.key_link} target="_blank" rel="noreferrer" className="text-[10px] font-bold text-accent hover:underline flex items-center gap-1">
                        {currentProvider.key_link_label}
                        <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                    </a>
                  </div>
                  <input 
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder={currentProvider.key_placeholder}
                    className="w-full h-14 bg-bg-subtle border border-border-mid rounded-2xl px-6 font-mono text-[14px] focus:border-accent outline-none transition-all"
                  />
               </section>
            </div>

            {/* Exa Key - Readonly info */}
            <div className="mt-8 pt-8 border-t border-border-light relative z-10">
               <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-orange-50 text-orange-600 flex items-center justify-center shadow-sm">
                    <span className="material-symbols-outlined fill-1">bolt</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                        <p className="text-[14px] font-bold text-text-ink">Exa Search Infrastructure</p>
                        <span className="px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 text-[9px] font-black uppercase tracking-wider">System Provided</span>
                    </div>
                    <p className="text-[12px] text-text-muted font-medium mt-0.5">
                        High-speed research engine is already provided by Guardian. You're all set!
                    </p>
                  </div>
               </div>
            </div>

            <button 
              onClick={handleSave}
              disabled={isVerifying}
              className="w-full h-14 bg-text-ink text-white rounded-2xl font-black uppercase tracking-[0.2em] text-[13px] mt-10 hover:bg-accent transition-all shadow-glow flex items-center justify-center gap-3 disabled:opacity-50 relative z-10 overflow-hidden"
            >
              {isVerifying ? (
                 <>
                   <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                   VERIFYING...
                 </>
              ) : (
                  <>
                    <span className="material-symbols-outlined text-[20px]">save</span>
                    Update Configuration
                  </>
              )}
            </button>
          </div>
        </div>

        {/* Status Panel */}
        <div className="lg:col-span-4 space-y-6">
           <section className="bg-text-ink text-white rounded-[32px] p-8 shadow-card relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-accent/20 rounded-full blur-3xl -mr-16 -mt-16 group-hover:bg-accent/30 transition-all duration-500" />
              <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/40 mb-6">Active Node</h3>
              
              <div className="space-y-6 relative z-10">
                 <div>
                    <div className="flex items-center gap-2 mb-1">
                       <div className={`w-2 h-2 rounded-full ${activeConfig ? 'bg-status-success shadow-glow animate-pulse' : 'bg-status-danger'}`} />
                       <p className="text-[10px] uppercase font-black text-white/30 tracking-widest">Connection</p>
                    </div>
                    <p className="text-[15px] font-bold">{activeConfig ? 'Encrypted & Active' : 'Unconfigured'}</p>
                 </div>
                 
                 <div className="grid grid-cols-2 gap-4">
                    <div>
                       <p className="text-[10px] uppercase font-black text-white/30 mb-1 tracking-widest">Provider</p>
                       <p className="text-[14px] font-bold">{activeConfig ? (PROVIDERS[activeConfig.provider]?.label || activeConfig.provider) : '--'}</p>
                    </div>
                    <div>
                       <p className="text-[10px] uppercase font-black text-white/30 mb-1 tracking-widest">Model</p>
                       <p className="text-[14px] font-bold truncate" title={activeConfig?.model_id}>{activeConfig ? activeConfig.model_id : '--'}</p>
                    </div>
                 </div>
                 
                 {activeConfig && (
                     <div className="pt-4 border-t border-white/10 mt-2">
                        <p className="text-[10px] text-white/40 font-medium">Last updated: {new Date(activeConfig.updated_at).toLocaleDateString()}</p>
                     </div>
                 )}
              </div>
           </section>

           <section className="bg-white border border-border-light rounded-[32px] p-8 shadow-soft">
              <h3 className="text-[12px] font-black uppercase tracking-widest text-text-muted mb-6">System Health</h3>
              <div className="space-y-4">
                 <div className="flex justify-between items-center px-4 py-3 bg-bg-subtle rounded-xl border border-border-light">
                    <span className="text-[11px] font-bold text-text-muted uppercase">Supabase</span>
                    <span className={`w-2 h-2 rounded-full ${dbError ? 'bg-status-danger' : 'bg-status-success shadow-glow'}`} />
                 </div>
                 <div className="flex justify-between items-center px-4 py-3 bg-bg-subtle rounded-xl border border-border-light">
                    <span className="text-[11px] font-bold text-text-muted uppercase">EXA API</span>
                    <span className="w-2 h-2 rounded-full bg-status-success shadow-glow" />
                 </div>
                 
                 <div className="pt-4 mt-2">
                    <p className="text-[10px] font-black text-text-muted uppercase tracking-widest mb-3 px-1">Maintenance</p>
                    <button 
                        onClick={handlePurge}
                        disabled={isPurging}
                        className="w-full py-4 border border-status-danger/20 bg-status-danger/5 text-status-danger rounded-2xl text-[11px] font-black uppercase tracking-widest hover:bg-status-danger hover:text-white transition-all flex items-center justify-center gap-2"
                    >
                        {isPurging ? (
                            <div className="w-3 h-3 border-2 border-status-danger border-t-transparent rounded-full animate-spin" />
                        ) : (
                            <span className="material-symbols-outlined text-[16px]">delete_forever</span>
                        )}
                        Purge System Data
                    </button>
                    <p className="text-[9px] text-text-muted mt-3 text-center leading-relaxed">
                        ⚠ Irreversibly erase all goals, income, and analysis history.
                    </p>
                 </div>
              </div>
           </section>
        </div>
      </div>
    </div>
  );
}
