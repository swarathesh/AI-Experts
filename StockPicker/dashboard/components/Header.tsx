'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, Activity, Wifi, WifiOff } from 'lucide-react';

interface HeaderProps {
  isConnected: boolean;
}

export default function Header({ isConnected }: HeaderProps) {
  const [time, setTime] = useState<string>('');
  const [marketStatus, setMarketStatus] = useState<'open' | 'closed' | 'pre' | 'after'>('closed');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const etTime = now.toLocaleString('en-US', { 
        timeZone: 'America/New_York',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
      setTime(etTime);
      
      // Check market hours (simplified)
      const hour = parseInt(now.toLocaleString('en-US', { 
        timeZone: 'America/New_York', 
        hour: 'numeric', 
        hour12: false 
      }));
      const day = now.getDay();
      
      if (day === 0 || day === 6) {
        setMarketStatus('closed');
      } else if (hour >= 9.5 && hour < 16) {
        setMarketStatus('open');
      } else if (hour >= 4 && hour < 9.5) {
        setMarketStatus('pre');
      } else if (hour >= 16 && hour < 20) {
        setMarketStatus('after');
      } else {
        setMarketStatus('closed');
      }
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="bg-[#1a1a2e] border-b border-[#2a2a4a] px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          {/* Market Status */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              marketStatus === 'open' ? 'bg-green-400 animate-pulse' :
              marketStatus === 'pre' || marketStatus === 'after' ? 'bg-yellow-400' :
              'bg-red-400'
            }`} />
            <span className="text-sm text-gray-400">
              Market: <span className={`font-medium ${
                marketStatus === 'open' ? 'text-green-400' :
                marketStatus === 'pre' ? 'text-yellow-400' :
                marketStatus === 'after' ? 'text-yellow-400' :
                'text-red-400'
              }`}>
                {marketStatus === 'open' ? 'Open' :
                 marketStatus === 'pre' ? 'Pre-Market' :
                 marketStatus === 'after' ? 'After-Hours' :
                 'Closed'}
              </span>
            </span>
          </div>
          
          {/* Time */}
          <div className="text-sm text-gray-400">
            {time} <span className="text-gray-500">ET</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* API Status */}
          <div className="flex items-center gap-2">
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4 text-green-400" />
                <span className="text-sm text-green-400">API Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-400" />
                <span className="text-sm text-red-400">API Disconnected</span>
              </>
            )}
          </div>

          {/* Refresh Button */}
          <button className="btn btn-ghost flex items-center gap-2 text-sm">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>
    </header>
  );
}
