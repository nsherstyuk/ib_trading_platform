from ib_insync import *
import pandas as pd
from datetime import datetime
import logging
from logger import setup_logger

logger = setup_logger()

class IBClient:
    def __init__(self):
        self.ib = IB()
        self.connected = False
        self.price_data = []
        self.positions = {}
        self.orders = {}
        self.trades = []

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
