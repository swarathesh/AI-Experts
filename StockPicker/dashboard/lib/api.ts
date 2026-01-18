import axios from 'axios';

const RAW_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const API_BASE = RAW_BASE.replace(/\/+$/, '');

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health check
export const checkHealth = () => api.get('/api/health');

// Stocks
export const getStocks = () => api.get('/api/stocks');
export const getStockDetail = (symbol: string, period: string = '1y') => 
  api.get(`/api/stock/${symbol}?period=${period}`);
export const getStockAnalysis = (symbol: string) => 
  api.get(`/api/stock/${symbol}/analysis`);

// Scanning
export const runMarketScan = (symbols?: string[]) => 
  api.post('/api/scan', { symbols });
export const getHotStocks = () => api.get('/api/hot-stocks');

// Trading
export interface TradeRequest {
  symbol: string;
  action: 'buy' | 'sell';
  quantity: number;
  order_type: 'market' | 'limit';
  limit_price?: number;
}

export const executeTrade = (trade: TradeRequest) => 
  api.post('/api/trade', trade);
export const executePipeline = () => api.post('/api/execute-pipeline');

// Portfolio
export const getPortfolio = () => api.get('/api/portfolio');
export const getOrders = (status: string = 'all') => 
  api.get(`/api/orders?status=${status}`);
export const cancelOrder = (orderId: string) => 
  api.delete(`/api/orders/${orderId}`);

// Optimization
export const optimizePortfolio = () => api.get('/api/optimize');

export default api;
