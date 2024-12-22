from ib_insync import *
import pandas as pd
from datetime import datetime
import logging
from logger import setup_logger
from trade_journal import TradeJournal

logger = setup_logger()

class IBClient:
    def __init__(self):
        self.ib = IB()
        self.connected = False
        self.price_data = []
        self.positions = {}
        self.orders = {}
        self.trades = []
        self.trade_journal = TradeJournal()

    def connect(self):
        """Connect to Interactive Brokers TWS"""
        try:
            self.ib.connect('127.0.0.1', 7497, clientId=1)
            self.connected = True
            logger.info("Successfully connected to IB")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IB: {str(e)}")
            return False

    def subscribe_market_data(self, symbol):
        """Subscribe to real-time market data"""
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            def on_price_update(trade):
                self.price_data.append({
                    'timestamp': datetime.now(),
                    'price': trade.price,
                    'size': trade.size
                })
            
            self.ib.reqMktData(contract, '', False, False)
            self.ib.pendingTickersEvent += on_price_update
            
        except Exception as e:
            logger.error(f"Error subscribing to market data: {str(e)}")

    def place_order(self, symbol, quantity, action, order_type='MKT'):
        """Place a new order"""
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            if order_type == 'MKT':
                order = MarketOrder(action, quantity)

            trade = self.ib.placeOrder(contract, order)

            # Store order details
            order_id = trade.order.orderId
            self.orders[order_id] = {
                'symbol': symbol,
                'quantity': quantity,
                'action': action,
                'status': 'SUBMITTED',
                'timestamp': datetime.now()
            }

            # Log the trade
            current_price = self.get_current_price(symbol)
            trade_data = {
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': current_price,
                'pnl': self.calculate_trade_pnl(symbol, quantity, action, current_price)
            }
            self.trade_journal.log_trade(trade_data)

            logger.info(f"Order placed: {symbol} {action} {quantity}")
            return order_id

        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return None

    def get_positions(self):
        """Get current positions"""
        positions = self.ib.positions()
        df = pd.DataFrame([
            {
                'symbol': p.contract.symbol,
                'position': p.position,
                'avg_cost': p.avgCost
            } for p in positions
        ])
        return df

    def get_orders(self):
        """Get order book"""
        df = pd.DataFrame(self.orders).T
        return df

    def get_trades(self):
        """Get trade history"""
        df = pd.DataFrame(self.trades)
        return df

    def get_daily_pnl(self):
        """Get daily P&L"""
        # Implementation depends on IB account structure
        return 0.0

    def get_total_pnl(self):
        """Get total P&L"""
        # Implementation depends on IB account structure
        return 0.0

    def disconnect(self):
        """Disconnect from IB"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IB")

    def get_current_price(self, symbol):
        """Get current market price for a symbol"""
        if self.price_data:
            return self.price_data[-1].get('price', 0)
        return 0

    def calculate_trade_pnl(self, symbol, quantity, action, current_price):
        """Calculate P&L for a trade"""
        position = self.get_position(symbol)
        if position is None:
            return 0

        avg_cost = position.get('avg_cost', current_price)
        if action == 'BUY':
            return 0  # P&L calculated on close
        else:
            return (current_price - avg_cost) * quantity

    def get_position(self, symbol):
        """Helper function to retrieve position details."""
        for pos in self.ib.positions():
            if pos.contract.symbol == symbol:
                return {'symbol': pos.contract.symbol, 'position': pos.position, 'avg_cost': pos.avgCost}
        return None

    def get_trade_metrics(self):
        """Get trading performance metrics"""
        return self.trade_journal.get_metrics()

    def get_trade_history(self):
        """Get complete trade history"""
        return self.trade_journal.get_trade_history()

    def export_trade_journal(self, format='csv'):
        """Export trade journal to file"""
        return self.trade_journal.export_trade_journal(format)