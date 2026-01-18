"""
Alert and Notification System
Sends alerts via Email, Slack, Discord, and Desktop notifications
"""
import os
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import requests
import threading
import queue


class AlertPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AlertType(Enum):
    PRICE_ALERT = "price_alert"
    SIGNAL_ALERT = "signal_alert"
    TRADE_EXECUTED = "trade_executed"
    STOP_LOSS_HIT = "stop_loss_hit"
    TAKE_PROFIT_HIT = "take_profit_hit"
    EARNINGS_UPCOMING = "earnings_upcoming"
    SENTIMENT_CHANGE = "sentiment_change"
    SYSTEM_ERROR = "system_error"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"


@dataclass
class Alert:
    """Represents an alert/notification"""
    type: AlertType
    priority: AlertPriority
    title: str
    message: str
    symbol: Optional[str] = None
    price: Optional[float] = None
    timestamp: datetime = None
    data: Optional[Dict] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "priority": self.priority.name,
            "title": self.title,
            "message": self.message,
            "symbol": self.symbol,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }
    
    def format_slack(self) -> Dict:
        """Format alert for Slack"""
        emoji_map = {
            AlertPriority.LOW: "ℹ️",
            AlertPriority.MEDIUM: "⚠️",
            AlertPriority.HIGH: "🚨",
            AlertPriority.CRITICAL: "🔴"
        }
        
        type_emoji = {
            AlertType.PRICE_ALERT: "💰",
            AlertType.SIGNAL_ALERT: "📊",
            AlertType.TRADE_EXECUTED: "✅",
            AlertType.STOP_LOSS_HIT: "🛑",
            AlertType.TAKE_PROFIT_HIT: "🎯",
            AlertType.EARNINGS_UPCOMING: "📅",
            AlertType.SENTIMENT_CHANGE: "📰",
            AlertType.SYSTEM_ERROR: "❌"
        }
        
        emoji = emoji_map.get(self.priority, "")
        type_icon = type_emoji.get(self.type, "📢")
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {type_icon} {self.title}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": self.message
                }
            }
        ]
        
        if self.symbol and self.price:
            blocks.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Symbol:* {self.symbol}"},
                    {"type": "mrkdwn", "text": f"*Price:* ${self.price:.2f}"}
                ]
            })
        
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"⏰ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"}
            ]
        })
        
        return {"blocks": blocks}
    
    def format_discord(self) -> Dict:
        """Format alert for Discord"""
        color_map = {
            AlertPriority.LOW: 0x3498db,     # Blue
            AlertPriority.MEDIUM: 0xf39c12,  # Orange
            AlertPriority.HIGH: 0xe74c3c,    # Red
            AlertPriority.CRITICAL: 0x9b59b6  # Purple
        }
        
        embed = {
            "title": self.title,
            "description": self.message,
            "color": color_map.get(self.priority, 0x3498db),
            "timestamp": self.timestamp.isoformat(),
            "footer": {"text": "StockPicker AI"}
        }
        
        if self.symbol:
            embed["fields"] = [
                {"name": "Symbol", "value": self.symbol, "inline": True}
            ]
            if self.price:
                embed["fields"].append(
                    {"name": "Price", "value": f"${self.price:.2f}", "inline": True}
                )
        
        return {"embeds": [embed]}


class EmailNotifier:
    """Send email notifications via SMTP"""
    
    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = 587,
        sender_email: str = None,
        sender_password: str = None,
        recipient_emails: List[str] = None
    ):
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = smtp_port
        self.sender_email = sender_email or os.getenv("SMTP_EMAIL")
        self.sender_password = sender_password or os.getenv("SMTP_PASSWORD")
        self.recipient_emails = recipient_emails or []
        
        if os.getenv("ALERT_EMAIL"):
            self.recipient_emails.append(os.getenv("ALERT_EMAIL"))
    
    def send(self, alert: Alert) -> bool:
        """Send email notification"""
        if not self.sender_email or not self.sender_password:
            logger.warning("Email credentials not configured")
            return False
        
        if not self.recipient_emails:
            logger.warning("No recipient emails configured")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[StockPicker] {alert.priority.name}: {alert.title}"
            msg["From"] = self.sender_email
            msg["To"] = ", ".join(self.recipient_emails)
            
            # Plain text version
            text = f"""
StockPicker Alert
-----------------
Priority: {alert.priority.name}
Type: {alert.type.value}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

{alert.title}

{alert.message}

Symbol: {alert.symbol or 'N/A'}
Price: ${alert.price:.2f if alert.price else 'N/A'}
            """
            
            # HTML version
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background: #f5f5f5; padding: 20px;">
                    <h2 style="color: #333;">🔔 StockPicker Alert</h2>
                    <div style="background: white; padding: 20px; border-radius: 8px;">
                        <p><strong>Priority:</strong> {alert.priority.name}</p>
                        <h3>{alert.title}</h3>
                        <p>{alert.message}</p>
                        {f'<p><strong>Symbol:</strong> {alert.symbol} @ ${alert.price:.2f}</p>' if alert.symbol else ''}
                        <hr>
                        <p style="color: #888; font-size: 12px;">
                            {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))
            
            # Send
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                server.sendmail(
                    self.sender_email,
                    self.recipient_emails,
                    msg.as_string()
                )
            
            logger.info(f"Email sent: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Email error: {e}")
            return False


class SlackNotifier:
    """Send notifications to Slack via webhook"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
    
    def send(self, alert: Alert) -> bool:
        """Send Slack notification"""
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False
        
        try:
            payload = alert.format_slack()
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Slack notification sent: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Slack error: {e}")
            return False


class DiscordNotifier:
    """Send notifications to Discord via webhook"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
    
    def send(self, alert: Alert) -> bool:
        """Send Discord notification"""
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
            return False
        
        try:
            payload = alert.format_discord()
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Discord notification sent: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Discord error: {e}")
            return False


class DesktopNotifier:
    """Show desktop notifications"""
    
    def send(self, alert: Alert) -> bool:
        """Show desktop notification"""
        try:
            # Try different notification methods
            
            # Method 1: plyer (cross-platform)
            try:
                from plyer import notification
                notification.notify(
                    title=f"StockPicker: {alert.title}",
                    message=alert.message,
                    app_name="StockPicker",
                    timeout=10
                )
                return True
            except ImportError:
                pass
            
            # Method 2: notify-send (Linux)
            import subprocess
            try:
                subprocess.run([
                    'notify-send',
                    f"StockPicker: {alert.title}",
                    alert.message
                ], check=True)
                return True
            except:
                pass
            
            # Method 3: osascript (macOS)
            try:
                subprocess.run([
                    'osascript', '-e',
                    f'display notification "{alert.message}" with title "StockPicker: {alert.title}"'
                ], check=True)
                return True
            except:
                pass
            
            logger.warning("Desktop notifications not available")
            return False
            
        except Exception as e:
            logger.error(f"Desktop notification error: {e}")
            return False


class NotificationManager:
    """
    Central notification manager
    Routes alerts to configured channels
    """
    
    def __init__(self):
        self.email = EmailNotifier()
        self.slack = SlackNotifier()
        self.discord = DiscordNotifier()
        self.desktop = DesktopNotifier()
        
        # Alert queue for async processing
        self.alert_queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Alert history
        self.alert_history: List[Alert] = []
        self.max_history = 1000
        
        # Callbacks for custom handlers
        self.custom_handlers: List[Callable[[Alert], None]] = []
        
        # Channel preferences by priority
        self.channel_config = {
            AlertPriority.CRITICAL: ['email', 'slack', 'discord', 'desktop'],
            AlertPriority.HIGH: ['slack', 'discord', 'desktop'],
            AlertPriority.MEDIUM: ['slack', 'desktop'],
            AlertPriority.LOW: ['desktop']
        }
    
    def configure_channels(self, priority: AlertPriority, channels: List[str]):
        """Configure which channels to use for a priority level"""
        self.channel_config[priority] = channels
    
    def add_handler(self, handler: Callable[[Alert], None]):
        """Add a custom alert handler"""
        self.custom_handlers.append(handler)
    
    def send_alert(
        self,
        alert_type: AlertType,
        title: str,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        symbol: str = None,
        price: float = None,
        data: Dict = None,
        channels: List[str] = None
    ) -> Alert:
        """
        Send an alert through configured channels
        
        Args:
            alert_type: Type of alert
            title: Alert title
            message: Alert message
            priority: Priority level
            symbol: Related stock symbol
            price: Related price
            data: Additional data
            channels: Override channels (optional)
        
        Returns:
            The created Alert object
        """
        alert = Alert(
            type=alert_type,
            priority=priority,
            title=title,
            message=message,
            symbol=symbol,
            price=price,
            data=data
        )
        
        # Add to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        # Determine channels
        if channels is None:
            channels = self.channel_config.get(priority, ['desktop'])
        
        # Send to each channel
        for channel in channels:
            try:
                if channel == 'email':
                    self.email.send(alert)
                elif channel == 'slack':
                    self.slack.send(alert)
                elif channel == 'discord':
                    self.discord.send(alert)
                elif channel == 'desktop':
                    self.desktop.send(alert)
            except Exception as e:
                logger.error(f"Error sending to {channel}: {e}")
        
        # Call custom handlers
        for handler in self.custom_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Custom handler error: {e}")
        
        # Log alert
        logger.info(f"Alert [{priority.name}]: {title}")
        
        return alert
    
    # Convenience methods for common alerts
    
    def price_alert(self, symbol: str, price: float, condition: str, priority: AlertPriority = AlertPriority.HIGH):
        """Send a price alert"""
        return self.send_alert(
            AlertType.PRICE_ALERT,
            f"{symbol} Price Alert",
            f"{symbol} is now ${price:.2f} ({condition})",
            priority=priority,
            symbol=symbol,
            price=price
        )
    
    def trade_alert(self, action: str, symbol: str, qty: int, price: float):
        """Send a trade execution alert"""
        return self.send_alert(
            AlertType.TRADE_EXECUTED,
            f"Trade Executed: {action} {symbol}",
            f"{action} {qty} shares of {symbol} @ ${price:.2f}",
            priority=AlertPriority.HIGH,
            symbol=symbol,
            price=price,
            data={"action": action, "qty": qty}
        )
    
    def signal_alert(self, symbol: str, signal: str, confidence: float, price: float):
        """Send a trading signal alert"""
        return self.send_alert(
            AlertType.SIGNAL_ALERT,
            f"{signal} Signal: {symbol}",
            f"{symbol} has a {signal} signal with {confidence:.0%} confidence @ ${price:.2f}",
            priority=AlertPriority.MEDIUM if confidence < 0.8 else AlertPriority.HIGH,
            symbol=symbol,
            price=price,
            data={"signal": signal, "confidence": confidence}
        )
    
    def stop_loss_alert(self, symbol: str, entry_price: float, exit_price: float, loss_pct: float):
        """Send stop loss alert"""
        return self.send_alert(
            AlertType.STOP_LOSS_HIT,
            f"⛔ Stop Loss Hit: {symbol}",
            f"{symbol} stop loss triggered. Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f} ({loss_pct:.1%} loss)",
            priority=AlertPriority.CRITICAL,
            symbol=symbol,
            price=exit_price,
            data={"entry_price": entry_price, "loss_pct": loss_pct}
        )
    
    def take_profit_alert(self, symbol: str, entry_price: float, exit_price: float, profit_pct: float):
        """Send take profit alert"""
        return self.send_alert(
            AlertType.TAKE_PROFIT_HIT,
            f"🎯 Take Profit Hit: {symbol}",
            f"{symbol} take profit triggered. Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f} ({profit_pct:.1%} profit)",
            priority=AlertPriority.HIGH,
            symbol=symbol,
            price=exit_price,
            data={"entry_price": entry_price, "profit_pct": profit_pct}
        )
    
    def error_alert(self, error: str, details: str = None):
        """Send system error alert"""
        return self.send_alert(
            AlertType.SYSTEM_ERROR,
            f"System Error",
            f"Error: {error}\n{details or ''}",
            priority=AlertPriority.CRITICAL
        )
    
    def get_recent_alerts(self, limit: int = 50) -> List[Alert]:
        """Get recent alerts"""
        return self.alert_history[-limit:]


# Create global instance
notification_manager = NotificationManager()


# Convenience functions
def send_alert(
    title: str,
    message: str,
    priority: AlertPriority = AlertPriority.MEDIUM,
    **kwargs
) -> Alert:
    """Quick function to send an alert"""
    return notification_manager.send_alert(
        AlertType.SIGNAL_ALERT,
        title,
        message,
        priority,
        **kwargs
    )
