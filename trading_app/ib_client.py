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
    def __init__(self, simulation_mode=False):
        self.ib = IB()
        self.connected = False
        self.simulation_mode = simulation_mode
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

        # Simulation data
        self._sim_price = 100.0
        self._sim_last_update = datetime.now()

    def _generate_simulated_price(self):
        """Generate simulated price movement"""
        if not self.price_data:
            self._sim_price = 100.0
        else:
            # Random walk with mean reversion
            change = np.random.normal(0, 0.1)
            mean_reversion = (100 - self._sim_price) * 0.1
            self._sim_price += change + mean_reversion

        current_time = datetime.now()

        # Generate OHLC data
        high = self._sim_price * (1 + abs(np.random.normal(0, 0.001)))
        low = self._sim_price * (1 - abs(np.random.normal(0, 0.001)))

        return {
            'open': self.price_data[-1]['close'] if self.price_data else self._sim_price,
            'high': high,
            'low': low,
            'close': self._sim_price,
            'volume': int(np.random.normal(1000, 200)),
            'timestamp': current_time
        }

    def connect(self, host='127.0.0.1', port=7497, client_id=1):
        """Connect to Interactive Brokers TWS or enter simulation mode"""
        try:
            if self.simulation_mode:
                self.connected = True
                logger.info("Started in simulation mode")
                return True, "Connected in simulation mode"

            current_time = time.time()
            if (current_time - self._last_connection_attempt) < self._connection_cooldown:
                return False, "Please wait a few seconds before trying to connect again"

            self._last_connection_attempt = current_time

            if self.connected:
                return True, "Already connected to IB"

            logger.info("Running pre-connection diagnostics...")
            logger.info(f"Testing connection to {host}:{port}")

            if not self._test_port_connection(host, port):
                error_msg = f"""
                TWS/Gateway port {port} is not accessible.
                Please verify:
                1. TWS/Gateway is running and logged in
                2. API settings in TWS:
                   - Edit -> Global Configuration -> API -> Settings
                   - Socket port matches {port}
                   - Enable Active X and Socket Clients is checked
                3. You're using the correct port (7497 for paper trading, 7496 for live)
                4. No firewall is blocking the connection
                """
                logger.error(error_msg)
                return False, error_msg

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

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

                except ConnectionRefusedError:
                    if attempt == self._connection_retries - 1:
                        error_msg = f"""
                        Connection refused at {host}:{port}
                        This usually means:
                        1. TWS/Gateway is not running
                        2. API connections are not enabled
                        3. The port number is incorrect
                        4. TWS is still starting up
                        """
                        return False, error_msg
                    time.sleep(2)
                    continue

                except Exception as e:
                    if attempt == self._connection_retries - 1:
                        return False, f"Connection error: {str(e)}"
                    time.sleep(2)
                    continue

            return False, "All connection attempts failed. Please verify TWS is running and configured correctly"

        except Exception as e:
            logger.error(f"Critical error during connection process: {str(e)}")
            return False, f"Critical connection error: {str(e)}"

    def _test_port_connection(self, host, port):
        """Test if the port is accepting connections"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                logger.info(f"Port {port} is open and accepting connections")
                return True
            else:
                logger.error(f"Port {port} is not accepting connections (Error code: {result})")
                return False
        except Exception as e:
            logger.error(f"Error testing port connection: {str(e)}")
            return False

    def subscribe_market_data(self, symbol):
        """Subscribe to real-time market data or generate simulated data"""
        try:
            if self.simulation_mode:
                # Start with initial simulated data point
                if not self.price_data:
                    self.price_data.append(self._generate_simulated_price())
                return True

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

    def update_simulated_data(self):
        """Update simulated market data"""
        if self.simulation_mode and self.connected:
            current_time = datetime.now()
            if not self.price_data or \
               (current_time - self.price_data[-1]['timestamp']).seconds >= 60:
                self.price_data.append(self._generate_simulated_price())

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