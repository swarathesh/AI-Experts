'use client';

import { useState, useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import Dashboard from '@/components/Dashboard';
import Scanner from '@/components/Scanner';
import StockDetail from '@/components/StockDetail';
import Portfolio from '@/components/Portfolio';
import Trade from '@/components/Trade';
import Optimizer from '@/components/Optimizer';
import Settings from '@/components/Settings';
import Header from '@/components/Header';
import { API_BASE } from '@/lib/api';

type View = 'dashboard' | 'scanner' | 'stock' | 'portfolio' | 'trade' | 'optimizer' | 'settings';

export default function Home() {
  const [currentView, setCurrentView] = useState<View>('dashboard');
  const [selectedStock, setSelectedStock] = useState<string | null>(null);
  const [isApiConnected, setIsApiConnected] = useState<boolean>(false);

  useEffect(() => {
    // Check API connection
    const checkConnection = async () => {
      try {
        console.log('🔍 Checking API connection at', `${API_BASE}/api/health`);
        const response = await fetch(`${API_BASE}/api/health`);
        const data = await response.json();
        console.log('✅ API Connected:', data);
        setIsApiConnected(true);
      } catch (error) {
        console.error('❌ API Connection Failed:', error);
        console.error(`   Make sure backend is running on ${API_BASE}`);
        console.error('   Run: cd /workspaces/AI-Experts/StockPicker && chmod +x start_backend_simple.sh && ./start_backend_simple.sh');
        setIsApiConnected(false);
      }
    };

    // Check immediately
    checkConnection();

    // Re-check every 5 seconds
    const interval = setInterval(checkConnection, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStockSelect = (symbol: string) => {
    setSelectedStock(symbol);
    setCurrentView('stock');
  };

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard onStockSelect={handleStockSelect} />;
      case 'scanner':
        return <Scanner onStockSelect={handleStockSelect} />;
      case 'stock':
        return <StockDetail symbol={selectedStock || 'AAPL'} onBack={() => setCurrentView('dashboard')} />;
      case 'portfolio':
        return <Portfolio />;
      case 'trade':
        return <Trade />;
      case 'optimizer':
        return <Optimizer />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard onStockSelect={handleStockSelect} />;
    }
  };

  return (
    <div className="flex h-screen bg-[#0f0f1a]">
      <Sidebar currentView={currentView} onViewChange={setCurrentView} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header isConnected={isApiConnected} />
        <main className="flex-1 overflow-y-auto p-6">
          {renderView()}
        </main>
      </div>
    </div>
  );
}
