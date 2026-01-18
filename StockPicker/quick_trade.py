#!/usr/bin/env python3
"""
Quick Trade CLI
Simple command-line interface for executing trades

Usage:
    python quick_trade.py buy AAPL 10          # Buy 10 shares of AAPL
    python quick_trade.py buy AAPL $1000       # Buy $1000 worth of AAPL
    python quick_trade.py sell AAPL            # Sell all AAPL shares
    python quick_trade.py sell AAPL 5          # Sell 5 shares of AAPL
    python quick_trade.py status               # Show account status
    python quick_trade.py positions            # Show open positions
    python quick_trade.py orders               # Show open orders
"""
import sys
import os
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="{message}")

from src.broker import AlpacaBroker


def print_help():
    print(__doc__)


def main():
    args = sys.argv[1:]
    
    if not args or args[0] in ['-h', '--help', 'help']:
        print_help()
        return
    
    # Check for API keys
    if not os.getenv("ALPACA_API_KEY"):
        print("\n⚠️  Alpaca API keys not configured!")
        print("\nTo trade, you need to:")
        print("1. Sign up at https://app.alpaca.markets/")
        print("2. Get your API keys (use paper trading keys to start)")
        print("3. Set environment variables:")
        print("   export ALPACA_API_KEY='your-key'")
        print("   export ALPACA_SECRET_KEY='your-secret'")
        print("\nOr create a .env file with these values.")
        return
    
    # Connect to broker (paper trading by default)
    broker = AlpacaBroker(paper=True)
    
    if not broker.connected:
        print("❌ Failed to connect to Alpaca")
        return
    
    command = args[0].lower()
    
    if command == "status":
        account = broker.get_account()
        if account:
            print("\n" + "="*50)
            print("  ACCOUNT STATUS")
            print("="*50)
            print(f"  Account: {account['account_number']}")
            print(f"  Status: {account['status']}")
            print(f"  Portfolio Value: ${account['portfolio_value']:,.2f}")
            print(f"  Cash: ${account['cash']:,.2f}")
            print(f"  Buying Power: ${account['buying_power']:,.2f}")
            print(f"  Day Trade Count: {account['daytrade_count']}")
            
            market = broker.get_market_hours()
            if market:
                status = "🟢 OPEN" if market['is_open'] else "🔴 CLOSED"
                print(f"\n  Market: {status}")
            print("="*50 + "\n")
    
    elif command == "positions":
        positions = broker.get_positions()
        print("\n" + "="*60)
        print("  OPEN POSITIONS")
        print("="*60)
        
        if positions:
            print(f"{'Symbol':<8} {'Qty':>6} {'Entry':>10} {'Current':>10} {'P&L':>12} {'%':>8}")
            print("-"*60)
            
            total_value = 0
            total_pnl = 0
            
            for pos in positions:
                pnl = pos['unrealized_pl']
                pnl_pct = pos['unrealized_plpc'] * 100
                emoji = "🟢" if pnl >= 0 else "🔴"
                
                print(f"{pos['symbol']:<8} {pos['qty']:>6} "
                      f"${pos['avg_entry_price']:>9.2f} "
                      f"${pos['current_price']:>9.2f} "
                      f"{emoji} ${pnl:>9.2f} {pnl_pct:>7.1f}%")
                
                total_value += pos['market_value']
                total_pnl += pnl
            
            print("-"*60)
            emoji = "🟢" if total_pnl >= 0 else "🔴"
            print(f"{'TOTAL':<8} {'':<6} {'':<10} "
                  f"${total_value:>9.2f} {emoji} ${total_pnl:>9.2f}")
        else:
            print("  No open positions")
        
        print("="*60 + "\n")
    
    elif command == "orders":
        orders = broker.get_orders("open")
        print("\n" + "="*70)
        print("  OPEN ORDERS")
        print("="*70)
        
        if orders:
            for order in orders:
                print(f"  {order['side'].upper():4} {order['qty']} {order['symbol']} "
                      f"@ {order['type']} | Status: {order['status']}")
                print(f"       Order ID: {order['order_id'][:8]}...")
        else:
            print("  No open orders")
        
        print("="*70 + "\n")
    
    elif command == "buy":
        if len(args) < 2:
            print("Usage: buy SYMBOL [quantity or $amount]")
            return
        
        symbol = args[1].upper()
        
        if len(args) >= 3:
            qty_str = args[2]
            if qty_str.startswith('$'):
                # Dollar amount
                amount = float(qty_str[1:])
                print(f"\n📈 Buying ${amount:.2f} worth of {symbol}...")
                order = broker.buy(symbol, notional=amount)
            else:
                # Share quantity
                qty = int(qty_str)
                print(f"\n📈 Buying {qty} shares of {symbol}...")
                order = broker.buy(symbol, qty=qty)
        else:
            # Default: $1000
            print(f"\n📈 Buying $1000 worth of {symbol}...")
            order = broker.buy(symbol, notional=1000)
        
        if order:
            print(f"✅ Order placed: {order.order_id}")
            print(f"   Status: {order.status.value}")
    
    elif command == "sell":
        if len(args) < 2:
            print("Usage: sell SYMBOL [quantity]")
            return
        
        symbol = args[1].upper()
        
        if len(args) >= 3:
            qty = int(args[2])
            print(f"\n📉 Selling {qty} shares of {symbol}...")
        else:
            print(f"\n📉 Selling all shares of {symbol}...")
            qty = None
        
        order = broker.sell(symbol, qty=qty)
        
        if order:
            print(f"✅ Order placed: {order.order_id}")
            print(f"   Status: {order.status.value}")
    
    elif command == "cancel":
        if len(args) >= 2:
            order_id = args[1]
            broker.cancel_order(order_id)
        else:
            print("Cancelling all orders...")
            broker.cancel_all_orders()
    
    elif command == "close":
        if len(args) >= 2:
            symbol = args[1].upper()
            broker.close_position(symbol)
        else:
            confirm = input("Close ALL positions? (yes/no): ")
            if confirm.lower() == 'yes':
                broker.close_all_positions()
    
    else:
        print(f"Unknown command: {command}")
        print_help()


if __name__ == "__main__":
    main()
