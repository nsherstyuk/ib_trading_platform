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
        return cls(
            host=os.getenv('IB_HOST', '127.0.0.1'),
            port=int(os.getenv('IB_PORT', '7497')),
            client_id=int(os.getenv('IB_CLIENT_ID', '1')),
            is_paper_trading=os.getenv('IB_PAPER_TRADING', 'true').lower() == 'true'
        )

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
       - Set Socket Port to 7497 (for paper trading)
       - Uncheck "Read-Only API"
       - Click Apply and OK

    4. Connection Troubleshooting:
       - Ensure TWS/Gateway is running and logged in
       - Check if port 7497 is not blocked by firewall
       - Verify the correct port number (7497 for paper, 7496 for live)
       - Try restarting TWS if issues persist

    5. Important Notes:
       - Keep TWS/Gateway running while using this application
       - Paper trading port (7497) is recommended for testing
       - Live trading port (7496) requires extra permissions
       - TWS must be running before connecting the application
    """