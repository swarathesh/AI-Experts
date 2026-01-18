import { type ClassValue, clsx } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
}

export function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export function formatNumber(value: number): string {
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
  return value.toString();
}

export function getSignalColor(signal: string): string {
  switch (signal) {
    case 'STRONG_BUY': return 'text-green-500';
    case 'BUY': return 'text-green-400';
    case 'HOLD': return 'text-yellow-400';
    case 'SELL': return 'text-red-400';
    case 'STRONG_SELL': return 'text-red-500';
    default: return 'text-gray-400';
  }
}

export function getSignalBgColor(signal: string): string {
  switch (signal) {
    case 'STRONG_BUY': return 'bg-green-500/20';
    case 'BUY': return 'bg-green-400/20';
    case 'HOLD': return 'bg-yellow-400/20';
    case 'SELL': return 'bg-red-400/20';
    case 'STRONG_SELL': return 'bg-red-500/20';
    default: return 'bg-gray-500/20';
  }
}
