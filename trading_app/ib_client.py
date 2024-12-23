from ib_insync import IB, Stock, MarketOrder
import pandas as pd
from datetime import datetime, timedelta
import logging
import asyncio
import time
import socket
import numpy as np
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
        self._connection_cooldown = 5
        self._connection_retries = 3

    def _verify_tws_configuration(self, host, port):
        """Verify TWS configuration and connectivity"""
        try:
            logger.info(f"Verifying TWS configuration on {host}:{port}")

            # Test TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)

            # Try to establish connection
            try:
                sock.connect((host, port))
                logger.info("TCP connection successful")

                # Try basic API handshake
                sock.send(b"API\0")
                response = sock.recv(4096)

                if response:
                    logger.info("TWS API handshake successful")
                    sock.close()
                    return True, "TWS connection and API configuration verified"
                else:
                    error_msg = """
                    TWS is running but not responding to API requests.
                    Please check in TWS:
                    1. You are logged in to your account
                    2. API Configuration under Edit → Global Configuration → API:
                       - "Enable ActiveX and Socket Clients" is checked
                       - Socket port matches your trading mode (7497 for paper, 7496 for live)
                       - "Read-Only API" is unchecked
                    3. Try restarting TWS after making any changes
                    """
                    logger.error(error_msg)
                    return False, error_msg

            except ConnectionRefusedError:
                error_msg = """
                Connection was refused by TWS.
                This usually means:
                1. TWS is not running (check Task Manager/Activity Monitor)
                2. TWS is still starting up
                3. Wrong port number (7497 for paper trading, 7496 for live trading)
                """
                logger.error(error_msg)
                return False, error_msg

            except socket.timeout:
                error_msg = """
                Connection attempt timed out.
                This could mean:
                1. TWS is not responding
                2. A firewall is blocking the connection
                3. TWS API connections are disabled
                """
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"TWS configuration verification failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        finally:
            try:
                sock.close()
            except:
                pass

    def connect(self, host='127.0.0.1', port=7497, client_id=1):
        """Connect to Interactive Brokers TWS"""
        try:
            current_time = time.time()
            if (current_time - self._last_connection_attempt) < self._connection_cooldown:
                return False, "Please wait a few seconds before trying to connect again"

            self._last_connection_attempt = current_time

            if self.connected:
                return True, "Already connected to IB"

            logger.info(f"Verifying TWS configuration on {host}:{port}")

            # First verify TWS configuration
            success, message = self._verify_tws_configuration(host, port)
            if not success:
                return False, message

            # If verification passed, attempt full connection
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Attempt connection with retries
            for attempt in range(self._connection_retries):
                try:
                    logger.info(f"Connection attempt {attempt + 1} of {self._connection_retries}")
                    self.ib.connect(host, port, clientId=client_id, readonly=False, timeout=20)

                    if not self.ib.isConnected():
                        if attempt == self._connection_retries - 1:
                            return False, f"Connection attempt {attempt + 1} failed: TWS reports not connected"
                        continue

                    self.connected = True
                    logger.info("Successfully connected to IB")
                    try:
                        contract = Stock('AAPL', 'SMART', 'USD')
                        self.ib.qualifyContracts(contract)
                        return True, "Successfully connected to Interactive Brokers"
                    except Exception as e:
                        return True, f"Connected, but market data access limited: {str(e)}"

                except Exception as e:
                    if attempt == self._connection_retries - 1:
                        return False, f"Connection error: {str(e)}"
                    time.sleep(2)
                    continue

            return False, "All connection attempts failed"

        except Exception as e:
            logger.error(f"Critical error during connection process: {str(e)}")
            return False, f"Critical connection error: {str(e)}"

    def subscribe_market_data(self, symbol):
        """Subscribe to real-time market data or generate simulated data"""
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)

            def on_price_update(trade):
                current_time = datetime.now()
                price = trade.price
                size = trade.size

                if self.current_bar['timestamp'] is None or \
                   (current_time - self.current_bar['timestamp']).seconds >= 60:
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
                    self.current_bar['high'] = max(self.current_bar['high'], price)
                    self.current_bar['low'] = min(self.current_bar['low'], price)
                    self.current_bar['close'] = price
                    self.current_bar['volume'] += size

            self.ib.reqMktData(contract, '', False, False)
            self.ib.pendingTickersEvent += on_price_update
            logger.info(f"Subscribed to market data for {symbol}")
            return True

        except Exception as e:
            logger.error(f"Error subscribing to market data: {str(e)}")
            return False

    def place_order(self, symbol, quantity, action, order_type='MKT'):
        """Place a new order"""
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            if order_type == 'MKT':
                order = MarketOrder(action, quantity)

            trade = self.ib.placeOrder(contract, order)

            order_id = trade.order.orderId
            self.orders[order_id] = {
                'symbol': symbol,
                'quantity': quantity,
                'action': action,
                'status': 'SUBMITTED',
                'timestamp': datetime.now()
            }

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
            return self.price_data[-1].get('close', 0)
        return 0

    def calculate_trade_pnl(self, symbol, quantity, action, current_price):
        """Calculate P&L for a trade"""
        position = self.get_position(symbol)
        if position is None:
            return 0

        avg_cost = position.get('avg_cost', current_price)
        if action == 'BUY':
            return 0
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