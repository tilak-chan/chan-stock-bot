import requests
from bs4 import BeautifulSoup

def get_company_summary(symbol):
    try:
        clean_symbol = symbol.replace('.NS', '')
        url = f"https://www.screener.in/company/{clean_symbol}/"
        
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml'
        }, timeout=10)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract description
        description = (soup.find('p', class_='body-text') or 
                      soup.find('div', class_='company-description')).get_text(strip=True)
        
        # Extract key metrics
        metrics = {}
        for row in soup.select('.company-ratios li'):
            if ':' in row.text:
                key, val = row.text.split(':', 1)
                metrics[key.strip()] = val.strip()
                
        return {
            "description": description[:200] + "..." if description else "No description",
            "P/E": metrics.get("Stock P/E", "N/A"),
            "ROE": metrics.get("ROE", "N/A"),
            "Profit Growth": metrics.get("Profit growth", "N/A")
        }
        
    except Exception as e:
        print(f"Screener Error for {symbol}: {str(e)}")
        return {
            "description": "Data unavailable",
            "P/E": "N/A",
            "ROE": "N/A",
            "Profit Growth": "N/A"
        }