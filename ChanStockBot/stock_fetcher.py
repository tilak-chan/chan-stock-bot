# stock_fetcher.py
from fetch_nse_symbols import fetch_nse_symbols
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time

def get_volatility(stock_ticker, period='1mo'):
    """
    Calculate historical volatility (as percentage)
    
    Parameters:
    - stock_ticker: yfinance.Ticker object
    - period: '1mo', '3mo', '1y' (default: 1 month)
    
    Returns:
    - Volatility percentage (e.g., 15.2 for 15.2%)
    """
    try:
        # Get historical data with retry
        for attempt in range(3):
            try:
                hist = stock_ticker.history(period=period)
                if len(hist) >= 5:  # Sufficient data
                    daily_returns = hist['Close'].pct_change().dropna()
                    volatility_pct = daily_returns.std() * (252 ** 0.5) * 100
                    return round(volatility_pct, 1)
                break
            except Exception as e:
                if attempt == 2:
                    logger.warning(f"Volatility calc failed for {stock_ticker.ticker}: {str(e)}")
                time.sleep(1)
        return 0.0
    except Exception as e:
        logger.error(f"Volatility error for {stock_ticker.ticker}: {str(e)}")
        return 0.0

def process_batch(symbols_batch):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(filter_cheap_stocks, sym): sym for sym in symbols_batch}
        return [f.result() for f in as_completed(futures) if f.result()]
    
def filter_cheap_stocks(symbol):
    """Enhanced stock filter with multiple symbol format attempts"""
    symbol_variants = [
        symbol,
        symbol.replace(".NS", ""),
        symbol.replace(".NS", ".BO"),  # BSE fallback
        symbol.lower()
    ]
    
    for sym in symbol_variants:
        try:
            stock = yf.Ticker(sym)
            info = stock.info
            
            # Skip if essential data missing
            if not all(k in info for k in ['currentPrice', 'trailingPE']):
                continue
                
            price = info['currentPrice']
            if not (10 < price < 100):
                continue
                
            # Flexible fundamental checks
            filters = [
                info.get('trailingPE', float('inf')) < 45,  # More lenient
                info.get('debtToEquity', 2) < 2.0,
                info.get('returnOnEquity', 0) > 0.05,  # Lower threshold
                info.get('currentRatio', 0.8) > 0.6,
                info.get('marketCap', 0) > 300  # Lower mcap threshold
            ]
            
            if sum(filters) >= 2:  # Only need 2/5 conditions
                return {
                    'symbol': symbol,
                    'name': info.get('shortName', symbol),
                    'price': price,
                    'pe': info.get('trailingPE', 'N/A'),
                    'mcap': f"₹{info.get('marketCap', 0)/100:.1f}Cr",
                    'volatility': get_volatility(stock),
                    'liquidity': info.get('averageVolume', 0)
                }
                
        except Exception as e:
            logger.debug(f"Attempt failed for {sym}: {str(e)}")
            continue
            
    return None

def quick_filter(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return (10 < info.get('currentPrice', 0) < 100 
                and info.get('marketCap', 0) > 500)
    except:
        return False
    
def get_cheap_stocks(limit=10):
    try:
        # Get all symbols without slicing
        symbols = fetch_nse_symbols()
        
        if not symbols:
            logger.error("No symbols from NSE, using fallback")
            return [{
                'symbol': 'FALLBACK.NS',
                'name': 'Example Stock',
                'price': 95.50,
                'pe': 12.3,
                'volatility': 25.5,
                'mcap': '₹1,000Cr'
            }]

        # Optimized processing with chunking
        batch_size = 50  # Process in batches to balance speed and memory
        results = []
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Process symbols in batches
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                batch_results = list(filter(None, executor.map(filter_cheap_stocks, batch)))
                results.extend(batch_results)
                
                # Early exit if we already have enough candidates
                if len(results) >= limit * 3:  # Collect 3x required for better sorting
                    break

        # Sort and return best candidates
        if results:
            results.sort(key=lambda x: (
                float(x.get('pe', float('inf'))),
                -x.get('price', 0)  # Prefer higher prices among low PEs
            ))
            return results[:limit]
            
        logger.info("No stocks passed filters")
        return []
        
    except Exception as e:
        logger.critical(f"get_cheap_stocks error: {str(e)}")
        return []

def generate_detailed_analysis(stock):
    # Valuation Assessment
    pe_assessment = (
        "Strongly Undervalued (P/E <6)" if stock['pe'] < 6 else
        "Moderately Undervalued (P/E 6-8)" if stock['pe'] < 8 else
        "Fairly Valued (P/E 8-15)" if stock['pe'] <=15 else
        "Overvalued (P/E 15-25)" if stock['pe'] <=25 else
        "Highly Overvalued (P/E >25)"
    )
    
    # Risk Assessment
    volatility_risk = (
        "Very Low (Excellent for long-term)" if stock['volatility'] < 15 else
        "Low (Good for investors)" if stock['volatility'] < 20 else
        "Moderate (Swing trading potential)" if stock['volatility'] <=35 else
        "High (Speculative)" if stock['volatility'] <=50 else
        "Extreme (Day traders only)"
    )
    
    # Market Cap Classification
    mcap = float(stock['mcap'].replace('₹','').replace('Cr','').strip())
    mcap_assessment = (
        "Mega Cap (₹100,000Cr+)" if mcap > 100000 else
        "Large Cap (₹20,000-100,000Cr)" if mcap > 20000 else
        "Mid Cap (₹5,000-20,000Cr)" if mcap > 5000 else
        "Small Cap (₹500-5,000Cr)" if mcap > 500 else
        "Micro Cap (₹<500Cr)"
    )
    
    # Sector-Specific Advice
    sector_advice = {
        'BANKING': "📌 Rising interest rate environment benefits net interest margins",
        'INFRA': "📌 Government infrastructure push (Budget 2024 allocation: ₹10L Cr)",
        'IT': "📌 Global slowdown concerns but rupee depreciation helps",
        'AUTO': "📌 EV transition creating new opportunities",
        'METALS': "📌 China reopening could boost commodity prices"
    }.get(stock.get('sector','GENERAL'), "📌 Sector outlook neutral")
    
    # Technical Analysis
    technicals = []
    if stock.get('200d_ma'):
        technicals.append(f"200D MA: ₹{stock['200d_ma']:.2f} ({'Above' if stock['price'] > stock['200d_ma'] else 'Below'} key level)")
    if stock.get('rsi'):
        technicals.append(f"RSI: {stock['rsi']} ({'Oversold' if stock['rsi'] <30 else 'Overbought' if stock['rsi']>70 else 'Neutral'})")
    
    # Financial Health
    financials = []
    if stock.get('debt_to_equity'):
        financials.append(f"Debt/Equity: {stock['debt_to_equity']} ({'High' if stock['debt_to_equity']>1 else 'Moderate' if stock['debt_to_equity']>0.5 else 'Low'} leverage)")
    if stock.get('roe'):
        financials.append(f"ROE: {stock['roe']}% ({'Excellent' if stock['roe']>20 else 'Good' if stock['roe']>15 else 'Weak'})")
    
    # Dividend Analysis
    dividend = (
        f"Dividend Yield: {stock.get('dividend_yield',0)}% ({'High' if stock.get('dividend_yield',0) >3 else 'Moderate' if stock.get('dividend_yield',0)>1 else 'Low'})"
        if stock.get('dividend_yield') else ""
    )
    
    return f"""
        🔍 **{stock['name']} ({stock['symbol']}) - Comprehensive Analysis**

        📊 *Valuation*:
        - Current Price: ₹{stock['price']:.2f}
        - P/E Ratio: {stock['pe']} → {pe_assessment}
        - Market Cap: {stock['mcap']} ({mcap_assessment})
        - {dividend}

        📈 *Technical Outlook*:
        {'- ' + '\n- '.join(technicals) if technicals else '⚠️ No technical data available'}

        💼 *Fundamentals*:
        {'- ' + '\n- '.join(financials) if financials else '⚠️ Limited fundamental data'}

        ⚠️ *Risk Assessment*:
        - Volatility: {volatility_risk}
        - Liquidity: {'Excellent' if stock.get('volume',0) > 500000 else 'Adequate' if stock.get('volume',0) > 100000 else 'Thin'} (Avg Vol: {stock.get('volume',0):,})
        - Beta: {stock.get('beta',1.0):.2f} ({'Less' if stock.get('beta',1) <1 else 'More'} volatile than market)

        {sector_advice}

        💡 *Recommendation*:
        {'✅ Strong Buy' if stock['pe'] < 8 and stock['volatility'] < 25 and mcap > 5000 else
        '🔼 Accumulate' if stock['pe'] < 12 and stock['volatility'] < 35 else
        '🔍 Watchlist' if stock['pe'] < 18 else
        '⏸️ Avoid' if stock['volatility'] > 50 else
        '⚠️ High Risk Speculative'}

        🎯 *Price Targets*:
        - Conservative: ₹{stock['price']*0.9:.2f} (-10% stop-loss)
        - Base Case: ₹{stock['price']*1.25:.2f} (+25%)
        - Bull Case: ₹{stock['price']*1.5:.2f} (+50%) if sector outperforms
        """

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)