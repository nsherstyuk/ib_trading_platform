import pandas as pd
import numpy as np
from datetime import datetime
import logging
from logger import setup_logger

logger = setup_logger()

class TradeJournal:
    def __init__(self):
        self.trades = []
        self.daily_performance = {}
        self.metrics = {}
        
    def log_trade(self, trade_data):
        """Log a new trade with timestamp and performance metrics"""
        trade_entry = {
            'timestamp': datetime.now(),
            'symbol': trade_data['symbol'],
            'action': trade_data['action'],
            'quantity': trade_data['quantity'],
            'price': trade_data['price'],
            'total_value': trade_data['price'] * trade_data['quantity'],
            'pnl': trade_data.get('pnl', 0),
            'strategy': trade_data.get('strategy', 'default')
        }
        
        self.trades.append(trade_entry)
        self._update_metrics()
        logger.info(f"Trade logged: {trade_entry}")
        
    def _update_metrics(self):
        """Update performance metrics"""
        if not self.trades:
            return
            
        df = pd.DataFrame(self.trades)
        
        # Calculate basic metrics
        self.metrics = {
            'total_trades': len(df),
            'winning_trades': len(df[df['pnl'] > 0]),
            'losing_trades': len(df[df['pnl'] < 0]),
            'total_pnl': df['pnl'].sum(),
            'win_rate': len(df[df['pnl'] > 0]) / len(df) if len(df) > 0 else 0,
            'avg_win': df[df['pnl'] > 0]['pnl'].mean() if len(df[df['pnl'] > 0]) > 0 else 0,
            'avg_loss': df[df['pnl'] < 0]['pnl'].mean() if len(df[df['pnl'] < 0]) > 0 else 0,
        }
        
        # Calculate daily performance
        df['date'] = df['timestamp'].dt.date
        daily_pnl = df.groupby('date')['pnl'].sum()
        self.daily_performance = daily_pnl.to_dict()
        
    def get_metrics(self):
        """Get current performance metrics"""
        return self.metrics
        
    def get_trade_history(self):
        """Get complete trade history"""
        return pd.DataFrame(self.trades)
        
    def get_daily_performance(self):
        """Get daily P&L performance"""
        return self.daily_performance
        
    def export_trade_journal(self, format='csv'):
        """Export trade journal to file"""
        if not self.trades:
            return None
            
        df = pd.DataFrame(self.trades)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trade_journal_{timestamp}.{format}"
        
        if format == 'csv':
            df.to_csv(f"logs/{filename}", index=False)
        elif format == 'json':
            df.to_json(f"logs/{filename}")
            
        logger.info(f"Trade journal exported to {filename}")
        return filename
