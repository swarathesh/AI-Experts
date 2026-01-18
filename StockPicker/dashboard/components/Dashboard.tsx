'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, BarChart2, Zap, DollarSign } from 'lucide-react';
import StockChart from './charts/StockChart';
import api from '@/lib/api';

interface DashboardProps {
  onStockSelect: (symbol: string) => void;
}

interface HotStock {
  symbol: string;
  price: number;
  change: number;
  signal: string;
  confidence: number;
  rsi: number;
  reasons: string[];
}

export default function Dashboard({ onStockSelect }: DashboardProps) {
  const [hotStocks, setHotStocks] = useState<{ top_buys: HotStock[]; top_sells: HotStock[] }>({ top_buys: [], top_sells: [] });
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  const fetchHotStocks = async () => {
    try {
      setLoading(true);
      console.log('🔍 Fetching hot stocks from:', `/api/hot-stocks`);
      const response = await api.get(`/api/hot-stocks`);
      console.log('✅ Hot stocks received:', response.data);
      setHotStocks(response.data);
    } catch (error) {
      console.error('❌ Error fetching hot stocks:', error);
      // Set empty data on error
      setHotStocks({ top_buys: [], top_sells: [] });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHotStocks();
  }, []);

  const runScan = async () => {
    setScanning(true);
    await fetchHotStocks();
    setScanning(false);
  };

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'STRONG_BUY': return 'signal-strong-buy';
      case 'BUY': return 'signal-buy';
      case 'HOLD': return 'signal-hold';
      case 'SELL': return 'signal-sell';
      case 'STRONG_SELL': return 'signal-strong-sell';
      default: return 'signal-hold';
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400">AI-powered market analysis and signals</p>
        </div>
        <button 
          onClick={runScan}
          disabled={scanning}
          className="btn btn-primary flex items-center gap-2"
        >
          <Activity className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
          {scanning ? 'Scanning...' : 'Run Market Scan'}
        </button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Buy Signals</p>
              <p className="text-2xl font-bold text-green-400">{hotStocks.top_buys?.length || 0}</p>
            </div>
            <TrendingUp className="w-8 h-8 text-green-400/30" />
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Sell Signals</p>
              <p className="text-2xl font-bold text-red-400">{hotStocks.top_sells?.length || 0}</p>
            </div>
            <TrendingDown className="w-8 h-8 text-red-400/30" />
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Avg Confidence</p>
              <p className="text-2xl font-bold text-primary-400">
                {hotStocks.top_buys?.length > 0 
                  ? Math.round(hotStocks.top_buys.reduce((a, b) => a + b.confidence, 0) / hotStocks.top_buys.length * 100)
                  : 0}%
              </p>
            </div>
            <BarChart2 className="w-8 h-8 text-primary-400/30" />
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Stocks Analyzed</p>
              <p className="text-2xl font-bold text-white">
                {(hotStocks.top_buys?.length || 0) + (hotStocks.top_sells?.length || 0)}
              </p>
            </div>
            <Zap className="w-8 h-8 text-yellow-400/30" />
          </div>
        </div>
      </div>

      {/* Hot Stocks Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Buy Signals */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-400" />
              Top Buy Signals
            </h2>
            <span className="text-xs text-gray-400">Highest confidence</span>
          </div>
          
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-16 loading-shimmer rounded-lg" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {hotStocks.top_buys?.slice(0, 5).map((stock) => (
                <div
                  key={stock.symbol}
                  onClick={() => onStockSelect(stock.symbol)}
                  className="flex items-center justify-between p-3 rounded-lg bg-green-500/5 border border-green-500/10 hover:bg-green-500/10 cursor-pointer transition-all"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                      <span className="text-sm font-bold text-green-400">{stock.symbol.slice(0, 2)}</span>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white">{stock.symbol}</span>
                        <span className={`signal-badge ${getSignalColor(stock.signal)}`}>
                          {stock.signal.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400">
                        RSI: {stock.rsi} | Confidence: {Math.round(stock.confidence * 100)}%
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-white">${stock.price?.toFixed(2)}</div>
                    <div className={stock.change >= 0 ? 'text-green-400 text-sm' : 'text-red-400 text-sm'}>
                      {stock.change >= 0 ? '+' : ''}{stock.change?.toFixed(2)}%
                    </div>
                  </div>
                </div>
              ))}
              
              {(!hotStocks.top_buys || hotStocks.top_buys.length === 0) && (
                <div className="text-center text-gray-400 py-8">
                  No buy signals found. Run a market scan.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Top Sell Signals */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-red-400" />
              Top Sell Signals
            </h2>
            <span className="text-xs text-gray-400">Highest confidence</span>
          </div>
          
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-16 loading-shimmer rounded-lg" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {hotStocks.top_sells?.slice(0, 5).map((stock) => (
                <div
                  key={stock.symbol}
                  onClick={() => onStockSelect(stock.symbol)}
                  className="flex items-center justify-between p-3 rounded-lg bg-red-500/5 border border-red-500/10 hover:bg-red-500/10 cursor-pointer transition-all"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
                      <span className="text-sm font-bold text-red-400">{stock.symbol.slice(0, 2)}</span>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white">{stock.symbol}</span>
                        <span className={`signal-badge ${getSignalColor(stock.signal)}`}>
                          {stock.signal.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400">
                        RSI: {stock.rsi} | Confidence: {Math.round(stock.confidence * 100)}%
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-white">${stock.price?.toFixed(2)}</div>
                    <div className={stock.change >= 0 ? 'text-green-400 text-sm' : 'text-red-400 text-sm'}>
                      {stock.change >= 0 ? '+' : ''}{stock.change?.toFixed(2)}%
                    </div>
                  </div>
                </div>
              ))}
              
              {(!hotStocks.top_sells || hotStocks.top_sells.length === 0) && (
                <div className="text-center text-gray-400 py-8">
                  No sell signals found.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Featured Stock Chart */}
      {hotStocks.top_buys && hotStocks.top_buys.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Featured: {hotStocks.top_buys[0]?.symbol}</h2>
            <button 
              onClick={() => onStockSelect(hotStocks.top_buys[0]?.symbol)}
              className="btn btn-ghost text-sm"
            >
              View Details →
            </button>
          </div>
          <StockChart symbol={hotStocks.top_buys[0]?.symbol} height={300} />
        </div>
      )}
    </div>
  );
}
