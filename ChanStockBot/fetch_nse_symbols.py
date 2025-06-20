import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_nse_cookies():
    """Establish session cookies by visiting main pages"""
    session = requests.Session()
    base_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # Step 1: Visit homepage to set initial cookies
    session.get("https://www.nseindia.com", headers=base_headers)
    time.sleep(1)
    
    # Step 2: Visit market data page to set additional cookies
    session.get("https://www.nseindia.com/market-data/live-equity-market", headers=base_headers)
    time.sleep(1)
    
    return session

def fetch_nse_symbols():
    try:
        # Establish authenticated session
        session = get_nse_cookies()
        
        # API URL (updated format as of 2024)
        api_url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20TOTAL%20MARKET"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/market-data/live-equity-market",
            "X-Requested-With": "XMLHttpRequest",
        }
        
        # Get JSON data (modern NSE API returns JSON, not CSV directly)
        response = session.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract symbols from JSON structure
            symbols = [
                f"{item['symbol']}.NS"
                for item in data['data']
                if isinstance(item.get('symbol'), str)
            ]
            return symbols
            
        else:
            print(f"API Failed (Status {response.status_code})")
            print("Response:", response.text[:500])
            return []
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return []


