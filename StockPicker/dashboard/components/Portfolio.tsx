'use client';

import { useState, useEffect } from 'react';
import { Wallet, TrendingUp, TrendingDown, DollarSign, RefreshCw, Loader2 } from 'lucide-react';
import api from '@/lib/api';

interface Position {
  symbol: string;
  qty: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_plpc: number;
}

interface Account {
  buying_power: number;
  portfolio_value: number;
  cash: number;
}

interface Order {
  id: string;
  symbol: string;
  side: string;
  qty: number;
  type: string;
  status: string;
  created_at: string;
}

export default function Portfolio() {
  const [account, setAccount] = useState<Account | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'positions' | 'orders'>('positions');

  const fetchPortfolio = async () => {
    setLoading(true);
    try {
      const [portfolioRes, ordersRes] = await Promise.all([
        api.get(`/api/portfolio`),
        api.get(`/api/orders`)
      ]);
      
      setAccount(portfolioRes.data.account);
      setPositions(portfolioRes.data.positions || []);
      setOrders(ordersRes.data.orders || []);
    } catch (error) {
      console.error('Error fetching portfolio:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const cancelOrder = async (orderId: string) => {
    try {
      await api.delete(`/api/orders/${orderId}`);
      fetchPortfolio();
    } catch (error) {
      console.error('Error cancelling order:', error);
    }
  };

  const totalPL = positions.reduce((sum, p) => sum + p.unrealized_pl, 0);
  const totalValue = positions.reduce((sum, p) => sum + p.market_value, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Portfolio</h1>
          <p className="text-gray-400">Your positions and account overview</p>
        </div>
        <button
          onClick={fetchPortfolio}
          disabled={loading}
          className="btn btn-ghost flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Account Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Portfolio Value</p>
              <p className="text-2xl font-bold text-white">
                ${account?.portfolio_value?.toLocaleString() || '0'}
              </p>
            </div>
            <Wallet className="w-8 h-8 text-primary-400/30" />
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Cash</p>
              <p className="text-2xl font-bold text-white">
                ${account?.cash?.toLocaleString() || '0'}
              </p>
            </div>
            <DollarSign className="w-8 h-8 text-green-400/30" />
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Buying Power</p>
              <p className="text-2xl font-bold text-white">
                ${account?.buying_power?.toLocaleString() || '0'}
              </p>
            </div>
            <TrendingUp className="w-8 h-8 text-yellow-400/30" />
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Unrealized P&L</p>
              <p className={`text-2xl font-bold ${totalPL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {totalPL >= 0 ? '+' : ''}${totalPL.toFixed(2)}
              </p>
            </div>
            {totalPL >= 0 
              ? <TrendingUp className="w-8 h-8 text-green-400/30" />
              : <TrendingDown className="w-8 h-8 text-red-400/30" />
            }
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="card">
        <div className="flex gap-4 border-b border-[#2a2a4a] mb-4">
          <button
            onClick={() => setActiveTab('positions')}
            className={`tab ${activeTab === 'positions' ? 'active' : ''}`}
          >
            Positions ({positions.length})
          </button>
          <button
            onClick={() => setActiveTab('orders')}
            className={`tab ${activeTab === 'orders' ? 'active' : ''}`}
          >
            Orders ({orders.length})
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
          </div>
        ) : activeTab === 'positions' ? (
          <div className="overflow-x-auto">
            {positions.length === 0 ? (
              <div className="text-center text-gray-400 py-12">
                No positions yet. Start trading to see your holdings here.
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="text-left text-gray-400 text-sm border-b border-[#2a2a4a]">
                    <th className="px-4 py-3">Symbol</th>
                    <th className="px-4 py-3">Qty</th>
                    <th className="px-4 py-3">Avg Price</th>
                    <th className="px-4 py-3">Current</th>
                    <th className="px-4 py-3">Market Value</th>
                    <th className="px-4 py-3">P&L</th>
                    <th className="px-4 py-3">P&L %</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos) => (
                    <tr key={pos.symbol} className="border-b border-[#2a2a4a]/50 hover:bg-white/5">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded bg-primary-500/20 flex items-center justify-center">
                            <span className="text-xs font-bold text-primary-400">
                              {pos.symbol.slice(0, 2)}
                            </span>
                          </div>
                          <span className="font-semibold text-white">{pos.symbol}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-white">{pos.qty}</td>
                      <td className="px-4 py-3 text-gray-400">${pos.avg_price.toFixed(2)}</td>
                      <td className="px-4 py-3 text-white">${pos.current_price.toFixed(2)}</td>
                      <td className="px-4 py-3 text-white">${pos.market_value.toFixed(2)}</td>
                      <td className={`px-4 py-3 ${pos.unrealized_pl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {pos.unrealized_pl >= 0 ? '+' : ''}${pos.unrealized_pl.toFixed(2)}
                      </td>
                      <td className={`px-4 py-3 ${pos.unrealized_plpc >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {pos.unrealized_plpc >= 0 ? '+' : ''}{pos.unrealized_plpc.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            {orders.length === 0 ? (
              <div className="text-center text-gray-400 py-12">
                No recent orders.
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="text-left text-gray-400 text-sm border-b border-[#2a2a4a]">
                    <th className="px-4 py-3">Symbol</th>
                    <th className="px-4 py-3">Side</th>
                    <th className="px-4 py-3">Qty</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.id} className="border-b border-[#2a2a4a]/50 hover:bg-white/5">
                      <td className="px-4 py-3 font-semibold text-white">{order.symbol}</td>
                      <td className={`px-4 py-3 font-medium ${
                        order.side === 'buy' ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {order.side.toUpperCase()}
                      </td>
                      <td className="px-4 py-3 text-white">{order.qty}</td>
                      <td className="px-4 py-3 text-gray-400">{order.type}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs ${
                          order.status === 'filled' ? 'bg-green-500/20 text-green-400' :
                          order.status === 'pending' || order.status === 'new' ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-gray-500/20 text-gray-400'
                        }`}>
                          {order.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-sm">
                        {new Date(order.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        {(order.status === 'pending' || order.status === 'new') && (
                          <button
                            onClick={() => cancelOrder(order.id)}
                            className="text-red-400 hover:text-red-300 text-sm"
                          >
                            Cancel
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
