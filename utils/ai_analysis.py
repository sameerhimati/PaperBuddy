from google import genai
from PIL import Image
from typing import List, Dict, Any, Optional
import time
import json
import re
from config import (
    GOOGLE_API_KEY, 
    ACTIVE_MODEL,
    DEFAULT_MODEL,
    PRO_MODEL, 
    AUTO_UPGRADE_TO_PRO,
    COMPLEXITY_THRESHOLD,
    MAX_OUTPUT_TOKENS,
    TEMPERATURE,
    TOP_P,
    TOP_K
)
from utils.prompts import get_prompt

# Configure the Gemini API
client = genai.Client(api_key=GOOGLE_API_KEY)

def initialize_gemini_model(model_name=None):
    """Initialize and return the Gemini model."""
    try:
        model = genai.GenerativeModel(
            model_name=model_name or ACTIVE_MODEL,
            generation_config={
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
                "top_k": TOP_K,
            }
        )
        return model
    except Exception as e:
        raise Exception(f"Error initializing Gemini model: {str(e)}")

def detect_paper_complexity(metadata: Dict[str, Any], page_images: List[Image.Image]) -> float:
    """
    Estimate the complexity of a paper to determine if we should use Pro model.
    This is a simple heuristic approach that could be improved over time.
    
    Returns:
        Float between 0-1 representing estimated complexity
    """
    complexity = 0.0
    
    # Check for complexity indicators in metadata
    abstract = metadata.get("abstract", "").lower()
    title = metadata.get("title", "").lower()
    
    # Keywords suggesting complexity
    complex_keywords = [
        "novel", "framework", "algorithm", "theoretical", "mathematics", 
        "quantum", "neural", "deep learning", "transformer", "attention",
        "theorem", "proof", "equation", "optimization", "gradient"
    ]
    
    # Check title and abstract for complex keywords
    for keyword in complex_keywords:
        if keyword in title:
            complexity += 0.15  # Higher weight for title
        if keyword in abstract:
            complexity += 0.05  # Lower weight for abstract
    
    # Limit to 0-1 range
    complexity = min(max(complexity, 0.0), 1.0)
    return complexity

def analyze_paper_with_gemini(
    page_images: List[Image.Image], 
    metadata: Dict[str, Any],
    analysis_type: str = "comprehensive",
    force_pro: bool = False
) -> Dict[str, Any]:
    """
    Analyze a paper using Google's Gemini model with adaptive model selection.
    
    Args:
        page_images: List of PIL images of the paper pages
        metadata: Paper metadata dictionary
        analysis_type: Type of analysis to perform
        force_pro: Whether to force using the Pro model
        
    Returns:
        Dictionary containing analysis results
    """
    start_time = time.time()
    
    try:
        # Determine if we should use the Pro model
        use_pro = force_pro
        
        if not force_pro and AUTO_UPGRADE_TO_PRO:
            # Check paper complexity to determine if we should upgrade to Pro
            complexity = detect_paper_complexity(metadata, page_images)
            metadata["estimated_complexity"] = complexity
            
            if complexity >= COMPLEXITY_THRESHOLD:
                use_pro = True
                
        # Select model based on complexity determination
        model_to_use = PRO_MODEL if use_pro else ACTIVE_MODEL
        model = initialize_gemini_model(model_to_use)
        
        # Get appropriate prompt based on analysis type
        prompt = get_prompt(analysis_type, metadata)
        
        # Select number of pages based on model and paper length
        max_pages = min(15, len(page_images))  # Default
        
        if "pro" in model_to_use:
            # Pro models can handle more pages
            max_pages = min(20, len(page_images))
        
        selected_images = page_images[:max_pages]
        
        # Create content list with text prompt and images
        content = [prompt]
        for img in selected_images:
            content.append(img)
        
        # Generate analysis
        response = client.models.generate_content(response, analysis_type, model_to_use)
        
        # Process response
        result = client.models.generate_content(response, analysis_type, model_to_use)
        
        # Add processing metadata
        result["processing_time"] = time.time() - start_time
        result["pages_analyzed"] = len(selected_images)
        result["total_pages"] = len(page_images)
        result["model_used"] = model_to_use
        
        if AUTO_UPGRADE_TO_PRO:
            result["paper_complexity"] = metadata.get("estimated_complexity", 0)
            result["pro_model_triggered"] = use_pro
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "analysis_type": analysis_type,
            "model_attempted": PRO_MODEL if force_pro else ACTIVE_MODEL,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "processing_time": time.time() - start_time
        }