# IB Trading Platform

A professional-grade live trading platform that simplifies Interactive Brokers API interactions through intelligent connection management and advanced diagnostic tools.

## Prerequisites

1. Interactive Brokers Account and Software:
   - An Interactive Brokers account (paper trading account for testing)
   - Trader Workstation (TWS) or IB Gateway installed and running
   - API connections enabled in TWS/Gateway

2. Python Environment:
   - Python 3.11 or higher
   - pip (Python package installer)

## Installation

1. Clone or download this repository to your local machine

2. Install required Python packages:
```bash
pip install ib_insync nest-asyncio pandas plotly streamlit
```

## Configuration

1. Configure TWS/Gateway:
   - Launch TWS/Gateway
   - Go to Edit → Global Configuration → API → Settings
   - Enable "Active X and Socket Clients"
   - Set Socket Port:
     * Paper Trading: 7497
     * Live Trading: 7496
   - Uncheck "Read-Only API"
   - Click Apply and OK

2. Verify the `.streamlit/config.toml` exists with proper settings:
```toml
[server]
headless = true
address = "0.0.0.0"
port = 5000
```

## Running the Application

1. Make sure TWS/Gateway is running and you're logged in

2. Start the trading application:
```bash
streamlit run trading_app/main.py
```

3. Open your web browser and navigate to:
   - `http://localhost:5000`

## Features

- Real-time market data streaming
- Advanced order types support
- Comprehensive trade journaling
- Risk management tools
- Performance analytics
- Paper/Live trading mode support

## Trading Modes

1. Paper Trading (Recommended for testing):
   - Uses port 7497
   - No real money at risk
   - Perfect for learning and testing strategies

2. Live Trading:
   - Uses port 7496
   - Involves real money and real risks
   - Requires funded account and proper permissions
   - Additional safety verifications required

## Troubleshooting

1. Connection Issues:
   - Verify TWS/Gateway is running
   - Check if the correct port is open (7497 for paper, 7496 for live)
   - Ensure API connections are enabled in TWS
   - Try restarting TWS after configuration changes

2. Data Issues:
   - Verify market data subscriptions in TWS
   - Check account permissions for required data

## Safety Notes

- Always start with paper trading mode
- Test thoroughly before switching to live trading
- Keep TWS/Gateway running while using the application
- Monitor positions and risk limits regularly

## Support

For issues and questions, please:
1. Check the troubleshooting section
2. Review TWS API configuration
3. Verify all prerequisites are met

## Disclaimer

Trading involves risk. This application is for educational and testing purposes. Always understand the risks involved before trading with real money.
