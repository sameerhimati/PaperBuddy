import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Model configurations
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash-preview-04-17")  # Cost-effective default
ALTERNATE_MODEL = os.getenv("ALTERNATE_MODEL", "gemini-2.0-flash")  # Stable alternative
PRO_MODEL = os.getenv("PRO_MODEL", "gemini-2.5-pro-preview-03-25")  # High intelligence option
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-1.5-flash")  # Stable fallback

# Default model selection
MODEL_TIER = os.getenv("MODEL_TIER", "default").lower()

# Auto-upgrade to pro settings
AUTO_UPGRADE_TO_PRO = os.getenv("AUTO_UPGRADE_TO_PRO", "False").lower() == "true"
COMPLEXITY_THRESHOLD = float(os.getenv("COMPLEXITY_THRESHOLD", "0.7"))  # 0-1 scale for complexity detection

# Get active model based on selected tier
if MODEL_TIER == "pro":
    ACTIVE_MODEL = PRO_MODEL
elif MODEL_TIER == "alternate":
    ACTIVE_MODEL = ALTERNATE_MODEL
elif MODEL_TIER == "fallback":
    ACTIVE_MODEL = FALLBACK_MODEL
else:  # default
    ACTIVE_MODEL = DEFAULT_MODEL

# Model parameters
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "8192"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
TOP_P = float(os.getenv("TOP_P", "0.95"))
TOP_K = int(os.getenv("TOP_K", "40"))

# Application settings
CACHE_DIR = os.getenv("CACHE_DIR", "cache")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Create cache directory if it doesn't exist
os.makedirs(CACHE_DIR, exist_ok=True)