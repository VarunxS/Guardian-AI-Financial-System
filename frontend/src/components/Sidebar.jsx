import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import UploadModal from './UploadModal';

const NAV_ITEMS = [
  { path: '/dashboard', icon: 'grid_view', label: 'Overview' },
  { path: '/findings', icon: 'troubleshoot', label: 'Audit', badge: true },
  { path: '/rewards', icon: 'auto_awesome', label: 'Rewards' },
  { path: '/budget', icon: 'track_changes', label: 'Strategy' },
  { path: '/ask', icon: 'chat_bubble', label: 'Guardian', iconFill: 1 },
];

export default function Sidebar() {
  const location = useLocation();
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  return (
    <aside className="w-[100px] flex-shrink-0 hidden lg:flex flex-col h-full sticky top-0 bg-bg-canvas border-r border-border-light py-8 z-50">
      
      {/* Brand Logo */}
      <div className="mb-12 w-full flex justify-center">
        <NavLink to="/" className="w-12 h-12 bg-accent rounded-2xl shadow-glow flex items-center justify-center text-white hover:scale-105 active:scale-95 transition-all block cursor-pointer">
          <span className="material-symbols-outlined text-[28px] font-bold">shield</span>
        </NavLink>
      </div>

      {/* Nav Links */}
      <nav className="flex-1 w-full flex flex-col gap-6">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `
              relative w-full group flex flex-col items-center gap-1.5 transition-all
              ${isActive ? 'text-accent' : 'text-text-muted hover:text-text-ink'}
            `}
          >
            {({ isActive }) => (
              <>
                <div className={`
                  w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300
                  ${isActive ? 'bg-accent/5' : 'bg-transparent group-hover:bg-bg-subtle'}
                `}>
                  <span className={`
                    material-symbols-outlined text-[24px] 
                    ${isActive ? 'fill-1' : ''}
                  `}>
                    {item.icon}
                  </span>
                  
                  {item.badge && (
                    <span className="absolute top-2 right-1/2 -translate-x-[-12px] w-2 h-2 bg-status-danger rounded-full border-2 border-bg-canvas" />
                  )}
                </div>
                
                {isActive && (
                  <motion.div 
                    layoutId="activeNav"
                    className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-accent rounded-l-full"
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom Actions */}
      <div className="flex flex-col gap-6 pb-4 w-full">
        <div className="w-full flex justify-center">
          <button 
            data-upload-trigger="true"
            onClick={() => setIsUploadOpen(true)}
            className="w-14 h-14 bg-accent hover:bg-accent-hover text-white rounded-2xl transition-all flex items-center justify-center shadow-glow active:scale-95 group relative"
            title="Analyze Statement"
          >
            <span className="material-symbols-outlined text-[24px] fill-1">add_circle</span>
            {/* Tooltip */}
            <div className="absolute left-full ml-4 px-3 py-2 bg-text-ink text-white text-[11px] font-bold rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-[100] shadow-card">
              Analyze Statement
            </div>
          </button>
        </div>

        <NavLink to="/settings" className={({ isActive }) => `relative w-full group flex flex-col items-center gap-1.5 transition-all ${isActive ? 'text-accent' : 'text-text-muted hover:text-text-ink'}`}>
          {({ isActive }) => (
            <>
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300 ${isActive ? 'bg-accent/5' : 'bg-transparent group-hover:bg-bg-subtle'}`}>
                <span className={`material-symbols-outlined text-[24px] ${isActive ? 'fill-1' : ''}`}>settings</span>
              </div>
              {isActive && (
                <motion.div layoutId="activeNav" className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-accent rounded-l-full" transition={{ type: 'spring', stiffness: 300, damping: 30 }} />
              )}
            </>
          )}
        </NavLink>
        
      </div>

      <UploadModal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} />
    </aside>
  );
}
