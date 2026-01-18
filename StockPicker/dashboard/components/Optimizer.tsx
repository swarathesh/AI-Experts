'use client';

import { useState, useEffect } from 'react';
import { Zap, PieChart, Loader2, RefreshCw, Target, TrendingUp, BarChart3 } from 'lucide-react';
import api from '@/lib/api';
import AllocationChart from './charts/AllocationChart';

const API_BASE = 'http://localhost:8000';

interface OptimizationResult {
  method: string;
  expected_return: number;
  volatility: number;
  sharpe_ratio: number;
  weights: Record<string, number>;
}

export default function Optimizer() {
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState<'sharpe' | 'minvol' | 'riskparity'>('sharpe');

  const runOptimization = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/api/optimize`);
      setResult(response.data);
    } catch (error) {
      console.error('Optimization error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runOptimization();
  }, []);

  const methods = [
    { id: 'sharpe', label: 'Max Sharpe Ratio', description: 'Maximize risk-adjusted returns' },
    { id: 'minvol', label: 'Minimum Volatility', description: 'Minimize portfolio risk' },
    { id: 'riskparity', label: 'Risk Parity', description: 'Equal risk contribution' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Portfolio Optimizer</h1>
          <p className="text-gray-400">AI-powered portfolio optimization using modern portfolio theory</p>
        </div>
        <button
          onClick={runOptimization}
          disabled={loading}
          className="btn btn-primary flex items-center gap-2"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Zap className="w-4 h-4" />
          )}
          {loading ? 'Optimizing...' : 'Run Optimization'}
        </button>
      </div>

      {/* Method Selection */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {methods.map((method) => (
          <div
            key={method.id}
            onClick={() => setSelectedMethod(method.id as typeof selectedMethod)}
            className={`card cursor-pointer transition-all ${
              selectedMethod === method.id
                ? 'border-primary-500 bg-primary-500/10'
                : 'hover:border-[#3a3a5a]'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                selectedMethod === method.id
                  ? 'bg-primary-500/20 text-primary-400'
                  : 'bg-gray-700/50 text-gray-400'
              }`}>
                {method.id === 'sharpe' && <TrendingUp className="w-5 h-5" />}
                {method.id === 'minvol' && <Target className="w-5 h-5" />}
                {method.id === 'riskparity' && <PieChart className="w-5 h-5" />}
              </div>
              <div>
                <h3 className="font-semibold text-white">{method.label}</h3>
                <p className="text-sm text-gray-400">{method.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Results */}
      {loading ? (
        <div className="card flex items-center justify-center py-16">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-400">Running optimization algorithm...</p>
          </div>
        </div>
      ) : result ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Metrics */}
          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">Optimization Results</h2>
            
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-[#0f0f1a] rounded-lg p-4 text-center">
                <p className="text-sm text-gray-400">Expected Return</p>
                <p className="text-2xl font-bold text-green-400">{result.expected_return}%</p>
                <p className="text-xs text-gray-500">Annual</p>
              </div>
              <div className="bg-[#0f0f1a] rounded-lg p-4 text-center">
                <p className="text-sm text-gray-400">Volatility</p>
                <p className="text-2xl font-bold text-yellow-400">{result.volatility}%</p>
                <p className="text-xs text-gray-500">Annual</p>
              </div>
              <div className="bg-[#0f0f1a] rounded-lg p-4 text-center">
                <p className="text-sm text-gray-400">Sharpe Ratio</p>
                <p className="text-2xl font-bold text-primary-400">{result.sharpe_ratio}</p>
                <p className="text-xs text-gray-500">Risk-Adj</p>
              </div>
            </div>

            {/* Weights Table */}
            <h3 className="text-sm font-medium text-gray-400 mb-2">Optimal Weights</h3>
            <div className="space-y-2">
              {Object.entries(result.weights)
                .sort(([, a], [, b]) => b - a)
                .map(([symbol, weight]) => (
                  <div key={symbol} className="flex items-center gap-3">
                    <div className="w-12 text-sm font-medium text-white">{symbol}</div>
                    <div className="flex-1 h-6 bg-[#0f0f1a] rounded overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-primary-600 to-primary-400 transition-all duration-500"
                        style={{ width: `${weight}%` }}
                      />
                    </div>
                    <div className="w-16 text-right text-sm text-white">{weight}%</div>
                  </div>
                ))}
            </div>
          </div>

          {/* Allocation Chart */}
          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">Portfolio Allocation</h2>
            <AllocationChart weights={result.weights} />
          </div>
        </div>
      ) : (
        <div className="card text-center py-12">
          <p className="text-gray-400">Run optimization to see results</p>
        </div>
      )}

      {/* Info */}
      <div className="card bg-[#0f0f1a]">
        <h3 className="text-sm font-semibold text-white mb-2">About Portfolio Optimization</h3>
        <p className="text-sm text-gray-400">
          This optimizer uses Modern Portfolio Theory (MPT) to find the optimal asset allocation.
          The algorithm considers historical returns, volatility, and correlations to construct
          an efficient portfolio that either maximizes returns for a given risk level or minimizes
          risk for a target return.
        </p>
        <div className="mt-4 grid grid-cols-3 gap-4 text-center text-xs text-gray-500">
          <div>📊 Mean-Variance Optimization</div>
          <div>🎯 Efficient Frontier Analysis</div>
          <div>⚖️ Correlation Matrix</div>
        </div>
      </div>
    </div>
  );
}
