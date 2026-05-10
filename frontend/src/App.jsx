import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Findings from './pages/Findings';
import RewardOptimiser from './pages/RewardOptimiser';
import BudgetGoals from './pages/BudgetGoals';
import AskGuardian from './pages/AskGuardian';
import Settings from './pages/Settings';

import Header from './components/Header';

function Layout() {
  const location = useLocation();
  const isLanding = location.pathname === '/';

  if (isLanding) {
    return <Landing />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-bg-canvas text-text-ink font-sans antialiased p-6 lg:p-8">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative bg-bg-surface rounded-3xl shadow-soft border border-border-light ml-6">
        <main 
          id="main-content-area"
          className={`flex-1 flex flex-col min-w-0 overflow-y-auto ${location.pathname === '/ask' ? '' : 'px-10 pt-16 pb-12'}`}
        >
          <div className="w-full max-w-[1400px] mx-auto flex-1 flex flex-col h-full">
            <Routes>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/findings" element={<Findings />} />
              <Route path="/rewards" element={<RewardOptimiser />} />
              <Route path="/budget" element={<BudgetGoals />} />
              <Route path="/ask" element={<AskGuardian />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/*" element={<Layout />} />
      </Routes>
    </Router>
  );
}

export default App;
