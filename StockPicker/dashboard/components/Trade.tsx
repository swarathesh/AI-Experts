'use client';

import { useState } from 'react';
import { Play, Loader2, AlertTriangle, CheckCircle, Zap, Target, TrendingUp } from 'lucide-react';
import api from '@/lib/api';

interface TradeToExecute {
  symbol: string;
  action: string;
  quantity: number;
  price: number;
  signal: string;
  confidence: number;
}

interface PipelineResult {
  success: boolean;
  timestamp: string;
  scan_results: number;
  trades_to_execute: TradeToExecute[];
  message: string;
}

export default function Trade() {
  const [mode, setMode] = useState<'single' | 'pipeline'>('single');
  
  // Single trade state
  const [symbol, setSymbol] = useState('');
  const [action, setAction] = useState<'buy' | 'sell'>('buy');
  const [quantity, setQuantity] = useState(10);
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [limitPrice, setLimitPrice] = useState<number | ''>('');
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
  
  // Pipeline state
  const [pipelineResult, setPipelineResult] = useState<PipelineResult | null>(null);
  const [runningPipeline, setRunningPipeline] = useState(false);
  const [confirmedTrades, setConfirmedTrades] = useState<Set<string>>(new Set());

  const executeSingleTrade = async () => {
    if (!symbol) return;
    
    setExecuting(true);
    setResult(null);
    
    try {
      const response = await api.post(`/api/trade`, {
        symbol: symbol.toUpperCase(),
        action,
        quantity,
        order_type: orderType,
        limit_price: orderType === 'limit' ? limitPrice : null
      });
      
      setResult({
        success: true,
        message: `${action.toUpperCase()} order submitted for ${quantity} shares of ${symbol.toUpperCase()}`
      });
    } catch (error: any) {
      setResult({
        success: false,
        message: error.response?.data?.detail || 'Trade failed'
      });
    } finally {
      setExecuting(false);
    }
  };

  const runPipeline = async () => {
    setRunningPipeline(true);
    setPipelineResult(null);
    
    try {
      const response = await api.post(`/api/execute-pipeline`);
      setPipelineResult(response.data);
    } catch (error: any) {
      setPipelineResult({
        success: false,
        timestamp: new Date().toISOString(),
        scan_results: 0,
        trades_to_execute: [],
        message: error.response?.data?.detail || 'Pipeline failed'
      });
    } finally {
      setRunningPipeline(false);
    }
  };

  const executeConfirmedTrades = async () => {
    if (!pipelineResult) return;
    
    const tradesToExecute = pipelineResult.trades_to_execute.filter(
      t => confirmedTrades.has(t.symbol)
    );
    
    setExecuting(true);
    
    for (const trade of tradesToExecute) {
      try {
        await api.post(`/api/trade`, {
          symbol: trade.symbol,
          action: trade.action,
          quantity: trade.quantity,
          order_type: 'market'
        });
      } catch (error) {
        console.error(`Failed to execute trade for ${trade.symbol}:`, error);
      }
    }
    
    setExecuting(false);
    setResult({
      success: true,
      message: `Executed ${tradesToExecute.length} trades`
    });
    setConfirmedTrades(new Set());
  };

  const toggleTrade = (symbol: string) => {
    const newConfirmed = new Set(confirmedTrades);
    if (newConfirmed.has(symbol)) {
      newConfirmed.delete(symbol);
    } else {
      newConfirmed.add(symbol);
    }
    setConfirmedTrades(newConfirmed);
  };

  const selectAllTrades = () => {
    if (pipelineResult) {
      setConfirmedTrades(new Set(pipelineResult.trades_to_execute.map(t => t.symbol)));
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Trade Execution</h1>
          <p className="text-gray-400">Execute single trades or run the full AI pipeline</p>
        </div>
      </div>

      {/* Mode Tabs */}
      <div className="flex gap-4">
        <button
          onClick={() => setMode('single')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            mode === 'single'
              ? 'bg-primary-600 text-white'
              : 'bg-[#1a1a2e] text-gray-400 hover:text-white'
          }`}
        >
          <Target className="w-4 h-4" />
          Single Trade
        </button>
        <button
          onClick={() => setMode('pipeline')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            mode === 'pipeline'
              ? 'bg-primary-600 text-white'
              : 'bg-[#1a1a2e] text-gray-400 hover:text-white'
          }`}
        >
          <Zap className="w-4 h-4" />
          AI Pipeline
        </button>
      </div>

      {/* Single Trade Form */}
      {mode === 'single' && (
        <div className="card max-w-lg">
          <h2 className="text-lg font-semibold text-white mb-4">Execute Trade</h2>
          
          <div className="space-y-4">
            {/* Symbol */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">Symbol</label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="AAPL"
                className="w-full bg-[#0f0f1a] border border-[#2a2a4a] rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary-500"
              />
            </div>

            {/* Action */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">Action</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setAction('buy')}
                  className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                    action === 'buy'
                      ? 'bg-green-600 text-white'
                      : 'bg-[#0f0f1a] text-gray-400 hover:text-white border border-[#2a2a4a]'
                  }`}
                >
                  BUY
                </button>
                <button
                  onClick={() => setAction('sell')}
                  className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                    action === 'sell'
                      ? 'bg-red-600 text-white'
                      : 'bg-[#0f0f1a] text-gray-400 hover:text-white border border-[#2a2a4a]'
                  }`}
                >
                  SELL
                </button>
              </div>
            </div>

            {/* Quantity */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">Quantity</label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
                min={1}
                className="w-full bg-[#0f0f1a] border border-[#2a2a4a] rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary-500"
              />
            </div>

            {/* Order Type */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">Order Type</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setOrderType('market')}
                  className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                    orderType === 'market'
                      ? 'bg-primary-600 text-white'
                      : 'bg-[#0f0f1a] text-gray-400 hover:text-white border border-[#2a2a4a]'
                  }`}
                >
                  Market
                </button>
                <button
                  onClick={() => setOrderType('limit')}
                  className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                    orderType === 'limit'
                      ? 'bg-primary-600 text-white'
                      : 'bg-[#0f0f1a] text-gray-400 hover:text-white border border-[#2a2a4a]'
                  }`}
                >
                  Limit
                </button>
              </div>
            </div>

            {/* Limit Price */}
            {orderType === 'limit' && (
              <div>
                <label className="block text-sm text-gray-400 mb-1">Limit Price</label>
                <input
                  type="number"
                  value={limitPrice}
                  onChange={(e) => setLimitPrice(parseFloat(e.target.value) || '')}
                  step="0.01"
                  placeholder="0.00"
                  className="w-full bg-[#0f0f1a] border border-[#2a2a4a] rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary-500"
                />
              </div>
            )}

            {/* Execute Button */}
            <button
              onClick={executeSingleTrade}
              disabled={!symbol || executing}
              className={`w-full py-3 rounded-lg font-semibold flex items-center justify-center gap-2 ${
                action === 'buy' ? 'btn btn-success' : 'btn btn-danger'
              }`}
            >
              {executing ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Play className="w-5 h-5" />
              )}
              {executing ? 'Executing...' : `${action.toUpperCase()} ${quantity} ${symbol || 'shares'}`}
            </button>
          </div>

          {/* Result */}
          {result && (
            <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
              result.success 
                ? 'bg-green-500/10 border border-green-500/20' 
                : 'bg-red-500/10 border border-red-500/20'
            }`}>
              {result.success ? (
                <CheckCircle className="w-5 h-5 text-green-400" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-red-400" />
              )}
              <span className={result.success ? 'text-green-400' : 'text-red-400'}>
                {result.message}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Pipeline Mode */}
      {mode === 'pipeline' && (
        <div className="space-y-6">
          {/* Run Pipeline */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-white">AI Trading Pipeline</h2>
                <p className="text-sm text-gray-400">
                  Scans market, analyzes signals, and recommends trades
                </p>
              </div>
              <button
                onClick={runPipeline}
                disabled={runningPipeline}
                className="btn btn-primary flex items-center gap-2"
              >
                {runningPipeline ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Zap className="w-4 h-4" />
                )}
                {runningPipeline ? 'Running...' : 'Run Pipeline'}
              </button>
            </div>

            {/* Pipeline Steps */}
            <div className="grid grid-cols-4 gap-4 text-center">
              {[
                { step: 1, label: 'Market Scan', status: runningPipeline ? 'running' : pipelineResult ? 'done' : 'pending' },
                { step: 2, label: 'Analysis', status: runningPipeline ? 'pending' : pipelineResult ? 'done' : 'pending' },
                { step: 3, label: 'Signal Gen', status: runningPipeline ? 'pending' : pipelineResult ? 'done' : 'pending' },
                { step: 4, label: 'Execute', status: 'pending' }
              ].map((item) => (
                <div key={item.step} className="flex flex-col items-center gap-2">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    item.status === 'done' ? 'bg-green-500/20 text-green-400' :
                    item.status === 'running' ? 'bg-primary-500/20 text-primary-400 animate-pulse' :
                    'bg-gray-700/50 text-gray-500'
                  }`}>
                    {item.status === 'done' ? (
                      <CheckCircle className="w-5 h-5" />
                    ) : item.status === 'running' ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <span>{item.step}</span>
                    )}
                  </div>
                  <span className="text-xs text-gray-400">{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Pipeline Results */}
          {pipelineResult && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white">
                  Recommended Trades ({pipelineResult.trades_to_execute.length})
                </h2>
                <div className="flex gap-2">
                  <button
                    onClick={selectAllTrades}
                    className="btn btn-ghost text-sm"
                  >
                    Select All
                  </button>
                  <button
                    onClick={executeConfirmedTrades}
                    disabled={confirmedTrades.size === 0 || executing}
                    className="btn btn-success flex items-center gap-2"
                  >
                    {executing ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    Execute Selected ({confirmedTrades.size})
                  </button>
                </div>
              </div>

              {pipelineResult.trades_to_execute.length === 0 ? (
                <div className="text-center text-gray-400 py-8">
                  No actionable trades found. Market conditions may not meet criteria.
                </div>
              ) : (
                <div className="space-y-3">
                  {pipelineResult.trades_to_execute.map((trade) => (
                    <div
                      key={trade.symbol}
                      onClick={() => toggleTrade(trade.symbol)}
                      className={`flex items-center justify-between p-4 rounded-lg border cursor-pointer transition-all ${
                        confirmedTrades.has(trade.symbol)
                          ? 'bg-green-500/10 border-green-500/30'
                          : 'bg-[#0f0f1a] border-[#2a2a4a] hover:border-[#3a3a5a]'
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <input
                          type="checkbox"
                          checked={confirmedTrades.has(trade.symbol)}
                          onChange={() => {}}
                          className="w-5 h-5 rounded border-gray-500 text-green-500 focus:ring-green-500"
                        />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white">{trade.symbol}</span>
                            <span className={`px-2 py-0.5 rounded text-xs ${
                              trade.signal === 'STRONG_BUY' ? 'bg-green-500/20 text-green-400' :
                              'bg-green-400/20 text-green-300'
                            }`}>
                              {trade.signal}
                            </span>
                          </div>
                          <div className="text-sm text-gray-400">
                            {trade.quantity} shares @ ${trade.price.toFixed(2)}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-white font-medium">
                          ${(trade.quantity * trade.price).toLocaleString()}
                        </div>
                        <div className="text-sm text-gray-400">
                          Confidence: {Math.round(trade.confidence * 100)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Warning */}
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-yellow-400">Paper Trading Mode</p>
                <p className="text-sm text-gray-400 mt-1">
                  All trades are executed on a paper trading account. No real money is at risk.
                  Switch to live trading in settings (not recommended without thorough testing).
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
