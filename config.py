import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Application settings
APP_NAME = "PaperBuddy"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# API configuration
API_KEY = os.getenv("GOOGLE_API_KEY")

# Model definitions
MODEL_DEFINITIONS = {
    # Main analysis models
    "default": {
        "name": "Default Quality",
        "model": os.getenv("DEFAULT_MODEL", "gemini-2.5-flash-preview-04-17"),
        "description": "Good balance of quality and speed"
    },
    "pro": {
        "name": "Pro Quality",
        "model": os.getenv("PRO_MODEL", "gemini-2.5-flash-preview-04-17"),
        "description": "Highest quality analysis (requires API key)",
        "requires_api_key": True
    },
    "alternate": {
        "name": "Balanced",
        "model": os.getenv("ALTERNATE_MODEL", "gemini-2.0-flash"),
        "description": "Reliable fallback option"
    },
    "fallback": {
        "name": "Fast",
        "model": os.getenv("FALLBACK_MODEL", "gemini-1.5-flash"),
        "description": "Fastest analysis with basic quality"
    },
    
    # Utility models for specific tasks
    "field_tags": {
        "name": "Field Tags Extractor",
        "model": "gemini-1.5-flash",
        "description": "Extracts research field tags",
        "temperature": 0.1,
        "max_output_tokens": 1024
    },
    "terminology": {
        "name": "Terminology Extractor",
        "model": "gemini-1.5-flash",
        "description": "Extracts key terminology and definitions",
        "temperature": 0.1,
        "max_output_tokens": 2048
    },
    "metadata": {
        "name": "Metadata Extractor",
        "model": "gemini-1.5-flash",
        "description": "Extracts paper metadata",
        "temperature": 0.1,
        "max_output_tokens": 1024
    }
}

# Analysis configurations
ANALYSIS_TYPES = {
    "comprehensive": {
        "title": "Comprehensive Analysis",
        "description": "Complete academic review with summary, innovations, techniques, and limitations",
        "icon": "📊",
        "for": "Researchers and academics",
        "model": "default",
        "temperature": 0.2,
        "max_output_tokens": 8192,
        "top_p": 0.95,
        "top_k": 40,
        "max_pages": 15,
        "try_pdf_input": True,
        "auto_analyze": True
    },
    "quick_summary": {
        "title": "Quick Summary",
        "description": "Brief overview with key points in bullet format",
        "icon": "⏱️",
        "for": "Busy readers needing essentials",
        "model": "default",
        "temperature": 0.1,
        "max_output_tokens": 4096,
        "top_p": 0.95,
        "top_k": 40,
        "max_pages": 8,
        "try_pdf_input": True,
        "auto_analyze": True
    },
    "technical": {
        "title": "Technical Deep Dive",
        "description": "Detailed analysis of algorithms, methods, and implementation details",
        "icon": "🔬",
        "for": "Engineers and developers",
        "model": "default",
        "temperature": 0.2,
        "max_output_tokens": 8192,
        "top_p": 0.95,
        "top_k": 40,
        "max_pages": 15,
        "try_pdf_input": True,
        "auto_analyze": True
    },
    "practical": {
        "title": "Practical Applications",
        "description": "Focus on real-world use cases and industry relevance",
        "icon": "🛠️",
        "for": "Industry professionals",
        "model": "default",
        "temperature": 0.2,
        "max_output_tokens": 6144,
        "top_p": 0.95,
        "top_k": 40,
        "max_pages": 12,
        "try_pdf_input": True,
        "auto_analyze": True
    },
    "simplified": {
        "title": "Explain Like I'm 5",
        "description": "Simplified explanation using everyday language and analogies",
        "icon": "👶",
        "for": "Non-experts and students",
        "model": "default",
        "temperature": 0.3,  # Slightly higher for more creative explanations
        "max_output_tokens": 4096,
        "top_p": 0.95,
        "top_k": 40,
        "max_pages": 10,
        "try_pdf_input": True,
        "auto_analyze": False  # Not part of initial auto-analysis
    },
    # Utility analysis types
    "field_tags": {
        "model": "field_tags",
        "temperature": 0.1,
        "max_output_tokens": 1024,
        "auto_analyze": True
    },
    "terminology": {
        "model": "terminology",
        "temperature": 0.1,
        "max_output_tokens": 2048,
        "auto_analyze": True
    },
    "metadata": {
        "model": "metadata",
        "temperature": 0.1,
        "max_output_tokens": 1024,
        "auto_analyze": True
    }
}

# Application UI settings
UI_SETTINGS = {
    "pdf_viewer_height": 800,
    "show_debug_info": False,
    "default_analysis_type": "comprehensive",
    "default_model": "default",
    "auto_extract_definitions": True,
    "auto_switch_to_analysis": True,  # Auto-switch to analysis tab after loading paper
    "auto_run_analysis": True,        # Auto-run analysis after loading paper
    "progress_timeout": 120
}

# Custom CSS for application
CUSTOM_CSS = """
<style>
    /* Clean divider */
    .divider {
        height: 1px;
        background-color: rgba(49, 51, 63, 0.2);
        margin: 1rem 0;
    }
    
    /* Field tag styling */
    .field-tag {
        display: inline-block;
        background-color: rgba(28, 131, 225, 0.1);
        padding: 0.2rem 0.6rem;
        border-radius: 1rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        font-size: 0.8rem;
    }
    
    /* Improved button contrast */
    div[data-testid="stButton"] > button {
        font-weight: 600;
    }
    
    /* Override for expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Remove extra padding around headers */
    h1, h2, h3, h4, h5, h6 {
        margin-top: 0.5rem !important;
    }
    
    /* Add space after analysis results */
    .stMarkdown {
        padding-bottom: 0.5rem;
    }
    
    /* Make container border more subtle */
    [data-testid="stDecoration"] {
        opacity: 0.2;
    }
    
    /* PDF viewer container */
    .pdf-viewer-container {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 0.5rem;
        padding: 0.5rem;
        margin: 1rem 0;
    }
    
    /* Definition cards */
    .definition-card {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: rgba(255, 255, 255, 0.03);
    }
    
    /* Tab content padding */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1rem;
    }
    
    /* Analysis result ratings */
    .rating {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    
    .rating-low {
        background-color: rgba(255, 99, 71, 0.2);
        color: #ff6347;
    }
    
    .rating-medium {
        background-color: rgba(255, 165, 0, 0.2);
        color: #ffa500;
    }
    
    .rating-high {
        background-color: rgba(34, 139, 34, 0.2);
        color: #228b22;
    }
</style>
"""

def get_api_key(user_api_key: Optional[str] = None) -> str:
    """
    Get API key, prioritizing user-provided key
    
    Args:
        user_api_key: User-provided API key
        
    Returns:
        API key to use
    """
    return user_api_key or API_KEY


def get_model_config(analysis_type: str, model_override: Optional[str] = None) -> Dict[str, Any]:
    """
    Get configuration for specific analysis type and model
    
    Args:
        analysis_type: Type of analysis
        model_override: Optional model override
        
    Returns:
        Configuration dictionary
    """
    # Get analysis type configuration
    analysis_config = ANALYSIS_TYPES.get(analysis_type, ANALYSIS_TYPES.get("comprehensive", {}))
    
    # Get specified model (from override, analysis config, or default)
    model_type = model_override or analysis_config.get("model", "default")
    model_config = MODEL_DEFINITIONS.get(model_type, MODEL_DEFINITIONS.get("default", {}))
    
    # Create combined configuration with model info taking precedence
    config = {**analysis_config, **model_config}
    
    return config


def get_analysis_types() -> Dict[str, Dict[str, Any]]:
    """
    Get displayable analysis types (excluding utility types)
    
    Returns:
        Dictionary of analysis types
    """
    return {k: v for k, v in ANALYSIS_TYPES.items() 
            if k not in ["field_tags", "terminology", "metadata"]}


def get_models() -> Dict[str, Dict[str, Any]]:
    """
    Get displayable models
    
    Returns:
        Dictionary of models
    """
    return {k: v for k, v in MODEL_DEFINITIONS.items() 
            if k in ["default", "pro", "alternate", "fallback"]}


def get_auto_analysis_types() -> List[str]:
    """
    Get analysis types that should run automatically on paper load
    
    Returns:
        List of analysis type keys to auto-run
    """
    if not UI_SETTINGS.get("auto_run_analysis", True):
        return []
        
    return [k for k, v in ANALYSIS_TYPES.items() 
            if v.get("auto_analyze", False)]