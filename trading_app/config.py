import os
from dataclasses import dataclass
from logger import setup_logger

logger = setup_logger()

@dataclass
class IBConfig:
    host: str = "127.0.0.1"
    port: int = 7497  # Default TWS paper trading port
    client_id: int = 1
    is_paper_trading: bool = True

    @classmethod
    def from_env(cls):
        """Load configuration from environment variables"""
        is_paper = os.getenv('IB_PAPER_TRADING', 'true').lower() == 'true'
        port = 7497 if is_paper else 7496  # Auto-select port based on trading mode

        return cls(
            host=os.getenv('IB_HOST', '127.0.0.1'),
            port=int(os.getenv('IB_PORT', str(port))),
            client_id=int(os.getenv('IB_CLIENT_ID', '1')),
            is_paper_trading=is_paper
        )

    def get_trading_mode_warning(self):
        """Get appropriate warning message based on trading mode"""
        if not self.is_paper_trading:
            return """
            ⚠️ LIVE TRADING MODE ACTIVATED ⚠️

            You are connecting to LIVE TRADING (Port 7496).
            This involves REAL MONEY and REAL RISKS.

            Please ensure:
            1. You have a funded live trading account
            2. You have necessary trading permissions
            3. You understand the risks involved
            4. Your TWS is configured for live trading

            To switch back to paper trading:
            1. Check "Paper Trading Mode" in settings
            2. Restart the connection
            """
        return """
        📝 Paper Trading Mode (Port 7497)

        You are in paper trading mode (simulation).
        No real money is at risk.
        """

def get_connection_instructions():
    return """
    To connect to Interactive Brokers:

    1. Download and Install TWS or IB Gateway:
       - TWS (Trader Workstation): Download from Interactive Brokers website
       - Paper Trading account recommended for testing
       - Install and run the application

    2. Login to TWS/Gateway:
       - Launch TWS/Gateway
       - Login with your Interactive Brokers credentials
       - Wait for the application to fully load

    3. Configure API Settings:
       - Go to Edit → Global Configuration → API → Settings
       - Check "Enable ActiveX and Socket Clients"
       - Set Socket Port:
         * Paper Trading: 7497
         * Live Trading: 7496
       - Uncheck "Read-Only API"
       - Click Apply and OK

    4. Connection Troubleshooting:
       - Ensure TWS/Gateway is running and logged in
       - Check if port (7497/7496) is not blocked by firewall
       - Try restarting TWS if issues persist
       - For live trading, verify account permissions

    5. Important Notes:
       - Keep TWS/Gateway running while using this application
       - Paper trading (7497) is recommended for testing
       - Live trading (7496) requires permissions and funded account
       - TWS must be running before connecting the application
    """