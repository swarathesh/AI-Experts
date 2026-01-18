'use client';

import { useState, useEffect } from 'react';
import { ArrowLeft, TrendingUp, TrendingDown, Target, ShieldAlert, Loader2, DollarSign, Activity } from 'lucide-react';
import api from '@/lib/api';
import CandlestickChart from './charts/CandlestickChart';
import IndicatorChart from './charts/IndicatorChart';
import VolumeChart from './charts/VolumeChart';

const API_BASE = 'http://localhost:8000';

interface StockDetailProps {
  symbol: string;
  onBack: () => void;
}

interface StockAnalysis {
  symbol: string;
  price: number;
  signal: {
    type: string;
    confidence: number;
    reasons: string[];
  };
  sentiment: {
    score: number;
    label: string;
  };
  earnings: {
    next_date: string | null;
    risk: string;
  };
  position: {
    recommended_shares: number;
    position_value: number;
    stop_loss: number;
    take_profit: number;
  };
  indicators: {
    rsi: number;
    macd: number;
    adx: number;
    bb_position: number;
  };
}

interface StockData {
  symbol: string;
  history: Array<{
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    sma_20: number | null;
    sma_50: number | null;
    rsi: number | null;
    macd: number | null;
  }>;
  current: {
    price: number;
    rsi: number;
    macd: number;
    sma_20: number;
    sma_50: number;
    volume: number;
    atr: number;
  };
}

export default function StockDetail({ symbol, onBack }: StockDetailProps) {
  const [stockData, setStockData] = useState<StockData | null>(null);
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('1y');
  const [activeTab, setActiveTab] = useState<'chart' | 'indicators' | 'analysis'>('chart');
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [dataRes, analysisRes] = await Promise.all([
          api.get(`/api/stock/${symbol}?period=${period}`),
          api.get(`/api/stock/${symbol}/analysis`)
        ]);
        setStockData(dataRes.data);
        setAnalysis(analysisRes.data);
      } catch (error) {
        console.error('Error fetching stock data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [symbol, period]);

  const executeTrade = async (action: 'buy' | 'sell') => {
    if (!analysis) return;
    
    setExecuting(true);
    try {
      const response = await api.post(`/api/trade`, {
        symbol,
        action,
        quantity: analysis.position.recommended_shares,
        order_type: 'market'
      });
      
      if (response.data.success) {
        alert(`${action.toUpperCase()} order submitted for ${analysis.position.recommended_shares} shares of ${symbol}`);
      }
    } catch (error) {
      console.error('Trade error:', error);
      alert('Trade failed. Check console for details.');
    } finally {
      setExecuting(false);
    }
  };

  const getSignalColor = (type: string) => {
    if (type.includes('BUY')) return 'text-green-400';
    if (type.includes('SELL')) return 'text-red-400';
    return 'text-yellow-400';
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.2) return 'text-green-400';
    if (score < -0.2) return 'text-red-400';
    return 'text-yellow-400';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  if (!stockData || !analysis) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">Failed to load stock data</p>
        <button onClick={onBack} className="btn btn-ghost mt-4">← Go Back</button>
      </div>
    );
  }

  const priceChange = stockData.history.length > 1 
    ? ((stockData.current.price - stockData.history[stockData.history.length - 2].close) / stockData.history[stockData.history.length - 2].close) * 100
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold text-white">{symbol}</h1>
              <span className={`signal-badge ${
                analysis.signal.type.includes('BUY') ? 'signal-buy' :
                analysis.signal.type.includes('SELL') ? 'signal-sell' : 'signal-hold'
              }`}>
                {analysis.signal.type.replace('_', ' ')}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-1">
              <span className="text-2xl font-semibold text-white">
                ${stockData.current.price.toFixed(2)}
              </span>
              <span className={`text-lg ${priceChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
              </span>
            </div>
          </div>
        </div>

        {/* Trade Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => executeTrade('buy')}
            disabled={executing}
            className="btn btn-success flex items-center gap-2"
          >
            {executing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TrendingUp className="w-4 h-4" />}
            Buy {analysis.position.recommended_shares} Shares
          </button>
          <button
            onClick={() => executeTrade('sell')}
            disabled={executing}
            className="btn btn-danger flex items-center gap-2"
          >
            {executing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TrendingDown className="w-4 h-4" />}
            Sell
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="card">
          <p className="text-xs text-gray-400">Signal Confidence</p>
          <p className={`text-xl font-bold ${getSignalColor(analysis.signal.type)}`}>
            {Math.round(analysis.signal.confidence * 100)}%
          </p>
        </div>
        <div className="card">
          <p className="text-xs text-gray-400">Sentiment</p>
          <p className={`text-xl font-bold ${getSentimentColor(analysis.sentiment.score)}`}>
            {analysis.sentiment.label}
          </p>
        </div>
        <div className="card">
          <p className="text-xs text-gray-400">RSI</p>
          <p className={`text-xl font-bold ${
            analysis.indicators.rsi < 30 ? 'text-green-400' :
            analysis.indicators.rsi > 70 ? 'text-red-400' : 'text-white'
          }`}>
            {analysis.indicators.rsi.toFixed(1)}
          </p>
        </div>
        <div className="card">
          <p className="text-xs text-gray-400">Stop Loss</p>
          <p className="text-xl font-bold text-red-400">${analysis.position.stop_loss.toFixed(2)}</p>
        </div>
        <div className="card">
          <p className="text-xs text-gray-400">Take Profit</p>
          <p className="text-xl font-bold text-green-400">${analysis.position.take_profit.toFixed(2)}</p>
        </div>
      </div>

      {/* Period Selector */}
      <div className="flex gap-2">
        {['1mo', '3mo', '6mo', '1y', '2y'].map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1 rounded text-sm ${
              period === p 
                ? 'bg-primary-600 text-white' 
                : 'bg-[#1a1a2e] text-gray-400 hover:text-white'
            }`}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Chart Tabs */}
      <div className="card">
        <div className="flex gap-4 border-b border-[#2a2a4a] mb-4">
          {[
            { id: 'chart', label: 'Price Chart' },
            { id: 'indicators', label: 'Indicators' },
            { id: 'analysis', label: 'AI Analysis' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'chart' && (
          <div className="space-y-4">
            <CandlestickChart data={stockData.history} height={400} />
            <VolumeChart data={stockData.history} height={100} />
          </div>
        )}

        {activeTab === 'indicators' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <IndicatorChart 
                data={stockData.history.map(d => ({ date: d.date, value: d.rsi }))} 
                label="RSI (14)"
                height={150}
                thresholds={[30, 70]}
              />
              <IndicatorChart 
                data={stockData.history.map(d => ({ date: d.date, value: d.macd }))} 
                label="MACD"
                height={150}
              />
            </div>
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="space-y-6">
            {/* Signal Reasons */}
            <div>
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary-400" />
                Signal Analysis
              </h3>
              <ul className="space-y-2">
                {analysis.signal.reasons.map((reason, i) => (
                  <li key={i} className="flex items-start gap-2 text-gray-300">
                    <span className="text-primary-400">•</span>
                    {reason}
                  </li>
                ))}
              </ul>
            </div>

            {/* Position Recommendation */}
            <div>
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <Target className="w-5 h-5 text-green-400" />
                Position Recommendation
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[#0f0f1a] rounded-lg p-3">
                  <p className="text-xs text-gray-400">Shares</p>
                  <p className="text-lg font-semibold text-white">{analysis.position.recommended_shares}</p>
                </div>
                <div className="bg-[#0f0f1a] rounded-lg p-3">
                  <p className="text-xs text-gray-400">Position Value</p>
                  <p className="text-lg font-semibold text-white">${analysis.position.position_value.toLocaleString()}</p>
                </div>
                <div className="bg-[#0f0f1a] rounded-lg p-3">
                  <p className="text-xs text-gray-400">Stop Loss</p>
                  <p className="text-lg font-semibold text-red-400">${analysis.position.stop_loss.toFixed(2)}</p>
                </div>
                <div className="bg-[#0f0f1a] rounded-lg p-3">
                  <p className="text-xs text-gray-400">Take Profit</p>
                  <p className="text-lg font-semibold text-green-400">${analysis.position.take_profit.toFixed(2)}</p>
                </div>
              </div>
            </div>

            {/* Risk Warning */}
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <ShieldAlert className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-yellow-400">Risk Notice</p>
                  <p className="text-sm text-gray-400 mt-1">
                    This is algorithmic trading advice. Always do your own research. 
                    Past performance doesn't guarantee future results.
                    {analysis.earnings.next_date && (
                      <span className="block mt-1">
                        ⚠️ Upcoming earnings on {analysis.earnings.next_date}
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
