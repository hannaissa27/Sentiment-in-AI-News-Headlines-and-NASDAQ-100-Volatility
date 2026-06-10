import os
import urllib3
import requests
import ssl

# --- 1. THE SSL BYPASS (The "Nuclear" Fix) ---
# This forces the 'requests' library (used by Alpaca) to ignore SSL errors
# caused by school/work firewalls.

# Disable the annoying warning messages
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Monkey-patch requests.Session to force verify=False on all connections
old_merge_environment_settings = requests.Session.merge_environment_settings

def merge_environment_settings(self, url, proxies, stream, verify, cert):
    # Regardless of what the library asks for, we force verify=False
    return old_merge_environment_settings(self, url, proxies, stream, False, cert)
                                                                                                        
requests.Session.merge_environment_settings = merge_environment_settings

# Also patch the standard library SSL just in case
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# --- 2. GLOBAL SETTINGS ---
TICKER = "QQQ"
MODEL_NAME = "ProsusAI/finbert"

# --- 3. ALPACA CREDENTIALS ---
# (I have removed your keys from this text for safety. Paste them back here!)
ALPACA_API_KEY = "YOUR_KEY_HERE"
ALPACA_SECRET_KEY = "YOUR_SECRET_HERE"
# Use paper-api for free/sandbox testing
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

# --- 4. SYSTEM SETUP ---
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

# --- 5. PATH HELPERS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def get_input_path(filename="articles.xlsx"):
    return os.path.join(DATA_DIR, filename)

def get_output_path(filename="final_research_results.xlsx"):
    return os.path.join(DATA_DIR, filename)