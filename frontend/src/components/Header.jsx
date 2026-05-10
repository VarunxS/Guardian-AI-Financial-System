import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import UploadModal from './UploadModal';

export default function Header() {
  const location = useLocation();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const mainElement = document.getElementById('main-content-area');
      if (mainElement) {
        setIsScrolled(mainElement.scrollTop > 20);
      }
    };
    
    const mainElement = document.getElementById('main-content-area');
    if (mainElement) {
      mainElement.addEventListener('scroll', handleScroll);
      return () => mainElement.removeEventListener('scroll', handleScroll);
    }
  }, []);

  return (
    <>
      <header 
        className={`h-24 sticky top-0 z-40 transition-all duration-300 flex items-center justify-between px-10 shrink-0 ${
          isScrolled 
            ? 'bg-white/80 backdrop-blur-md border-b border-border-light' 
            : 'bg-transparent'
        }`}
      >
        <div className="flex items-center gap-6">
        </div>

        <div className="flex items-center gap-4">
          <button className="w-10 h-10 rounded-full border border-border-light flex items-center justify-center text-text-body hover:bg-bg-subtle transition-all">
            <span className="material-symbols-outlined text-[20px]">notifications</span>
          </button>
          <button 
            onClick={() => setIsUploadOpen(true)}
            className="h-11 px-6 bg-accent hover:bg-accent-hover text-white text-[13px] font-bold rounded-2xl transition-all flex items-center justify-center gap-2 shadow-glow active:scale-95"
          >
            <span className="material-symbols-outlined text-[18px] fill-1">add_circle</span>
            Analyze Statement
          </button>
        </div>
      </header>

      <UploadModal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} />
    </>
  );
}
