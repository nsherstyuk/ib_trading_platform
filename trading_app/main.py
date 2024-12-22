import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
from ib_client import IBClient
from trading_logic import TradingLogic
from risk_manager import RiskManager
from logger import setup_logger

# Setup logging
logger = setup_logger()

# Page config
st.set_page_config(
    page_title="IB Trading Algorithm",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if 'ib_client' not in st.session_state:
    st.session_state.ib_client = IBClient()
if 'trading_logic' not in st.session_state:
    st.session_state.trading_logic = TradingLogic()
if 'risk_manager' not in st.session_state:
    st.session_state.risk_manager = RiskManager()

def main():
    # Sidebar
    with st.sidebar:
        st.title("Trading Controls")
        
        # Connection status
        if st.button("Connect to IB"):
            st.session_state.ib_client.connect()
        
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
            st.session_state.trading_logic.start_trading(symbol, quantity)
        if st.button("Stop Trading"):
            st.session_state.trading_logic.stop_trading()

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.title("Market Data & Charts")

        # Price chart
        fig = go.Figure()
        if hasattr(st.session_state.ib_client, 'price_data'):
            df = pd.DataFrame(st.session_state.ib_client.price_data)
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
        position_df = st.session_state.ib_client.get_positions()
        st.dataframe(position_df)
        
        # P&L metrics
        st.metric("Daily P&L", f"${st.session_state.ib_client.get_daily_pnl():,.2f}")
        st.metric("Total P&L", f"${st.session_state.ib_client.get_total_pnl():,.2f}")

    # Order book and execution
    st.title("Order Book")
    orders_df = st.session_state.ib_client.get_orders()
    st.dataframe(orders_df)
    
    # Trade log
    st.title("Trade Log")
    trades_df = st.session_state.ib_client.get_trades()
    st.dataframe(trades_df)

if __name__ == "__main__":
    main()