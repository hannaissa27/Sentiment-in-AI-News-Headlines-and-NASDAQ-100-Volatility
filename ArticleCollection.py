import pandas as pd
import requests
import urllib.parse
from datetime import datetime, time as datetime_time, timedelta
import time as time_module
import warnings
from dateutil import parser, tz
import urllib3
import re

# --- 1. SILENCE WARNINGS ---
warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 2. CONFIGURATION & KEYS ---
NYT_API_KEY = "replace"
GUARDIAN_API_KEY = "replace"

# TOP 5 KEYWORDS
KEYWORDS = ["Generative AI", "ChatGPT", "OpenAI", "A.I.", "Artificial Intelligence"]

# Regex to STRICTLY check if the keyword is in the headline
escaped_kws = [re.escape(kw) for kw in KEYWORDS]
KEYWORD_PATTERN = re.compile(r'(?<![A-Za-z])(?:' + '|'.join(escaped_kws) + r')(?![A-Za-z])', re.IGNORECASE)

def check_headline_strict(headline):
    if not headline: return False
    return bool(KEYWORD_PATTERN.search(headline))

# Generate Year/Month Data Structure
MONTHS_DATA = []
curr = datetime(2022, 11, 1)
end_limit = datetime.now()
while curr <= end_limit:
    next_month = curr.replace(month=curr.month+1) if curr.month < 12 else curr.replace(year=curr.year+1, month=1)
    last_day = next_month - timedelta(days=1)
    MONTHS_DATA.append({
        'year': curr.year,
        'month': curr.month,
        'start': curr.strftime("%Y-%m-%d"),
        'end': min(last_day, end_limit).strftime("%Y-%m-%d")
    })
    curr = next_month

START_DATE = datetime(2022, 11, 1)
END_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

NYSE_HOLIDAYS = {
    '2022-12-26', '2023-01-02', '2023-01-16', '2023-02-20', '2023-04-07', 
    '2023-05-29', '2023-06-19', '2023-07-04', '2023-09-04', '2023-11-23', 
    '2023-12-25', '2024-01-01', '2024-01-15', '2024-02-19', '2024-03-29', 
    '2024-05-27', '2024-06-19', '2024-07-04', '2024-09-02', '2024-11-28', 
    '2024-12-25', '2025-01-01', '2025-01-20', '2025-02-17', '2025-04-18', 
    '2025-05-26', '2025-06-19', '2025-07-04', '2025-09-01', '2025-11-27', 
    '2025-12-25', '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', 
    '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07', '2026-11-26', 
    '2026-12-25'
}

def is_market_hours(date_str):
    try:
        dt_obj = parser.parse(date_str)
        dt_nyc = dt_obj.astimezone(tz.gettz('America/New_York'))
        d_str = dt_nyc.strftime("%Y-%m-%d")
        if not (START_DATE <= dt_nyc.replace(tzinfo=None) <= END_DATE) or dt_nyc.weekday() > 4 or d_str in NYSE_HOLIDAYS:
            return False, None, None
        if datetime_time(9, 30) <= dt_nyc.time() <= datetime_time(16, 0):
            return True, d_str, dt_nyc.strftime("%H:%M:%S")
        return False, None, None
    except: return False, None, None

# --- 3. MAIN EXECUTION ---
if __name__ == "__main__":
    all_data = []
    print("---STARTING---")

    for m_data in MONTHS_DATA:
        year = m_data['year']
        month = m_data['month']
        start = m_data['start']
        end = m_data['end']
        
        print(f"\n[MONTH] {year}-{month:02d}")

        # ==========================================
        # PHASE 1: THE GUARDIAN (Dynamic Page Scan)
        # ==========================================
        print("  > Guardian (Dynamic Search):", end=" ", flush=True)
        g_month_count = 0
        
        for kw in KEYWORDS:
            q = urllib.parse.quote(kw)
            url_g_base = f"https://content.guardianapis.com/search?q={q}&from-date={start}&to-date={end}&page-size=50&api-key={GUARDIAN_API_KEY}"
            
            try:
                res_g = requests.get(url_g_base, timeout=10).json().get('response', {})
                total_pages_g = res_g.get('pages', 0)
                
                for p in range(1, total_pages_g + 1):
                    time_module.sleep(1.0) # Guardian rate limit safety
                    items = requests.get(f"{url_g_base}&page={p}", timeout=10).json().get('response', {}).get('results', [])
                    for item in items:
                        headline = item.get('webTitle', '').split(' | ')[0]
                        if check_headline_strict(headline):
                            ok, d, t = is_market_hours(item.get('webPublicationDate'))
                            if ok:
                                all_data.append({'Headline': headline, 'Date': d, 'Time': t, 'Source': 'The Guardian', 'Region': 'Europe'})
                                g_month_count += 1
            except Exception as e:
                pass # Silently pass so an error on one keyword doesn't ruin the whole month
                
        print(f"{g_month_count} kept")

        # ==========================================
        # PHASE 2: NYT (Full Monthly Archive Dump)
        # ==========================================
        print("  > NYT (Archive Dump):       ", end=" ", flush=True)
        url_n = f"https://api.nytimes.com/svc/archive/v1/{year}/{month}.json?api-key={NYT_API_KEY}"
        
        try:
            time_module.sleep(12.5) # Vital for NYT rate limit
            res_n = requests.get(url_n, timeout=20)
            
            if res_n.status_code == 200:
                docs = res_n.json().get('response', {}).get('docs', [])
                n_count = 0
                for doc in docs:
                    headline = doc.get('headline', {}).get('main', '')
                    if check_headline_strict(headline):
                        ok, d, t = is_market_hours(doc.get('pub_date'))
                        if ok:
                            all_data.append({'Headline': headline, 'Date': d, 'Time': t, 'Source': 'The New York Times', 'Region': 'USA'})
                            n_count += 1
                print(f"{n_count} kept")
            elif res_n.status_code == 429:
                print(f"Error 429: Rate Limit Hit. Stopping.")
                break
            else:
                print(f"Error {res_n.status_code}")
        except Exception as e:
            print(f"Connection Error")

    # --- FINAL EXPORT ---
    df = pd.DataFrame(all_data)
    if not df.empty:
        df = df.drop_duplicates(subset=['Headline'])
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by=['Date', 'Time'], ascending=[False, False])
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        df.to_excel('Ultimate_Combined_Dataset.xlsx', index=False)
        
        print("\n======================================")
        print(f" COLLECTION COMPLETE")
        print(f"Total Unique Articles: {len(df)}")
        print(f"USA (NYT): {len(df[df['Region']=='USA'])}")
        print(f"Europe (Guardian): {len(df[df['Region']=='Europe'])}")
        print("======================================")
    else:
        print("\n No articles collected.")
