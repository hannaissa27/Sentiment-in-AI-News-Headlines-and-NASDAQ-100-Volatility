import datetime
import pandas as pd
import numpy as np
from dateutil import tz

def force_float(x):
    """Forces any data type into a simple float."""
    try:
        if isinstance(x, (float, int)): return float(x)
        if hasattr(x, 'item'): return float(x.item())
        if hasattr(x, 'values'): x = x.values
        if hasattr(x, '__len__') and len(x) > 0: return force_float(x[0])
        return float(x)
    except:
        return 0.0

def combine_date_time(date_val, time_val):
    """
    Safely merges Date and Time columns.
    Handles strings, Excel objects, and Pandas Timestamps.
    """
    try:
        # 1. Handle Date (Convert to date object)
        d = pd.to_datetime(date_val).date()
        
        # 2. Handle Time (The Tricky Part)
        t = datetime.time(9, 30) # Default
        
        # Check if it is ALREADY a time object (Excel does this)
        if isinstance(time_val, datetime.time):
            t = time_val
        elif pd.notnull(time_val):
            # Try converting string to time
            try:
                t = pd.to_datetime(str(time_val)).time()
            except:
                pass # Stick with default if conversion fails
            
        # 3. Combine into a "Naive" Datetime
        dt_naive = datetime.datetime.combine(d, t)
        
        # 4. Add Timezone Info (New York Time)
        nyc_zone = tz.gettz('America/New_York')
        if nyc_zone is None:
            # Fallback if system timezone database is missing
            # We assume offset -5 (EST) manually just to keep it running
            nyc_zone = datetime.timezone(datetime.timedelta(hours=-5))
            
        dt_nyc = dt_naive.replace(tzinfo=nyc_zone)
        
        # 5. Convert to UTC (Required by Alpaca)
        return dt_nyc.astimezone(datetime.timezone.utc)
        
    except Exception as e:
        # DEBUG PRINT: This will show you exactly what is failing in the console
        print(f" [!] Date Error: {e} | Inputs: {date_val} (Type: {type(date_val)}) / {time_val} (Type: {type(time_val)})")
        return None

def format_for_excel(df):
    """Cleans up columns for the final report."""
    # Ensure we don't crash on empty columns
    if 'Date' in df.columns:
        df['Date'] = df['Date'].apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d') if pd.notnull(x) else x)
    if 'Time' in df.columns:
        df['Time'] = df['Time'].apply(lambda x: str(x).split(' ')[-1] if pd.notnull(x) else x)
    return df