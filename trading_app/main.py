import os
import sys
import logging
from logger import setup_logger

# Setup logging first
logger = setup_logger()

# Log Python path and environment for debugging
logger.info(f"Python Path: {sys.path}")
logger.info(f"Current working directory: {os.getcwd()}")

try:
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    logger.info("Successfully initialized async support")
except ImportError as e:
    logger.error(f"Failed to import async packages: {str(e)}")
    sys.exit(1)

try:
    import streamlit as st
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime
    import time
    logger.info("Successfully imported main dependencies")
except ImportError as e:
    logger.error(f"Failed to import main dependencies: {str(e)}")
    sys.exit(1)

try:
    from ib_client import IBClient
    from trading_logic import TradingLogic
    from risk_manager import RiskManager
    from config import IBConfig, get_connection_instructions
    logger.info("Successfully imported local modules")
except ImportError as e:
    logger.error(f"Failed to import local modules: {str(e)}")
    sys.exit(1)

# Initialize event loop
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logger.info("Created new event loop")

# Page config
st.set_page_config(
    page_title="IB Trading Algorithm",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if 'initialized' not in st.session_state:
    logger.info("Initializing session state")
    st.session_state.initialized = True
    st.session_state.simulation_mode = True  # Default to simulation mode
    st.session_state.ib_client = IBClient(simulation_mode=True)
    st.session_state.trading_logic = TradingLogic()
    st.session_state.risk_manager = RiskManager()
    st.session_state.show_instructions = False
    st.session_state.last_connection_attempt = 0
    st.session_state.connection_status = {
        'connected': False,
        'last_error': None,
        'last_attempt_time': None
    }
    logger.info("Session state initialized successfully")

def main():
    try:
        # Sidebar
        with st.sidebar:
            st.title("Trading Controls")

            # Mode Selection
            st.subheader("Trading Mode")
            simulation_mode = st.checkbox("Simulation Mode", value=st.session_state.simulation_mode)
            if simulation_mode != st.session_state.simulation_mode:
                st.session_state.simulation_mode = simulation_mode
                st.session_state.ib_client = IBClient(simulation_mode=simulation_mode)
                st.session_state.connection_status['connected'] = False
                st.experimental_rerun()

            # Connection Configuration
            st.subheader("IB Connection Settings")

            # Connection status indicator with detailed state
            conn_status = st.session_state.connection_status
            if conn_status['connected']:
                st.success("Connected to Interactive Brokers")
            else:
                st.warning("Not connected to Interactive Brokers")
                if conn_status['last_error']:
                    st.error(f"Last error: {conn_status['last_error']}")

            host = st.text_input("TWS/Gateway Host", value="127.0.0.1")
            port = st.number_input("TWS/Gateway Port", value=7497)
            client_id = st.number_input("Client ID", value=1)
            is_paper_trading = st.checkbox("Paper Trading Mode", value=True)

            # Save configuration button
            if st.button("Save Configuration"):
                try:
                    os.environ['IB_HOST'] = host
                    os.environ['IB_PORT'] = str(port)
                    os.environ['IB_CLIENT_ID'] = str(client_id)
                    os.environ['IB_PAPER_TRADING'] = str(is_paper_trading).lower()
                    st.success("Configuration saved!")
                    logger.info("Trading configuration updated")
                except Exception as e:
                    logger.error(f"Failed to save configuration: {str(e)}")
                    st.error("Failed to save configuration")

            # Connection control with improved error handling
            if st.button("Connect to IB"):
                current_time = time.time()
                if (current_time - st.session_state.last_connection_attempt) < 5:
                    st.error("Please wait a few seconds before trying to connect again")
                else:
                    st.session_state.last_connection_attempt = current_time
                    config = IBConfig.from_env()
                    with st.spinner("Connecting to Interactive Brokers..."):
                        try:
                            success, message = st.session_state.ib_client.connect(
                                host=config.host,
                                port=config.port,
                                client_id=config.client_id
                            )
                            if success:
                                st.session_state.connection_status['connected'] = True
                                st.session_state.connection_status['last_error'] = None
                                st.success(message)
                                logger.info("Successfully connected to Interactive Brokers")
                            else:
                                st.session_state.connection_status['last_error'] = message
                                st.error(message)
                                st.info("Click 'Show Connection Instructions' for help")
                                logger.error("Failed to establish IB connection")
                        except Exception as e:
                            error_msg = f"Connection error: {str(e)}"
                            st.session_state.connection_status['last_error'] = error_msg
                            st.error(error_msg)
                            logger.error(f"Exception during connection: {str(e)}")

            # Show/Hide Instructions
            if st.button("Show Connection Instructions"):
                st.session_state.show_instructions = not st.session_state.show_instructions

            if st.session_state.show_instructions:
                st.markdown(get_connection_instructions())

            # Trading parameters
            st.subheader("Trading Parameters")
            symbol = st.text_input("Symbol", value="AAPL")
            quantity = st.number_input("Quantity", min_value=1, value=100)

            # Risk parameters
            st.subheader("Risk Parameters")
            max_position = st.number_input("Max Position Size", min_value=1, value=1000)
            stop_loss_pct = st.number_input("Stop Loss %", min_value=0.1, value=2.0)

            # Trading controls
            if st.button("Start Trading"):
                if not st.session_state.ib_client.connected:
                    st.error("Please connect to Interactive Brokers first!")
                else:
                    st.session_state.trading_logic.start_trading(symbol, quantity)
                    st.success(f"Started trading {symbol}")

            if st.button("Stop Trading"):
                st.session_state.trading_logic.stop_trading()
                st.info("Trading stopped")

        # Update simulated data if in simulation mode
        if st.session_state.simulation_mode and st.session_state.ib_client.connected:
            st.session_state.ib_client.update_simulated_data()

        # Main content area
        col1, col2 = st.columns([2, 1])

        with col1:
            st.title("Market Data & Charts")

            # Price chart
            fig = go.Figure()
            if hasattr(st.session_state.ib_client, 'price_data') and st.session_state.ib_client.price_data:
                df = pd.DataFrame(st.session_state.ib_client.price_data)
                if not df.empty:
                    fig.add_trace(go.Candlestick(
                        x=df['timestamp'],
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close']
                    ))

            fig.update_layout(
                title="Price Chart",
                yaxis_title="Price",
                xaxis_title="Time"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Trade Journal
            st.title("Trade Journal")
            trade_history = st.session_state.ib_client.get_trade_history()
            if not isinstance(trade_history, pd.DataFrame):
                trade_history = pd.DataFrame()

            if not trade_history.empty:
                st.dataframe(
                    trade_history.sort_values('timestamp', ascending=False),
                    use_container_width=True
                )

                # Export buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Export to CSV"):
                        filename = st.session_state.ib_client.export_trade_journal('csv')
                        if filename:
                            st.success(f"Trade journal exported to {filename}")
                with col2:
                    if st.button("Export to JSON"):
                        filename = st.session_state.ib_client.export_trade_journal('json')
                        if filename:
                            st.success(f"Trade journal exported to {filename}")

        with col2:
            st.title("Performance Metrics")

            # Get metrics
            metrics = st.session_state.ib_client.get_trade_metrics()

            # Display metrics
            st.metric("Total P&L", f"${metrics.get('total_pnl', 0):,.2f}")
            st.metric("Win Rate", f"{metrics.get('win_rate', 0)*100:.1f}%")
            st.metric("Total Trades", metrics.get('total_trades', 0))

            # Detailed metrics
            st.subheader("Detailed Metrics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Winning Trades", metrics.get('winning_trades', 0))
                st.metric("Avg Win", f"${metrics.get('avg_win', 0):,.2f}")
            with col2:
                st.metric("Losing Trades", metrics.get('losing_trades', 0))
                st.metric("Avg Loss", f"${metrics.get('avg_loss', 0):,.2f}")

            # Current position
            st.subheader("Current Positions")
            position_df = st.session_state.ib_client.get_positions()
            if not isinstance(position_df, pd.DataFrame):
                position_df = pd.DataFrame()
            st.dataframe(position_df)

            # P&L metrics
            st.metric("Daily P&L", f"${st.session_state.ib_client.get_daily_pnl():,.2f}")
            st.metric("Total P&L", f"${st.session_state.ib_client.get_total_pnl():,.2f}")

        # Order book and execution
        st.title("Order Book")
        orders_df = st.session_state.ib_client.get_orders()
        if not isinstance(orders_df, pd.DataFrame):
            orders_df = pd.DataFrame()
        st.dataframe(orders_df)

        # Trade log
        st.title("Trade Log")
        trades_df = st.session_state.ib_client.get_trades()
        if not isinstance(trades_df, pd.DataFrame):
            trades_df = pd.DataFrame()
        st.dataframe(trades_df)

    except Exception as e:
        logger.error(f"Critical error in main function: {str(e)}")
        st.error("An unexpected error occurred. Please check the logs for details.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application failed to start: {str(e)}")
        st.error("Failed to start the application. Please check the logs.")