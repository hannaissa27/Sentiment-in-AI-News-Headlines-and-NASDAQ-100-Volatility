import pandas as pd
import numpy as np
from scipy.stats import pearsonr

from .config import TICKER, MODEL_NAME
from .utils import combine_date_time, format_for_excel
from .sentiment import SentimentEngine
from .market import MarketEngine

class ResearchPipeline:
    def __init__(self):
        self.sentiment_engine = SentimentEngine(MODEL_NAME)
        self.market_engine = MarketEngine(TICKER)

    def _calculate_accuracy(self, df):
        """
        Checks accuracy based on the 60-minute POST-news trend.
        Logic: Did the price move in the direction of the sentiment?
        """
        acc_list = []
        for _, row in df.iterrows():
            sent = row.get('Sentiment_Score', 0)
            # We look at the 60m POST-news price change
            move = row.get('Chg_60m_POST', 0)
            
            # If Sentiment is Positive (> 0.05) and Price went Up (> 0) -> Correct
            if (sent > 0.05 and move > 0): acc_list.append(1)
            # If Sentiment is Negative (< -0.05) and Price went Down (< 0) -> Correct
            elif (sent < -0.05 and move < 0): acc_list.append(1)
            # If Sentiment Positive but Price Down -> Incorrect
            elif (sent > 0.05 and move < 0): acc_list.append(0)
            # If Sentiment Negative but Price Up -> Incorrect
            elif (sent < -0.05 and move > 0): acc_list.append(0)
            # Neutral sentiment or flat price -> Ignore
            else: acc_list.append(None)
        return acc_list

    def run(self, input_file, output_file):
        print(f"--- STARTING MULTI-TIMEFRAME PIPELINE ({TICKER}) ---")
        
        # 1. LOAD
        try:
            df = pd.read_excel(input_file)
            print(f"Loaded {len(df)} articles.")
        except Exception as e:
            print(f"ERROR: Could not load {input_file}\n{e}")
            return

        # 2. SENTIMENT
        print("Step 1/3: Analyzing Sentiment...")
        df['Sentiment_Score'] = [self.sentiment_engine.get_score(txt) for txt in df['Headline']]

        # 3. MARKET DATA
        print("Step 2/3: Fetching Data (Pre/Post Analysis)...")
        market_data_list = []
        total = len(df)
        
        for idx, row in df.iterrows():
            if idx % 10 == 0: print(f"Processing {idx}/{total}...", end='\r')
            
            # Combine Date/Time to get the Article Timestamp
            dt = combine_date_time(row.get('Date'), row.get('Time'))
            
            # Default: 16 zeros (4 timeframes * 2 periods * 2 metrics)
            metrics = [0.0] * 16 
            
            if dt:
                # Fetch massive block around the time
                bars = self.market_engine.fetch_data(dt)
                if bars:
                    # Pass the article time (dt) so market.py knows where to split Pre/Post
                    metrics = self.market_engine.calculate_metrics(bars, dt)
            
            market_data_list.append(metrics)
        
        # Unpack results into DataFrame columns
        market_arr = np.array(market_data_list)
        
        # --- 1 Minute Window ---
        df['Vol_1m_PRE'] = market_arr[:, 0]
        df['Chg_1m_PRE'] = market_arr[:, 1]
        df['Vol_1m_POST'] = market_arr[:, 2]
        df['Chg_1m_POST'] = market_arr[:, 3]
        
        # --- 5 Minute Window ---
        df['Vol_5m_PRE'] = market_arr[:, 4]
        df['Chg_5m_PRE'] = market_arr[:, 5]
        df['Vol_5m_POST'] = market_arr[:, 6]
        df['Chg_5m_POST'] = market_arr[:, 7]
        
        # --- 30 Minute Window ---
        df['Vol_30m_PRE'] = market_arr[:, 8]
        df['Chg_30m_PRE'] = market_arr[:, 9]
        df['Vol_30m_POST'] = market_arr[:, 10]
        df['Chg_30m_POST'] = market_arr[:, 11]
        
        # --- 60 Minute Window ---
        df['Vol_60m_PRE'] = market_arr[:, 12]
        df['Chg_60m_PRE'] = market_arr[:, 13]
        df['Vol_60m_POST'] = market_arr[:, 14]
        df['Chg_60m_POST'] = market_arr[:, 15]

        # 4. STATS & SAVE
        print("\nStep 3/3: Finalizing...")
        df['AI_Correct'] = self._calculate_accuracy(df)
        
        # Quick Correlation Check (Sentiment vs 60m Post-News Price)
        # We check rows where we actually found data (Vol > 0)
        valid = df[df['Vol_60m_POST'] > 0]
        if len(valid) > 1:
            r, p = pearsonr(valid['Sentiment_Score'], valid['Chg_60m_POST'])
            print(f"\nCorrelation (Sentiment vs 60m Post Price): r={r:.4f} (p={p:.4f})")
            
        # Save
        df = format_for_excel(df)
        df.to_excel(output_file, index=False)
        print(f"Saved: {output_file}")