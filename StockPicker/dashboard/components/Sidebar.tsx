'use client';

import {
  LayoutDashboard,
  Search,
  PieChart,
  TrendingUp,
  Settings,
  Wallet,
  Zap,
  BarChart3,
} from 'lucide-react';

type View = 'dashboard' | 'scanner' | 'stock' | 'portfolio' | 'trade' | 'optimizer' | 'settings';

interface SidebarProps {
  currentView: View;
  onViewChange: (view: View) => void;
}

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'scanner', label: 'Market Scanner', icon: Search },
  { id: 'portfolio', label: 'Portfolio', icon: PieChart },
  { id: 'trade', label: 'Trade', icon: TrendingUp },
  { id: 'optimizer', label: 'Optimizer', icon: Zap },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ currentView, onViewChange }: SidebarProps) {
  return (
    <aside className="w-64 bg-[#1a1a2e] border-r border-[#2a2a4a] flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-[#2a2a4a]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center">
            <BarChart3 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">StockPicker</h1>
            <p className="text-xs text-gray-400">AI Trading System</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id || 
              (currentView === 'stock' && item.id === 'dashboard');
            
            return (
              <li key={item.id}>
                <button
                  onClick={() => onViewChange(item.id as View)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
                    ${isActive 
                      ? 'bg-primary-600/20 text-primary-400 border border-primary-600/30' 
                      : 'text-gray-400 hover:bg-white/5 hover:text-white'
                    }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[#2a2a4a]">
        <div className="card bg-gradient-to-r from-primary-900/50 to-primary-800/30">
          <div className="flex items-center gap-3">
            <Wallet className="w-8 h-8 text-primary-400" />
            <div>
              <p className="text-xs text-gray-400">Paper Trading</p>
              <p className="text-sm font-semibold text-white">$100,000.00</p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
