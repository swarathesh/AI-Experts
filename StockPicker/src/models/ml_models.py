"""
Machine Learning Models for Stock Prediction
Implements ensemble of models for price direction prediction
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import xgboost as xgb
import lightgbm as lgb
from loguru import logger
import joblib
from pathlib import Path


class StockPredictor:
    """
    Ensemble ML model for stock prediction
    Predicts whether price will go up or down over a specified horizon
    """
    
    def __init__(self, prediction_horizon: int = 5):
        """
        Initialize the predictor
        
        Args:
            prediction_horizon: Number of days ahead to predict
        """
        self.prediction_horizon = prediction_horizon
        self.scaler = StandardScaler()
        self.models: Dict = {}
        self.feature_columns: List[str] = []
        self.is_fitted = False
        
        # Model weights for ensemble
        self.weights = {
            "xgboost": 0.4,
            "lightgbm": 0.35,
            "random_forest": 0.25
        }
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features and target for training
        
        Args:
            df: DataFrame with technical indicators
        
        Returns:
            Tuple of (features DataFrame, target Series)
        """
        df = df.copy()
        
        # Create target: 1 if price goes up over horizon, 0 otherwise
        df['target'] = (df['close'].shift(-self.prediction_horizon) > df['close']).astype(int)
        
        # Drop non-feature columns
        exclude_cols = ['open', 'high', 'low', 'close', 'volume', 'dividends', 
                       'stock splits', 'target', 'body', 'upper_shadow', 
                       'lower_shadow', 'hl_range']
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        self.feature_columns = feature_cols
        
        # Drop rows with NaN
        df_clean = df.dropna()
        
        X = df_clean[feature_cols]
        y = df_clean['target']
        
        return X, y
    
    def train(
        self, 
        X: pd.DataFrame, 
        y: pd.Series,
        test_size: float = 0.2,
        n_splits: int = 5
    ) -> Dict:
        """
        Train the ensemble model using time series cross-validation
        
        Args:
            X: Feature DataFrame
            y: Target Series
            test_size: Fraction of data for testing
            n_splits: Number of cross-validation splits
        
        Returns:
            Dictionary with training metrics
        """
        logger.info(f"Training on {len(X)} samples with {len(self.feature_columns)} features")
        
        # Time series split for validation
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Initialize models
        self.models = {
            "xgboost": xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                use_label_encoder=False,
                eval_metric='logloss'
            ),
            "lightgbm": lgb.LGBMClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbose=-1
            ),
            "random_forest": RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
        }
        
        # Train each model
        metrics = {}
        for name, model in self.models.items():
            logger.info(f"Training {name}...")
            
            if name == "random_forest":
                model.fit(X_train_scaled, y_train)
                y_pred = model.predict(X_test_scaled)
            else:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
            
            metrics[name] = {
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred, zero_division=0),
                "recall": recall_score(y_test, y_pred, zero_division=0),
                "f1": f1_score(y_test, y_pred, zero_division=0)
            }
            
            logger.info(f"{name} - Accuracy: {metrics[name]['accuracy']:.4f}, F1: {metrics[name]['f1']:.4f}")
        
        # Ensemble prediction
        ensemble_pred = self._ensemble_predict(X_test, X_test_scaled)
        metrics["ensemble"] = {
            "accuracy": accuracy_score(y_test, ensemble_pred),
            "precision": precision_score(y_test, ensemble_pred, zero_division=0),
            "recall": recall_score(y_test, ensemble_pred, zero_division=0),
            "f1": f1_score(y_test, ensemble_pred, zero_division=0)
        }
        
        logger.info(f"Ensemble - Accuracy: {metrics['ensemble']['accuracy']:.4f}, F1: {metrics['ensemble']['f1']:.4f}")
        
        self.is_fitted = True
        return metrics
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions with confidence scores
        
        Args:
            X: Feature DataFrame
        
        Returns:
            Tuple of (predictions, confidence scores)
        """
        if not self.is_fitted:
            raise ValueError("Model not trained. Call train() first.")
        
        X = X[self.feature_columns]
        X_scaled = self.scaler.transform(X)
        
        predictions = self._ensemble_predict(X, X_scaled)
        confidences = self._ensemble_confidence(X, X_scaled)
        
        return predictions, confidences
    
    def _ensemble_predict(self, X: pd.DataFrame, X_scaled: np.ndarray) -> np.ndarray:
        """Get weighted ensemble prediction"""
        probas = self._get_probabilities(X, X_scaled)
        weighted_proba = sum(
            self.weights[name] * proba 
            for name, proba in probas.items()
        )
        return (weighted_proba > 0.5).astype(int)
    
    def _ensemble_confidence(self, X: pd.DataFrame, X_scaled: np.ndarray) -> np.ndarray:
        """Get ensemble confidence scores"""
        probas = self._get_probabilities(X, X_scaled)
        weighted_proba = sum(
            self.weights[name] * proba 
            for name, proba in probas.items()
        )
        # Confidence is how far from 0.5 (uncertain) the probability is
        return np.abs(weighted_proba - 0.5) * 2
    
    def _get_probabilities(self, X: pd.DataFrame, X_scaled: np.ndarray) -> Dict[str, np.ndarray]:
        """Get probability predictions from each model"""
        probas = {}
        for name, model in self.models.items():
            if name == "random_forest":
                probas[name] = model.predict_proba(X_scaled)[:, 1]
            else:
                probas[name] = model.predict_proba(X)[:, 1]
        return probas
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from all models"""
        if not self.is_fitted:
            raise ValueError("Model not trained. Call train() first.")
        
        importance_dict = {}
        
        for name, model in self.models.items():
            if hasattr(model, 'feature_importances_'):
                importance_dict[name] = model.feature_importances_
        
        importance_df = pd.DataFrame(importance_dict, index=self.feature_columns)
        importance_df['mean'] = importance_df.mean(axis=1)
        importance_df = importance_df.sort_values('mean', ascending=False)
        
        return importance_df
    
    def save(self, path: str = "models/stock_predictor"):
        """Save the trained model"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(self.models, path / "models.joblib")
        joblib.dump(self.scaler, path / "scaler.joblib")
        joblib.dump(self.feature_columns, path / "feature_columns.joblib")
        
        logger.info(f"Model saved to {path}")
    
    def load(self, path: str = "models/stock_predictor"):
        """Load a trained model"""
        path = Path(path)
        
        self.models = joblib.load(path / "models.joblib")
        self.scaler = joblib.load(path / "scaler.joblib")
        self.feature_columns = joblib.load(path / "feature_columns.joblib")
        self.is_fitted = True
        
        logger.info(f"Model loaded from {path}")


class SignalGenerator:
    """Generate trading signals from model predictions"""
    
    def __init__(self, predictor: StockPredictor, min_confidence: float = 0.6):
        """
        Initialize signal generator
        
        Args:
            predictor: Trained StockPredictor model
            min_confidence: Minimum confidence threshold for signals
        """
        self.predictor = predictor
        self.min_confidence = min_confidence
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals for a stock
        
        Args:
            df: DataFrame with technical indicators
        
        Returns:
            DataFrame with signals added
        """
        df = df.copy()
        
        # Prepare features
        X, _ = self.predictor.prepare_features(df)
        
        if len(X) == 0:
            logger.warning("No valid data for signal generation")
            return df
        
        # Get predictions
        predictions, confidences = self.predictor.predict(X)
        
        # Add to dataframe (align with original index)
        signal_df = pd.DataFrame({
            'prediction': predictions,
            'confidence': confidences
        }, index=X.index)
        
        df = df.join(signal_df)
        
        # Generate signals
        df['signal'] = 0  # 0 = hold, 1 = buy, -1 = sell
        
        # Buy signal: prediction is up with high confidence
        df.loc[
            (df['prediction'] == 1) & (df['confidence'] >= self.min_confidence),
            'signal'
        ] = 1
        
        # Sell signal: prediction is down with high confidence
        df.loc[
            (df['prediction'] == 0) & (df['confidence'] >= self.min_confidence),
            'signal'
        ] = -1
        
        return df


# Create instances
predictor = StockPredictor()
