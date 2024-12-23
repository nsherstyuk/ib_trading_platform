import numpy as np
import pandas as pd
from datetime import datetime
import logging
from logger import setup_logger

logger = setup_logger()

class TradingLogic:
    def __init__(self):
        self.active = False
        self.symbol = None
        self.quantity = None
        self.position = 0
        self.last_signal = None

    def start_trading(self, symbol, quantity):
        """Start trading algorithm"""
        self.active = True
        self.symbol = symbol
        self.quantity = quantity
        logger.info(f"Started trading algorithm for {symbol}")

    def stop_trading(self):
        """Stop trading algorithm"""
        self.active = False
        logger.info("Stopped trading algorithm")

    def calculate_signal(self, price_data):
        """Calculate trading signal based on OHLC price data"""
        if len(price_data) < 50:  # Need minimum data points for both SMAs
            return None

        df = pd.DataFrame(price_data)

        # Use typical price for SMA calculation
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3

        # Calculate technical indicators
        df['SMA20'] = df['typical_price'].rolling(window=20).mean()
        df['SMA50'] = df['typical_price'].rolling(window=50).mean()

        # Additional momentum indicator
        df['ROC'] = df['typical_price'].pct_change(periods=10) * 100  # 10-period Rate of Change

        # Generate signals with confirmation from momentum
        last_row = df.iloc[-1]
        if last_row['SMA20'] > last_row['SMA50'] and last_row['ROC'] > 0:
            return 'BUY'
        elif last_row['SMA20'] < last_row['SMA50'] and last_row['ROC'] < 0:
            return 'SELL'
        else:
            return None

    def execute_signal(self, ib_client, signal):
        """Execute trading signal"""
        if not self.active:
            return

        if signal == 'BUY' and self.position <= 0:
            order_id = ib_client.place_order(
                self.symbol,
                self.quantity,
                'BUY'
            )
            if order_id:
                self.position += self.quantity
                self.last_signal = signal
                logger.info(f"Executed BUY signal for {self.symbol}")

        elif signal == 'SELL' and self.position >= 0:
            order_id = ib_client.place_order(
                self.symbol,
                self.quantity,
                'SELL'
            )
            if order_id:
                self.position -= self.quantity
                self.last_signal = signal
                logger.info(f"Executed SELL signal for {self.symbol}")