'use client';

import { useState } from 'react';
import { Save, AlertTriangle, Bell, Shield, Database, Cpu } from 'lucide-react';

export default function Settings() {
  const [settings, setSettings] = useState({
    // Trading Settings
    paperTrading: true,
    maxPositionSize: 10000,
    maxPortfolioRisk: 5,
    defaultOrderType: 'market',
    
    // Analysis Settings
    rsiOversold: 30,
    rsiOverbought: 70,
    confidenceThreshold: 50,
    
    // Notifications
    emailAlerts: false,
    slackAlerts: false,
    discordAlerts: false,
    
    // API Keys (masked)
    alpacaKey: '****',
    newsApiKey: '****',
  });

  const handleSave = () => {
    // Save settings to localStorage or API
    localStorage.setItem('stockpicker-settings', JSON.stringify(settings));
    alert('Settings saved!');
  };

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="text-gray-400">Configure your trading parameters and preferences</p>
        </div>
        <button onClick={handleSave} className="btn btn-primary flex items-center gap-2">
          <Save className="w-4 h-4" />
          Save Changes
        </button>
      </div>

      {/* Trading Settings */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="w-5 h-5 text-primary-400" />
          <h2 className="text-lg font-semibold text-white">Trading Settings</h2>
        </div>

        <div className="space-y-4">
          {/* Paper Trading Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white font-medium">Paper Trading</p>
              <p className="text-sm text-gray-400">Use simulated trades (recommended)</p>
            </div>
            <button
              onClick={() => setSettings({ ...settings, paperTrading: !settings.paperTrading })}
              className={`w-12 h-6 rounded-full transition-colors ${
                settings.paperTrading ? 'bg-green-500' : 'bg-red-500'
              }`}
            >
              <div className={`w-5 h-5 bg-white rounded-full transition-transform ${
                settings.paperTrading ? 'translate-x-6' : 'translate-x-0.5'
              }`} />
            </button>
          </div>

          {!settings.paperTrading && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-sm text-red-400">
                Live trading is enabled. Real money will be used for trades.
                Make sure you understand the risks.
              </p>
            </div>
          )}

          {/* Max Position Size */}
          <div>
            <label className="block text-white font-medium mb-1">Max Position Size ($)</label>
            <input
              type="number"
              value={settings.maxPositionSize}
              onChange={(e) => setSettings({ ...settings, maxPositionSize: parseInt(e.target.value) })}
              className="w-full bg-[#0f0f1a] border border-[#2a2a4a] rounded-lg px-4 py-2 text-white"
            />
            <p className="text-xs text-gray-500 mt-1">Maximum $ amount per trade</p>
          </div>

          {/* Max Portfolio Risk */}
          <div>
            <label className="block text-white font-medium mb-1">Max Portfolio Risk (%)</label>
            <input
              type="number"
              value={settings.maxPortfolioRisk}
              onChange={(e) => setSettings({ ...settings, maxPortfolioRisk: parseInt(e.target.value) })}
              min={1}
              max={20}
              className="w-full bg-[#0f0f1a] border border-[#2a2a4a] rounded-lg px-4 py-2 text-white"
            />
            <p className="text-xs text-gray-500 mt-1">Max % of portfolio at risk per trade</p>
          </div>

          {/* Default Order Type */}
          <div>
            <label className="block text-white font-medium mb-1">Default Order Type</label>
            <select
              value={settings.defaultOrderType}
              onChange={(e) => setSettings({ ...settings, defaultOrderType: e.target.value })}
              className="w-full bg-[#0f0f1a] border border-[#2a2a4a] rounded-lg px-4 py-2 text-white"
            >
              <option value="market">Market Order</option>
              <option value="limit">Limit Order</option>
            </select>
          </div>
        </div>
      </div>

      {/* Analysis Settings */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Cpu className="w-5 h-5 text-primary-400" />
          <h2 className="text-lg font-semibold text-white">Analysis Settings</h2>
        </div>

        <div className="space-y-4">
          {/* RSI Settings */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-white font-medium mb-1">RSI Oversold Level</label>
              <input
                type="number"
                value={settings.rsiOversold}
                onChange={(e) => setSettings({ ...settings, rsiOversold: parseInt(e.target.value) })}
                min={10}
                max={40}
                className="w-full bg-[#0f0f1a] border border-[#2a2a4a] rounded-lg px-4 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-white font-medium mb-1">RSI Overbought Level</label>
              <input
                type="number"
                value={settings.rsiOverbought}
                onChange={(e) => setSettings({ ...settings, rsiOverbought: parseInt(e.target.value) })}
                min={60}
                max={90}
                className="w-full bg-[#0f0f1a] border border-[#2a2a4a] rounded-lg px-4 py-2 text-white"
              />
            </div>
          </div>

          {/* Confidence Threshold */}
          <div>
            <label className="block text-white font-medium mb-1">
              Minimum Signal Confidence (%)
            </label>
            <input
              type="range"
              value={settings.confidenceThreshold}
              onChange={(e) => setSettings({ ...settings, confidenceThreshold: parseInt(e.target.value) })}
              min={0}
              max={100}
              className="w-full"
            />
            <div className="flex justify-between text-sm text-gray-400">
              <span>0%</span>
              <span className="text-primary-400 font-medium">{settings.confidenceThreshold}%</span>
              <span>100%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Notification Settings */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Bell className="w-5 h-5 text-primary-400" />
          <h2 className="text-lg font-semibold text-white">Notifications</h2>
        </div>

        <div className="space-y-4">
          {[
            { key: 'emailAlerts', label: 'Email Alerts', desc: 'Get trade alerts via email' },
            { key: 'slackAlerts', label: 'Slack Alerts', desc: 'Send alerts to Slack channel' },
            { key: 'discordAlerts', label: 'Discord Alerts', desc: 'Send alerts to Discord' },
          ].map((item) => (
            <div key={item.key} className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">{item.label}</p>
                <p className="text-sm text-gray-400">{item.desc}</p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, [item.key]: !settings[item.key as keyof typeof settings] })}
                className={`w-12 h-6 rounded-full transition-colors ${
                  settings[item.key as keyof typeof settings] ? 'bg-primary-500' : 'bg-gray-600'
                }`}
              >
                <div className={`w-5 h-5 bg-white rounded-full transition-transform ${
                  settings[item.key as keyof typeof settings] ? 'translate-x-6' : 'translate-x-0.5'
                }`} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* API Configuration */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Database className="w-5 h-5 text-primary-400" />
          <h2 className="text-lg font-semibold text-white">API Configuration</h2>
        </div>

        <p className="text-sm text-gray-400 mb-4">
          API keys are configured via environment variables in the .env file.
          Edit the file directly to update keys.
        </p>

        <div className="space-y-3">
          <div className="flex items-center justify-between bg-[#0f0f1a] rounded-lg px-4 py-3">
            <span className="text-gray-400">Alpaca API</span>
            <span className="text-green-400 text-sm">● Connected</span>
          </div>
          <div className="flex items-center justify-between bg-[#0f0f1a] rounded-lg px-4 py-3">
            <span className="text-gray-400">News API</span>
            <span className="text-green-400 text-sm">● Connected</span>
          </div>
          <div className="flex items-center justify-between bg-[#0f0f1a] rounded-lg px-4 py-3">
            <span className="text-gray-400">Alpha Vantage</span>
            <span className="text-green-400 text-sm">● Connected</span>
          </div>
        </div>
      </div>
    </div>
  );
}
