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

    # Main content
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
    
    with col2:
        st.title("Position & P&L")
        
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
