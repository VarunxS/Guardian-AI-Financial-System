import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getUserId } from '../utils/auth';

export default function UploadModal({ isOpen, onClose }) {
  const [file, setFile] = useState(null);
  const [source, setSource] = useState('bank_csv');
  const [statementMonths, setStatementMonths] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loadingMessage, setLoadingMessage] = useState("Guardian Analyzing...");
  const [isSampleMode, setIsSampleMode] = useState(false);
  const [monthlyIncome, setMonthlyIncome] = useState(localStorage.getItem('GUARDIAN_INCOME') || 100000);

  useEffect(() => {
    let interval;
    if (isLoading) {
      const messages = [
        "Initializing Guardian Pipeline...",
        "Parsing Statements (PyMuPDF)...",
        "Insights Agent checking for anomalies...",
        "Reward Optimizer scanning 100+ cards...",
        "Budget Goals Agent computing forecasts...",
        "Finalizing Intelligence Report..."
      ];
      let i = 0;
      setLoadingMessage(messages[0]);
      interval = setInterval(() => {
        i = (i + 1);
        if (i < messages.length) {
          setLoadingMessage(messages[i]);
        }
      }, 3000);
    } else {
      setLoadingMessage("Guardian Analyzing...");
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      
      const fileName = selectedFile.name.toLowerCase();
      if (fileName.endsWith('.csv')) {
        setSource('bank_csv');
      } else if (fileName.endsWith('.pdf')) {
        if (source === 'bank_csv') {
          setSource('credit_card_pdf');
        }
      }
      setError(null);
    }
  };

  const handleUpload = async (e, isSample = false) => {
    if (!isSample && !file) {
      setError("Please select a file first.");
      return;
    }

    const apiKey = localStorage.getItem('GUARDIAN_API_KEY') || "";
    localStorage.setItem('GUARDIAN_INCOME', monthlyIncome);

    setIsLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    if (!isSample) {
        formData.append('file', file);
        formData.append('source', source);
        formData.append('statement_months', statementMonths.toString());
    }
    formData.append('user_id', getUserId());
    formData.append('use_sample', isSample ? 'true' : 'false');
    formData.append('monthly_income', monthlyIncome.toString());
    if (apiKey) formData.append('api_key', apiKey);
    if (isSample) {
        formData.append('source', 'credit_card_pdf');
        formData.append('statement_months', '6');
    }

    try {
      const res = await fetch('http://localhost:8000/api/analyse', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || `Upload failed (${res.status})`);
      }

      const data = await res.json();
      sessionStorage.setItem('GUARDIAN_ANALYSIS', JSON.stringify(data));
      sessionStorage.setItem('GUARDIAN_ANALYSIS_TIME', new Date().toISOString());
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-text-ink/40 backdrop-blur-md"
        />
        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-xl bg-bg-surface border border-border-light rounded-[40px] p-10 shadow-2xl"
        >
          <div className="flex justify-between items-center mb-8 pb-6 border-b border-border-light">
            <div className="flex items-center gap-3">
               <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                 <span className="material-symbols-outlined text-[24px] fill-1">upload_file</span>
               </div>
               <div>
                  <h2 className="text-[20px] font-bold text-text-ink leading-none">Analyze Statements</h2>
                  <p className="text-[11px] text-text-muted uppercase font-bold tracking-widest mt-1">Guardian Intelligence Protocol</p>
               </div>
            </div>
            <button onClick={onClose} className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-bg-subtle transition-colors">
              <span className="material-symbols-outlined text-[20px] text-text-muted">close</span>
            </button>
          </div>

          {!result ? (
            <div className="space-y-8">
              <div>
                <p className="text-[12px] font-bold text-text-ink uppercase tracking-wider mb-4">Select Source Engine</p>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: 'bank_csv', label: 'Bank CSV', icon: 'account_balance' },
                    { id: 'credit_card_pdf', label: 'Card PDF', icon: 'credit_card' },
                    { id: 'upi_pdf', label: 'UPI PDF', icon: 'payments' }
                  ].map(t => (
                    <button
                      key={t.id}
                      onClick={() => setSource(t.id)}
                      className={`flex flex-col items-center gap-2 py-4 px-3 rounded-2xl border transition-all ${
                        source === t.id 
                          ? 'bg-accent/5 border-accent text-accent shadow-glow' 
                          : 'bg-bg-subtle border-border-light text-text-muted hover:border-border-mid hover:text-text-body'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[20px]">{t.icon}</span>
                      <span className="text-[12px] font-bold">{t.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-[12px] font-bold text-text-ink uppercase tracking-wider mb-4">Statement Period</p>
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { val: 1, label: '1 Month' },
                    { val: 3, label: '3 Months' },
                    { val: 6, label: '6 Months' },
                    { val: 12, label: '1 Year' }
                  ].map(p => (
                    <button
                      key={p.val}
                      onClick={() => setStatementMonths(p.val)}
                      className={`flex items-center justify-center py-3 px-2 rounded-xl border transition-all ${
                        statementMonths === p.val 
                          ? 'bg-accent/5 border-accent text-accent shadow-soft font-bold' 
                          : 'bg-bg-subtle border-border-light text-text-muted hover:border-border-mid hover:text-text-body font-medium'
                      }`}
                    >
                      <span className="text-[12px]">{p.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-[12px] font-bold text-text-ink uppercase tracking-wider mb-4">Adjust Monthly Income</p>
                <div className="relative">
                  <span className="absolute left-5 top-1/2 -translate-y-1/2 text-text-muted font-mono font-bold">₹</span>
                  <input 
                    type="number" 
                    value={monthlyIncome} 
                    onChange={(e) => setMonthlyIncome(e.target.value)}
                    className="w-full h-14 bg-bg-subtle border border-border-light rounded-2xl pl-10 pr-6 text-[15px] font-mono font-bold text-text-ink focus:border-accent focus:bg-accent/5 outline-none transition-all"
                  />
                </div>
              </div>

              <div className="relative group">
                <input 
                  type="file" 
                  accept=".csv,.pdf" 
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" 
                />
                <div className={`w-full border-2 border-dashed rounded-3xl p-10 flex flex-col items-center justify-center transition-all ${
                  file ? 'border-accent bg-accent/5' : 'border-border-mid group-hover:border-accent bg-bg-subtle'
                }`}>
                  <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 ${file ? 'bg-accent text-white shadow-glow' : 'bg-bg-surface border border-border-light text-text-muted shadow-soft'}`}>
                    <span className="material-symbols-outlined text-[28px] fill-1">{file ? 'task' : 'add_circle'}</span>
                  </div>
                  <p className="text-[15px] font-bold text-text-ink mb-1">
                    {file ? file.name : 'Drop statement here'}
                  </p>
                  <p className="text-[12px] text-text-muted font-medium">
                    {file ? `${(file.size / 1024).toFixed(1)} KB` : 'Supports standard Indian banking formats'}
                  </p>
                </div>
              </div>

              {error && (
                <div className="p-5 rounded-2xl bg-status-danger/5 border border-status-danger/10 text-[13px] text-status-danger font-bold flex items-start gap-3">
                   <span className="material-symbols-outlined text-[18px]">error</span>
                   <span>{error}</span>
                </div>
              )}

              <div className="bg-bg-subtle border border-border-light rounded-[24px] p-6 flex flex-col items-center gap-4">
                 <p className="text-[12px] text-text-muted font-bold text-center">Don't have a statement handy?</p>
                 <button 
                   onClick={(e) => handleUpload(e, true)}
                   disabled={isLoading}
                   className="text-[13px] font-black text-accent uppercase tracking-widest hover:underline flex items-center gap-2"
                 >
                   <span className="material-symbols-outlined text-[18px]">lab_profile</span>
                   Try with 6-Month Sample PDF
                 </button>
              </div>

              <button 
                onClick={handleUpload}
                disabled={isLoading || !file}
                className="w-full h-14 bg-text-ink text-white font-bold rounded-2xl transition-all disabled:opacity-50 hover:bg-accent flex justify-center items-center gap-3 text-[15px] shadow-card active:scale-[0.98]"
              >
                {isLoading ? (
                  <><div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> <span className="animate-pulse">{loadingMessage}</span></>
                ) : (
                  <><span className="material-symbols-outlined text-[20px] fill-1">bolt</span> Execute Analysis</>
                )}
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center space-y-6 py-4">
              <div className="w-20 h-20 rounded-full bg-status-success/10 border border-status-success/20 flex items-center justify-center mb-2">
                <span className="material-symbols-outlined text-status-success text-[40px] fill-1">check_circle</span>
              </div>
              <div>
                <h3 className="text-[24px] font-bold text-text-ink mb-2 tracking-tight">Intelligence Sync Complete</h3>
                <p className="text-[15px] text-text-body max-w-sm leading-relaxed opacity-80 italic">"{result.executive_summary}"</p>
              </div>
              <div className="grid grid-cols-3 gap-4 w-full mt-6">
                <div className="bg-bg-subtle border border-border-light rounded-2xl p-5 shadow-soft">
                  <p className="text-[10px] text-text-muted uppercase font-bold tracking-widest mb-2">Health</p>
                  <p className="text-[24px] font-mono text-status-success font-bold">{result.health_score}%</p>
                </div>
                <div className="bg-bg-subtle border border-border-light rounded-2xl p-5 shadow-soft">
                  <p className="text-[10px] text-text-muted uppercase font-bold tracking-widest mb-2">Flags</p>
                  <p className="text-[24px] font-mono text-text-ink font-bold">{result.findings_count}</p>
                </div>
                <div className="bg-status-danger/5 border border-status-danger/10 rounded-2xl p-5 shadow-soft">
                  <p className="text-[10px] text-status-danger uppercase font-bold tracking-widest mb-2">Leak</p>
                  <p className="text-[24px] font-mono text-status-danger font-bold">₹{Math.round(result.total_monthly_at_risk).toLocaleString()}</p>
                </div>
              </div>
              <button 
                onClick={() => { onClose(); window.location.reload(); }} 
                className="w-full h-14 bg-bg-subtle border border-border-light hover:bg-bg-hover text-text-ink font-bold rounded-2xl transition-all text-[15px] shadow-soft mt-6"
              >
                Enter Analysis Console
              </button>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
