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
       - TWS (Trader Workstation): Full trading platform
       - IB Gateway: Lighter alternative for API connections
    
    2. Login to TWS/Gateway:
       - Use your Interactive Brokers credentials
       - Enable API connections in settings
    
    3. Configure API Settings:
       - Go to Configure > API > Settings
       - Enable Active X and Socket Clients
       - Set Socket Port to match IB_PORT (default: 7497 for paper trading, 7496 for live)
       
    4. Important Notes:
       - Keep TWS/Gateway running while using this application
       - Paper trading port (7497) is recommended for testing
       - Live trading port (7496) requires extra permissions
    """
