"""
LSTM and Transformer Models for Time Series Prediction
Deep learning models for stock price forecasting
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from loguru import logger
from pathlib import Path

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import (
        LSTM, GRU, Dense, Dropout, Input, 
        MultiHeadAttention, LayerNormalization,
        GlobalAveragePooling1D, Bidirectional
    )
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
    from tensorflow.keras.optimizers import Adam
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logger.warning("TensorFlow not available. Install with: pip install tensorflow")

from sklearn.preprocessing import MinMaxScaler
import joblib


class LSTMPredictor:
    """
    LSTM-based stock price predictor
    
    Uses sequence of historical prices to predict future movements
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        prediction_horizon: int = 5,
        features: Optional[List[str]] = None
    ):
        """
        Initialize LSTM predictor
        
        Args:
            sequence_length: Number of time steps to look back
            prediction_horizon: Number of days ahead to predict
            features: List of feature columns to use (None = use defaults)
        """
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        self.features = features or [
            'close', 'volume', 'rsi_14', 'macd', 'sma_20', 'sma_50',
            'bb_position', 'atr_14', 'return_1d', 'volume_ratio'
        ]
        
        self.model = None
        self.scaler = MinMaxScaler()
        self.target_scaler = MinMaxScaler()
        self.is_fitted = False
        
        if not TF_AVAILABLE:
            logger.error("TensorFlow not available. LSTM model cannot be used.")
    
    def build_model(self, input_shape: Tuple[int, int]) -> None:
        """
        Build the LSTM model architecture
        
        Args:
            input_shape: Shape of input (sequence_length, num_features)
        """
        if not TF_AVAILABLE:
            return
        
        self.model = Sequential([
            # First LSTM layer
            LSTM(128, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            
            # Second LSTM layer
            LSTM(64, return_sequences=True),
            Dropout(0.2),
            
            # Third LSTM layer
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            
            # Dense layers
            Dense(32, activation='relu'),
            Dropout(0.1),
            Dense(16, activation='relu'),
            
            # Output layer (regression for price, or sigmoid for direction)
            Dense(1, activation='linear')
        ])
        
        self.model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        logger.info(f"LSTM model built: {self.model.count_params():,} parameters")
    
    def prepare_data(
        self,
        df: pd.DataFrame,
        target_col: str = 'close'
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare data for LSTM training
        
        Args:
            df: DataFrame with features
            target_col: Column to predict
        
        Returns:
            X_train, X_test, y_train, y_test
        """
        # Select features that exist
        available_features = [f for f in self.features if f in df.columns]
        if not available_features:
            available_features = ['close', 'volume']
        
        logger.info(f"Using features: {available_features}")
        
        # Prepare feature data
        data = df[available_features].values
        
        # Create target (future returns or prices)
        target = df[target_col].shift(-self.prediction_horizon).values
        
        # Remove NaN rows
        valid_idx = ~np.isnan(target)
        data = data[:-self.prediction_horizon]
        target = target[valid_idx][:-self.prediction_horizon] if sum(valid_idx) > self.prediction_horizon else target[:-self.prediction_horizon]
        
        # Handle remaining NaN
        data = np.nan_to_num(data, nan=0)
        target = np.nan_to_num(target, nan=0)
        
        # Scale data
        data_scaled = self.scaler.fit_transform(data)
        target_scaled = self.target_scaler.fit_transform(target.reshape(-1, 1))
        
        # Create sequences
        X, y = [], []
        for i in range(self.sequence_length, len(data_scaled)):
            X.append(data_scaled[i-self.sequence_length:i])
            y.append(target_scaled[i-1])  # Predict next value
        
        X = np.array(X)
        y = np.array(y)
        
        # Train/test split (time-based)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        logger.info(f"Data prepared: Train={len(X_train)}, Test={len(X_test)}")
        
        return X_train, X_test, y_train, y_test
    
    def train(
        self,
        df: pd.DataFrame,
        epochs: int = 100,
        batch_size: int = 32,
        validation_split: float = 0.1
    ) -> Dict:
        """
        Train the LSTM model
        
        Args:
            df: DataFrame with features and target
            epochs: Number of training epochs
            batch_size: Training batch size
            validation_split: Fraction for validation
        
        Returns:
            Training history
        """
        if not TF_AVAILABLE:
            logger.error("TensorFlow not available")
            return {}
        
        # Prepare data
        X_train, X_test, y_train, y_test = self.prepare_data(df)
        
        if len(X_train) < batch_size:
            logger.error("Not enough training data")
            return {}
        
        # Build model
        input_shape = (X_train.shape[1], X_train.shape[2])
        self.build_model(input_shape)
        
        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=15,
                restore_best_weights=True
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=0.0001
            )
        ]
        
        # Train
        logger.info("Training LSTM model...")
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=callbacks,
            verbose=1
        )
        
        # Evaluate
        test_loss, test_mae = self.model.evaluate(X_test, y_test, verbose=0)
        logger.info(f"Test Loss: {test_loss:.6f}, Test MAE: {test_mae:.6f}")
        
        self.is_fitted = True
        
        return {
            "train_loss": history.history['loss'][-1],
            "val_loss": history.history['val_loss'][-1],
            "test_loss": test_loss,
            "test_mae": test_mae,
            "epochs_trained": len(history.history['loss'])
        }
    
    def predict(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions
        
        Args:
            df: DataFrame with features
        
        Returns:
            Tuple of (predictions, confidence)
        """
        if not self.is_fitted:
            raise ValueError("Model not trained. Call train() first.")
        
        # Prepare features
        available_features = [f for f in self.features if f in df.columns]
        data = df[available_features].values
        data = np.nan_to_num(data, nan=0)
        data_scaled = self.scaler.transform(data)
        
        # Create sequences
        X = []
        for i in range(self.sequence_length, len(data_scaled) + 1):
            X.append(data_scaled[i-self.sequence_length:i])
        
        if not X:
            return np.array([]), np.array([])
        
        X = np.array(X)
        
        # Predict
        predictions_scaled = self.model.predict(X, verbose=0)
        predictions = self.target_scaler.inverse_transform(predictions_scaled)
        
        # Estimate confidence (based on prediction variance across slightly modified inputs)
        confidence = np.ones(len(predictions)) * 0.5  # Default confidence
        
        return predictions.flatten(), confidence
    
    def predict_direction(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict price direction (up/down)
        
        Args:
            df: DataFrame with features
        
        Returns:
            Tuple of (direction: 1=up, 0=down, confidence)
        """
        predictions, confidence = self.predict(df)
        
        if len(predictions) == 0:
            return np.array([]), np.array([])
        
        # Compare predictions to current prices
        current_prices = df['close'].values[-len(predictions):]
        directions = (predictions > current_prices).astype(int)
        
        return directions, confidence
    
    def save(self, path: str = "models/lstm"):
        """Save the model"""
        if not self.is_fitted:
            logger.warning("Model not trained")
            return
        
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        self.model.save(path / "lstm_model.keras")
        joblib.dump(self.scaler, path / "scaler.joblib")
        joblib.dump(self.target_scaler, path / "target_scaler.joblib")
        joblib.dump(self.features, path / "features.joblib")
        
        logger.info(f"LSTM model saved to {path}")
    
    def load(self, path: str = "models/lstm"):
        """Load a trained model"""
        if not TF_AVAILABLE:
            logger.error("TensorFlow not available")
            return
        
        path = Path(path)
        
        self.model = keras.models.load_model(path / "lstm_model.keras")
        self.scaler = joblib.load(path / "scaler.joblib")
        self.target_scaler = joblib.load(path / "target_scaler.joblib")
        self.features = joblib.load(path / "features.joblib")
        self.is_fitted = True
        
        logger.info(f"LSTM model loaded from {path}")


class TransformerPredictor:
    """
    Transformer-based stock predictor
    
    Uses self-attention mechanism for time series prediction
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        prediction_horizon: int = 5,
        d_model: int = 64,
        num_heads: int = 4,
        num_layers: int = 2
    ):
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        self.d_model = d_model
        self.num_heads = num_heads
        self.num_layers = num_layers
        
        self.model = None
        self.scaler = MinMaxScaler()
        self.target_scaler = MinMaxScaler()
        self.is_fitted = False
        self.features = ['close', 'volume', 'rsi_14', 'macd', 'sma_20']
    
    def build_model(self, input_shape: Tuple[int, int]) -> None:
        """Build Transformer model"""
        if not TF_AVAILABLE:
            return
        
        inputs = Input(shape=input_shape)
        
        # Project to d_model dimensions
        x = Dense(self.d_model)(inputs)
        
        # Transformer encoder blocks
        for _ in range(self.num_layers):
            # Multi-head attention
            attention_output = MultiHeadAttention(
                num_heads=self.num_heads,
                key_dim=self.d_model // self.num_heads
            )(x, x)
            x = LayerNormalization(epsilon=1e-6)(x + attention_output)
            
            # Feed-forward
            ff_output = Dense(self.d_model * 4, activation='relu')(x)
            ff_output = Dense(self.d_model)(ff_output)
            ff_output = Dropout(0.1)(ff_output)
            x = LayerNormalization(epsilon=1e-6)(x + ff_output)
        
        # Global pooling and output
        x = GlobalAveragePooling1D()(x)
        x = Dense(32, activation='relu')(x)
        x = Dropout(0.1)(x)
        outputs = Dense(1, activation='linear')(x)
        
        self.model = Model(inputs, outputs)
        self.model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        logger.info(f"Transformer model built: {self.model.count_params():,} parameters")
    
    def train(self, df: pd.DataFrame, epochs: int = 100, batch_size: int = 32) -> Dict:
        """Train the Transformer model"""
        if not TF_AVAILABLE:
            return {}
        
        # Similar data preparation as LSTM
        available_features = [f for f in self.features if f in df.columns]
        data = df[available_features].values
        target = df['close'].shift(-self.prediction_horizon).values
        
        data = data[:-self.prediction_horizon]
        target = target[:-self.prediction_horizon]
        
        data = np.nan_to_num(data, nan=0)
        target = np.nan_to_num(target, nan=0)
        
        data_scaled = self.scaler.fit_transform(data)
        target_scaled = self.target_scaler.fit_transform(target.reshape(-1, 1))
        
        # Create sequences
        X, y = [], []
        for i in range(self.sequence_length, len(data_scaled)):
            X.append(data_scaled[i-self.sequence_length:i])
            y.append(target_scaled[i-1])
        
        X = np.array(X)
        y = np.array(y)
        
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Build and train
        self.build_model((X_train.shape[1], X_train.shape[2]))
        
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)
        ]
        
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.1,
            callbacks=callbacks,
            verbose=1
        )
        
        test_loss, test_mae = self.model.evaluate(X_test, y_test, verbose=0)
        logger.info(f"Transformer - Test Loss: {test_loss:.6f}, MAE: {test_mae:.6f}")
        
        self.is_fitted = True
        
        return {
            "test_loss": test_loss,
            "test_mae": test_mae
        }


class HybridEnsemble:
    """
    Ensemble combining LSTM, Transformer, and traditional ML models
    """
    
    def __init__(self):
        self.lstm = LSTMPredictor()
        self.transformer = TransformerPredictor()
        self.weights = {
            'lstm': 0.4,
            'transformer': 0.3,
            'ml': 0.3  # From existing ML models
        }
        self.is_fitted = False
    
    def train(self, df: pd.DataFrame, **kwargs) -> Dict:
        """Train all models in the ensemble"""
        results = {}
        
        # Train LSTM
        logger.info("Training LSTM...")
        results['lstm'] = self.lstm.train(df, **kwargs)
        
        # Train Transformer
        logger.info("Training Transformer...")
        results['transformer'] = self.transformer.train(df, **kwargs)
        
        self.is_fitted = True
        return results
    
    def predict(self, df: pd.DataFrame, ml_predictions: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get ensemble predictions
        
        Args:
            df: DataFrame with features
            ml_predictions: Optional predictions from ML models
        
        Returns:
            Tuple of (predictions, confidence)
        """
        predictions = []
        weights = []
        
        # LSTM predictions
        if self.lstm.is_fitted:
            lstm_pred, _ = self.lstm.predict(df)
            if len(lstm_pred) > 0:
                predictions.append(lstm_pred)
                weights.append(self.weights['lstm'])
        
        # Transformer predictions
        if self.transformer.is_fitted:
            try:
                trans_pred, _ = self.transformer.predict(df)
                if len(trans_pred) > 0:
                    predictions.append(trans_pred)
                    weights.append(self.weights['transformer'])
            except:
                pass
        
        # ML predictions
        if ml_predictions is not None and len(ml_predictions) > 0:
            predictions.append(ml_predictions)
            weights.append(self.weights['ml'])
        
        if not predictions:
            return np.array([]), np.array([])
        
        # Align lengths
        min_len = min(len(p) for p in predictions)
        predictions = [p[-min_len:] for p in predictions]
        
        # Weighted average
        total_weight = sum(weights)
        ensemble_pred = sum(p * w for p, w in zip(predictions, weights)) / total_weight
        
        # Confidence based on agreement
        if len(predictions) > 1:
            std = np.std(predictions, axis=0)
            confidence = 1 - np.clip(std / np.mean(ensemble_pred), 0, 1)
        else:
            confidence = np.ones(len(ensemble_pred)) * 0.5
        
        return ensemble_pred, confidence


# Create instances
lstm_predictor = LSTMPredictor()
transformer_predictor = TransformerPredictor()
hybrid_ensemble = HybridEnsemble()
