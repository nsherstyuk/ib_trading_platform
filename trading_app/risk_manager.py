import pandas as pd
from datetime import datetime
import logging
from logger import setup_logger

logger = setup_logger()

class RiskManager:
    def __init__(self):
        self.max_position_size = 1000
        self.max_daily_loss = -5000
        self.stop_loss_pct = 2.0
        self.daily_pnl = 0
        
    def check_position_limits(self, current_position, proposed_quantity):
        """Check if proposed trade exceeds position limits"""
        if abs(current_position + proposed_quantity) > self.max_position_size:
            logger.warning("Position limit would be exceeded")
            return False
        return True
        
    def check_daily_loss_limit(self, current_pnl):
        """Check if daily loss limit has been reached"""
        if current_pnl < self.max_daily_loss:
            logger.warning("Daily loss limit reached")
            return False
        return True
        
    def calculate_stop_loss(self, entry_price):
        """Calculate stop loss price"""
        return entry_price * (1 - self.stop_loss_pct/100)
        
    def should_exit_position(self, current_price, position):
        """Check if position should be exited based on risk parameters"""
        if position.stop_loss and current_price <= position.stop_loss:
            logger.warning("Stop loss triggered")
            return True
        return False
        
    def update_daily_pnl(self, pnl):
        """Update daily P&L tracking"""
        self.daily_pnl = pnl
        
    def reset_daily_metrics(self):
        """Reset daily tracking metrics"""
        self.daily_pnl = 0
