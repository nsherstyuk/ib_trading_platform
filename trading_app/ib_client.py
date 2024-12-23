from ib_insync import *
import pandas as pd
from datetime import datetime
import logging
import asyncio
import time
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
        self.current_bar = {
            'open': None,
            'high': None,
            'low': None,
            'close': None,
            'volume': 0,
            'timestamp': None
        }
        self._last_connection_attempt = 0
        self._connection_cooldown = 5  # seconds between connection attempts

    def connect(self, host='127.0.0.1', port=7497, client_id=1):
        """Connect to Interactive Brokers TWS with retry mechanism"""
        try:
            # Prevent rapid reconnection attempts
            current_time = time.time()
            if (current_time - self._last_connection_attempt) < self._connection_cooldown:
                logger.warning("Connection attempt too soon after last attempt. Please wait.")
                return False

            self._last_connection_attempt = current_time

            if self.connected:
                logger.info("Already connected to IB")
                return True

            # Ensure we're in the event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            logger.info(f"Connecting to IB at {host}:{port} with client ID {client_id}")

            # Try to connect with timeout
            try:
                self.ib.connect(host, port, clientId=client_id, readonly=True, timeout=20)
                self.connected = True
                logger.info("Successfully connected to IB")
                return True
            except ConnectionRefusedError:
                logger.error("Connection refused. Please verify TWS is running and API connections are enabled.")
                return False
            except Exception as e:
                logger.error(f"Connection failed: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to IB: {str(e)}")
            return False

    def subscribe_market_data(self, symbol):
        """Subscribe to real-time market data"""
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)

            def on_price_update(trade):
                current_time = datetime.now()
                price = trade.price
                size = trade.size

                # Initialize new bar if needed
                if self.current_bar['timestamp'] is None or \
                   (current_time - self.current_bar['timestamp']).seconds >= 60:  # 1-minute bars
                    if self.current_bar['timestamp'] is not None:
                        self.price_data.append(self.current_bar.copy())

                    self.current_bar = {
                        'open': price,
                        'high': price,
                        'low': price,
                        'close': price,
                        'volume': size,
                        'timestamp': current_time
                    }
                else:
                    # Update current bar
                    self.current_bar['high'] = max(self.current_bar['high'], price)
                    self.current_bar['low'] = min(self.current_bar['low'], price)
                    self.current_bar['close'] = price
                    self.current_bar['volume'] += size

            self.ib.reqMktData(contract, '', False, False)
            self.ib.pendingTickersEvent += on_price_update
            logger.info(f"Subscribed to market data for {symbol}")

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
        try:
            positions = self.ib.positions()
            df = pd.DataFrame([
                {
                    'symbol': p.contract.symbol,
                    'position': p.position,
                    'avg_cost': p.avgCost
                } for p in positions
            ])
            return df
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return pd.DataFrame()

    def get_orders(self):
        """Get order book"""
        try:
            df = pd.DataFrame(self.orders).T
            return df
        except Exception as e:
            logger.error(f"Error getting orders: {str(e)}")
            return pd.DataFrame()

    def get_trades(self):
        """Get trade history"""
        try:
            df = pd.DataFrame(self.trades)
            return df
        except Exception as e:
            logger.error(f"Error getting trades: {str(e)}")
            return pd.DataFrame()

    def get_daily_pnl(self):
        """Get daily P&L"""
        try:
            return self.trade_journal.get_daily_performance().get(datetime.now().date(), 0.0)
        except Exception as e:
            logger.error(f"Error getting daily PnL: {str(e)}")
            return 0.0

    def get_total_pnl(self):
        """Get total P&L"""
        try:
            return self.trade_journal.get_metrics().get('total_pnl', 0.0)
        except Exception as e:
            logger.error(f"Error getting total PnL: {str(e)}")
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
            return self.price_data[-1].get('close', 0) # Use 'close' price for OHLC
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
        try:
            return self.trade_journal.get_metrics()
        except Exception as e:
            logger.error(f"Error getting trade metrics: {str(e)}")
            return {}

    def get_trade_history(self):
        """Get complete trade history"""
        try:
            return self.trade_journal.get_trade_history()
        except Exception as e:
            logger.error(f"Error getting trade history: {str(e)}")
            return pd.DataFrame()

    def export_trade_journal(self, format='csv'):
        """Export trade journal to file"""
        try:
            return self.trade_journal.export_trade_journal(format)
        except Exception as e:
            logger.error(f"Error exporting trade journal: {str(e)}")
            return None