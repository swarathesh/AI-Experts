"""
News & Social Media Sentiment Analysis
Fetches news and analyzes sentiment to generate trading signals
"""
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from loguru import logger

# Sentiment analysis
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available. Install with: pip install transformers torch")

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    logger.warning("VADER not available. Install with: pip install vaderSentiment")


class NewsSentimentAnalyzer:
    """
    Analyzes news and social media sentiment for stocks
    
    Uses multiple sources:
    - NewsAPI for news headlines
    - Reddit (via API) for social sentiment
    - FinBERT for financial-specific sentiment
    - VADER for general sentiment
    """
    
    def __init__(
        self,
        news_api_key: Optional[str] = None,
        use_finbert: bool = True
    ):
        """
        Initialize sentiment analyzer
        
        Args:
            news_api_key: NewsAPI key (or set NEWS_API_KEY env var)
            use_finbert: Whether to use FinBERT (slower but more accurate for finance)
        """
        self.news_api_key = news_api_key or os.getenv("NEWS_API_KEY")
        self.use_finbert = use_finbert and TRANSFORMERS_AVAILABLE
        
        # Initialize VADER (fast, general purpose)
        if VADER_AVAILABLE:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None
        
        # Initialize FinBERT (slower, finance-specific)
        self.finbert = None
        if self.use_finbert:
            try:
                self.finbert = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert",
                    tokenizer="ProsusAI/finbert"
                )
                logger.info("FinBERT model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load FinBERT: {e}")
                self.finbert = None
        
        # Cache for API responses
        self._cache: Dict[str, Tuple[datetime, List]] = {}
        self._cache_duration = timedelta(minutes=15)
    
    def get_news_sentiment(
        self,
        symbol: str,
        company_name: Optional[str] = None,
        days: int = 7
    ) -> Dict:
        """
        Get news sentiment for a stock
        
        Args:
            symbol: Stock ticker symbol
            company_name: Full company name for better search
            days: Number of days to look back
        
        Returns:
            Dictionary with sentiment scores and articles
        """
        # Check cache
        cache_key = f"news_{symbol}_{days}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key][1]
        
        articles = self._fetch_news(symbol, company_name, days)
        
        if not articles:
            return {
                "symbol": symbol,
                "overall_sentiment": 0.0,
                "sentiment_label": "neutral",
                "article_count": 0,
                "positive_ratio": 0.0,
                "articles": []
            }
        
        # Analyze sentiment for each article
        analyzed_articles = []
        sentiments = []
        
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            sentiment = self._analyze_text(text)
            
            analyzed_articles.append({
                "title": article.get('title'),
                "source": article.get('source', {}).get('name'),
                "published_at": article.get('publishedAt'),
                "url": article.get('url'),
                "sentiment_score": sentiment['compound'],
                "sentiment_label": sentiment['label']
            })
            sentiments.append(sentiment['compound'])
        
        # Calculate overall sentiment
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        positive_count = sum(1 for s in sentiments if s > 0.1)
        
        result = {
            "symbol": symbol,
            "overall_sentiment": avg_sentiment,
            "sentiment_label": self._score_to_label(avg_sentiment),
            "article_count": len(articles),
            "positive_ratio": positive_count / len(articles) if articles else 0,
            "negative_ratio": sum(1 for s in sentiments if s < -0.1) / len(articles) if articles else 0,
            "articles": analyzed_articles[:10]  # Return top 10
        }
        
        # Cache result
        self._cache[cache_key] = (datetime.now(), result)
        
        return result
    
    def _fetch_news(
        self,
        symbol: str,
        company_name: Optional[str] = None,
        days: int = 7
    ) -> List[Dict]:
        """Fetch news articles from NewsAPI"""
        if not self.news_api_key:
            logger.warning("NewsAPI key not configured")
            return self._fetch_fallback_news(symbol)
        
        try:
            # Build search query
            query = symbol
            if company_name:
                query = f"{symbol} OR {company_name}"
            
            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "from": from_date,
                "sortBy": "relevancy",
                "language": "en",
                "pageSize": 50,
                "apiKey": self.news_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('articles', [])
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return self._fetch_fallback_news(symbol)
    
    def _fetch_fallback_news(self, symbol: str) -> List[Dict]:
        """Fallback to free news sources when NewsAPI unavailable"""
        articles = []
        
        # Try Yahoo Finance RSS
        try:
            import feedparser
            feed_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}"
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:20]:
                articles.append({
                    "title": entry.get('title'),
                    "description": entry.get('summary'),
                    "source": {"name": "Yahoo Finance"},
                    "publishedAt": entry.get('published'),
                    "url": entry.get('link')
                })
        except Exception as e:
            logger.debug(f"Yahoo RSS fallback failed: {e}")
        
        return articles
    
    def _analyze_text(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        if not text:
            return {"compound": 0.0, "label": "neutral"}
        
        # Clean text
        text = re.sub(r'http\S+', '', text)
        text = text[:512]  # Limit length for models
        
        scores = []
        
        # FinBERT analysis (finance-specific)
        if self.finbert:
            try:
                result = self.finbert(text)[0]
                label = result['label'].lower()
                score = result['score']
                
                if label == 'positive':
                    finbert_score = score
                elif label == 'negative':
                    finbert_score = -score
                else:
                    finbert_score = 0
                
                scores.append(('finbert', finbert_score, 0.6))  # Higher weight
            except Exception as e:
                logger.debug(f"FinBERT error: {e}")
        
        # VADER analysis (general purpose, fast)
        if self.vader:
            vader_scores = self.vader.polarity_scores(text)
            scores.append(('vader', vader_scores['compound'], 0.4))
        
        # Weighted average
        if scores:
            total_weight = sum(s[2] for s in scores)
            compound = sum(s[1] * s[2] for s in scores) / total_weight
        else:
            compound = 0.0
        
        return {
            "compound": compound,
            "label": self._score_to_label(compound)
        }
    
    def _score_to_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score >= 0.3:
            return "very_positive"
        elif score >= 0.1:
            return "positive"
        elif score <= -0.3:
            return "very_negative"
        elif score <= -0.1:
            return "negative"
        else:
            return "neutral"
    
    def get_social_sentiment(self, symbol: str) -> Dict:
        """
        Get social media sentiment (Reddit, Twitter/X)
        
        Note: Requires additional API setup for full functionality
        """
        # Reddit sentiment via free API
        try:
            subreddits = ["wallstreetbets", "stocks", "investing"]
            all_posts = []
            
            for subreddit in subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    "q": symbol,
                    "sort": "new",
                    "limit": 25,
                    "t": "week"
                }
                headers = {"User-Agent": "StockPicker/1.0"}
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])
                    all_posts.extend(posts)
            
            if not all_posts:
                return {
                    "symbol": symbol,
                    "overall_sentiment": 0.0,
                    "mention_count": 0,
                    "source": "reddit"
                }
            
            # Analyze sentiment
            sentiments = []
            for post in all_posts:
                post_data = post.get('data', {})
                text = f"{post_data.get('title', '')} {post_data.get('selftext', '')}"
                sentiment = self._analyze_text(text)
                sentiments.append(sentiment['compound'])
            
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            return {
                "symbol": symbol,
                "overall_sentiment": avg_sentiment,
                "sentiment_label": self._score_to_label(avg_sentiment),
                "mention_count": len(all_posts),
                "bullish_ratio": sum(1 for s in sentiments if s > 0.1) / len(sentiments),
                "source": "reddit"
            }
            
        except Exception as e:
            logger.error(f"Error fetching social sentiment: {e}")
            return {
                "symbol": symbol,
                "overall_sentiment": 0.0,
                "mention_count": 0,
                "source": "reddit",
                "error": str(e)
            }
    
    def get_combined_sentiment(self, symbol: str, company_name: Optional[str] = None) -> Dict:
        """
        Get combined sentiment from all sources
        
        Args:
            symbol: Stock ticker
            company_name: Optional company name for better search
        
        Returns:
            Combined sentiment analysis
        """
        news = self.get_news_sentiment(symbol, company_name)
        social = self.get_social_sentiment(symbol)
        
        # Weighted combination (news weighted higher)
        news_weight = 0.6
        social_weight = 0.4
        
        combined_score = (
            news['overall_sentiment'] * news_weight +
            social['overall_sentiment'] * social_weight
        )
        
        return {
            "symbol": symbol,
            "combined_sentiment": combined_score,
            "combined_label": self._score_to_label(combined_score),
            "news_sentiment": news['overall_sentiment'],
            "social_sentiment": social['overall_sentiment'],
            "news_article_count": news['article_count'],
            "social_mention_count": social['mention_count'],
            "signal_strength": abs(combined_score),
            "recommendation": self._sentiment_to_signal(combined_score),
            "details": {
                "news": news,
                "social": social
            }
        }
    
    def _sentiment_to_signal(self, score: float) -> str:
        """Convert sentiment to trading signal"""
        if score >= 0.3:
            return "STRONG_BUY"
        elif score >= 0.15:
            return "BUY"
        elif score <= -0.3:
            return "STRONG_SELL"
        elif score <= -0.15:
            return "SELL"
        else:
            return "HOLD"
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key not in self._cache:
            return False
        cached_time, _ = self._cache[key]
        return datetime.now() - cached_time < self._cache_duration


class EarningsCalendar:
    """
    Earnings calendar and earnings surprise analysis
    """
    
    def __init__(self):
        self._cache: Dict[str, Tuple[datetime, Dict]] = {}
    
    def get_upcoming_earnings(self, symbol: str) -> Dict:
        """
        Get upcoming earnings date and historical surprises
        
        Args:
            symbol: Stock ticker
        
        Returns:
            Earnings information
        """
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            calendar = ticker.calendar
            
            # Get earnings dates
            # Handle calendar as dict or DataFrame
            earnings_date = None
            if calendar is not None:
                if isinstance(calendar, dict):
                    earnings_date = calendar.get('Earnings Date')
                    if isinstance(earnings_date, list) and earnings_date:
                        earnings_date = earnings_date[0]
                elif hasattr(calendar, 'empty') and not calendar.empty:
                    earnings_date = calendar.iloc[0].get('Earnings Date') if len(calendar) > 0 else None
            
            # Get historical earnings
            earnings_history = ticker.earnings_history
            
            surprises = []
            if earnings_history is not None and hasattr(earnings_history, 'empty') and not earnings_history.empty:
                for _, row in earnings_history.iterrows():
                    surprise_pct = row.get('surprisePercent', 0) or 0
                    surprises.append({
                        "date": str(row.name),
                        "eps_actual": row.get('epsActual'),
                        "eps_estimate": row.get('epsEstimate'),
                        "surprise_pct": surprise_pct
                    })
            
            # Calculate average surprise
            avg_surprise = sum(s['surprise_pct'] for s in surprises) / len(surprises) if surprises else 0
            beat_rate = sum(1 for s in surprises if s['surprise_pct'] > 0) / len(surprises) if surprises else 0
            
            return {
                "symbol": symbol,
                "next_earnings_date": str(earnings_date) if earnings_date else None,
                "days_until_earnings": self._days_until(earnings_date),
                "avg_surprise_pct": avg_surprise,
                "beat_rate": beat_rate,
                "earnings_history": surprises[:8],  # Last 8 quarters
                "earnings_risk": self._calculate_earnings_risk(earnings_date, avg_surprise)
            }
            
        except Exception as e:
            logger.error(f"Error getting earnings for {symbol}: {e}")
            return {
                "symbol": symbol,
                "next_earnings_date": None,
                "error": str(e)
            }
    
    def _days_until(self, date) -> Optional[int]:
        """Calculate days until a date"""
        if date is None:
            return None
        try:
            if hasattr(date, 'date'):
                target = date.date()
            else:
                from datetime import datetime
                target = datetime.strptime(str(date)[:10], '%Y-%m-%d').date()
            
            today = datetime.now().date()
            delta = (target - today).days
            return delta if delta >= 0 else None
        except:
            return None
    
    def _calculate_earnings_risk(self, earnings_date, avg_surprise: float) -> str:
        """Calculate risk level around earnings"""
        days = self._days_until(earnings_date)
        
        if days is None:
            return "unknown"
        elif days <= 7:
            if abs(avg_surprise) > 10:
                return "high"  # Volatile stock near earnings
            return "medium"
        elif days <= 30:
            return "low"
        else:
            return "minimal"


# Create instances
sentiment_analyzer = NewsSentimentAnalyzer()
earnings_calendar = EarningsCalendar()
