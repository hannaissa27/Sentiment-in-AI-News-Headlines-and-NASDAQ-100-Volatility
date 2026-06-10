import pandas as pd
import requests
import datetime
from .config import ALPACA_API_KEY, ALPACA_SECRET_KEY
from .utils import force_float

class MarketEngine:
    def __init__(self, ticker):
        self.ticker = ticker
        self.base_url = "https://data.alpaca.markets/v2/stocks/bars"
        
        self.headers = {
           
            "APCA-API-KEY-ID": "replace you rid with this",
            "APCA-API-SECRET-KEY":"replace your id with this",


            
            "accept": "application/json"
        }

    def fetch_data(self, utc_datetime):
        """
        Fetches a large block of data surrounding the article time
        (65 minutes BEFORE -> 65 minutes AFTER).
        """
        try:
            if not utc_datetime: return None
            
            # We need history BEFORE the article to calculate "Pre-News" volatility.
            # We grab 65 mins back and 65 mins forward to cover the largest window (60m).
            start_dt = utc_datetime - datetime.timedelta(minutes=65)
            # We add a buffer to the end just in case
            end_dt = utc_datetime + datetime.timedelta(minutes=65) 
            
            start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            print(f"[DEBUG] Fetching Window: {start_str} -> {end_str}...", end=" ")
            
            params = {
                "symbols": self.ticker,
                "timeframe": "1Min",
                "start": start_str,
                "end": end_str,
                "limit": 1000, 
                "feed": "iex" 
            }
            
            response = requests.get(
                self.base_url, 
                headers=self.headers, 
                params=params, 
                verify=False
            )
            
            if response.status_code != 200:
                print(f"FAILED (Status {response.status_code})")
                return None
                
            data = response.json()
            bars = data.get('bars', {}).get(self.ticker, [])
            
            if not bars:
                print("EMPTY")
                return None
                
            print(f"SUCCESS! ({len(bars)} bars)")
            
            # Helper Class for Bar Data
            class BarObj:
                def __init__(self, b):
                    self.t = pd.to_datetime(b['t']) # Keep time for filtering
                    self.high = b['h']
                    self.low = b['l']
                    self.open = b['o']
                    self.close = b['c']
            
            return [BarObj(b) for b in bars]

        except Exception as e:
            print(f"ERROR: {e}")
            return None

    def calculate_metrics(self, bars_list, article_utc_time):
        """
        Calculates Volatility & Price Change for BEFORE and AFTER windows.
        Timeframes: 1m, 5m, 30m, 60m.
        """
        if not bars_list:
            return [0.0] * 16 # 4 timeframes * 2 periods (pre/post) * 2 metrics (vol/chg)

        # Convert article time to same timezone-aware format as bars
        target_time = pd.to_datetime(article_utc_time)

        # We need 4 timeframes
        windows_minutes = [1, 5, 30, 60]
        results = []

        for mins in windows_minutes:
            # --- 1. PRE-NEWS WINDOW (Before) ---
            # From (Target - X mins) to Target
            start_pre = target_time - datetime.timedelta(minutes=mins)
            pre_bars = [b for b in bars_list if start_pre <= b.t < target_time]
            
            results.extend(self._calc_window_stats(pre_bars))

            # --- 2. POST-NEWS WINDOW (After) ---
            # From Target to (Target + X mins)
            end_post = target_time + datetime.timedelta(minutes=mins)
            post_bars = [b for b in bars_list if target_time <= b.t < end_post]
            
            results.extend(self._calc_window_stats(post_bars))

        # Returns list of 16 values:
        # [1m_Pre_Vol, 1m_Pre_Chg, 1m_Post_Vol, 1m_Post_Chg, 5m_Pre..., 5m_Post..., etc.]
        return results

    def _calc_window_stats(self, slice_data):
        """Helper to crunch numbers for a specific slice of bars."""
        if not slice_data:
            return [0.0, 0.0] # Volatility, Price Change
            
        try:
            base_open = slice_data[0].open
            high_val = max([b.high for b in slice_data])
            low_val = min([b.low for b in slice_data])
            close_val = slice_data[-1].close
            
            # Volatility: (High - Low) / Open
            vol = ((high_val - low_val) / base_open) * 100.0
            
            # Price Change: (Close - Open) / Open
            chg = ((close_val - base_open) / base_open) * 100.0
            
            return [force_float(vol), force_float(chg)]
        except:
            return [0.0, 0.0]
