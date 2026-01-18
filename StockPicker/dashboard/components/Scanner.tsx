'use client';

import { useState, useEffect } from 'react';
import { Search, Filter, ArrowUpDown, Play, Loader2 } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';

interface ScannerProps {
  onStockSelect: (symbol: string) => void;
}

interface ScanResult {
  symbol: string;
  price: number;
  change: number;
  signal: string;
  confidence: number;
  technical_score: number;
  sentiment_score: number;
  combined_score: number;
  rsi: number;
  volume: number;
  reasons: string[];
}

export default function Scanner({ onStockSelect }: ScannerProps) {
  const [results, setResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<'all' | 'buy' | 'sell' | 'hold'>('all');
  const [sortBy, setSortBy] = useState<'combined_score' | 'confidence' | 'change'>('combined_score');
  const [sortDesc, setSortDesc] = useState(true);
  const [customSymbols, setCustomSymbols] = useState('');

  const runScan = async () => {
    setLoading(true);
    try {
      const symbols = customSymbols.trim() 
        ? customSymbols.split(',').map(s => s.trim().toUpperCase())
        : null;
      
      console.log('🔍 Running market scan with symbols:', symbols || 'default watchlist');
      const response = await api.post(`/api/scan`, { symbols });
      console.log('✅ Scan results received:', response.data);
      setResults(response.data.results);
    } catch (error) {
      console.error('❌ Scan error:', error);
      if (axios.isAxiosError(error)) {
        console.error('   Response:', error.response?.data);
        console.error('   Status:', error.response?.status);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runScan();
  }, []);

  const filteredResults = results
    .filter(r => {
      if (filter === 'buy') return r.signal === 'BUY' || r.signal === 'STRONG_BUY';
      if (filter === 'sell') return r.signal === 'SELL' || r.signal === 'STRONG_SELL';
      if (filter === 'hold') return r.signal === 'HOLD';
      return true;
    })
    .sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      return sortDesc ? bVal - aVal : aVal - bVal;
    });

  const getSignalBadge = (signal: string) => {
    const colors: Record<string, string> = {
      'STRONG_BUY': 'bg-green-500/20 text-green-400 border-green-500/30',
      'BUY': 'bg-green-400/20 text-green-300 border-green-400/30',
      'HOLD': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      'SELL': 'bg-red-400/20 text-red-300 border-red-400/30',
      'STRONG_SELL': 'bg-red-500/20 text-red-400 border-red-500/30',
    };
    return colors[signal] || colors['HOLD'];
  };

  const getScoreBar = (score: number) => {
    const percentage = ((score + 1) / 2) * 100; // Convert -1 to 1 range to 0-100
    const color = score > 0.3 ? 'bg-green-500' : score < -0.3 ? 'bg-red-500' : 'bg-yellow-500';
    return (
      <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} transition-all`} 
          style={{ width: `${percentage}%` }}
        />
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Market Scanner</h1>
          <p className="text-gray-400">AI-powered signal detection across your watchlist</p>
        </div>
      </div>

      {/* Controls */}
      <div className="card">
        <div className="flex flex-wrap gap-4 items-center">
          {/* Custom Symbols Input */}
          <div className="flex-1 min-w-[300px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Enter symbols (e.g., AAPL, MSFT, GOOGL) or leave empty for default"
                value={customSymbols}
                onChange={(e) => setCustomSymbols(e.target.value)}
                className="w-full bg-[#0f0f1a] border border-[#2a2a4a] rounded-lg pl-10 pr-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-primary-500"
              />
            </div>
          </div>

          {/* Filter Buttons */}
          <div className="flex gap-2">
            {['all', 'buy', 'sell', 'hold'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f as typeof filter)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                  ${filter === f 
                    ? 'bg-primary-600 text-white' 
                    : 'bg-[#0f0f1a] text-gray-400 hover:text-white'
                  }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="bg-[#0f0f1a] border border-[#2a2a4a] rounded-lg px-3 py-2 text-white text-sm"
          >
            <option value="combined_score">Combined Score</option>
            <option value="confidence">Confidence</option>
            <option value="change">Price Change</option>
          </select>

          <button
            onClick={() => setSortDesc(!sortDesc)}
            className="p-2 rounded-lg bg-[#0f0f1a] border border-[#2a2a4a] text-gray-400 hover:text-white"
          >
            <ArrowUpDown className="w-4 h-4" />
          </button>

          {/* Scan Button */}
          <button
            onClick={runScan}
            disabled={loading}
            className="btn btn-primary flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {loading ? 'Scanning...' : 'Run Scan'}
          </button>
        </div>
      </div>

      {/* Results Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 text-sm border-b border-[#2a2a4a]">
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Change</th>
                <th className="px-4 py-3">Signal</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">RSI</th>
                <th className="px-4 py-3">Reasons</th>
                <th className="px-4 py-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i}>
                    <td colSpan={9} className="px-4 py-4">
                      <div className="h-8 loading-shimmer rounded" />
                    </td>
                  </tr>
                ))
              ) : filteredResults.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center text-gray-400 py-12">
                    No results found. Adjust filters or run a new scan.
                  </td>
                </tr>
              ) : (
                filteredResults.map((stock) => (
                  <tr 
                    key={stock.symbol} 
                    className="stock-row border-b border-[#2a2a4a]/50"
                    onClick={() => onStockSelect(stock.symbol)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded bg-primary-500/20 flex items-center justify-center">
                          <span className="text-xs font-bold text-primary-400">
                            {stock.symbol.slice(0, 2)}
                          </span>
                        </div>
                        <span className="font-semibold text-white">{stock.symbol}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-white font-medium">
                      ${stock.price?.toFixed(2)}
                    </td>
                    <td className={`px-4 py-3 font-medium ${stock.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {stock.change >= 0 ? '+' : ''}{stock.change?.toFixed(2)}%
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${getSignalBadge(stock.signal)}`}>
                        {stock.signal.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-white">{Math.round(stock.confidence * 100)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getScoreBar(stock.combined_score)}
                        <span className="text-xs text-gray-400">{stock.combined_score?.toFixed(2)}</span>
                      </div>
                    </td>
                    <td className={`px-4 py-3 ${
                      stock.rsi < 30 ? 'text-green-400' : 
                      stock.rsi > 70 ? 'text-red-400' : 
                      'text-gray-300'
                    }`}>
                      {stock.rsi?.toFixed(1)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="max-w-[200px] text-xs text-gray-400 truncate">
                        {stock.reasons?.slice(0, 2).join(', ')}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          onStockSelect(stock.symbol);
                        }}
                        className="btn btn-ghost text-xs"
                      >
                        Analyze
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary */}
      {results.length > 0 && (
        <div className="text-sm text-gray-400 text-center">
          Showing {filteredResults.length} of {results.length} stocks | 
          {' '}{results.filter(r => r.signal.includes('BUY')).length} Buy signals | 
          {' '}{results.filter(r => r.signal.includes('SELL')).length} Sell signals
        </div>
      )}
    </div>
  );
}
