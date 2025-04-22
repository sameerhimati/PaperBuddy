import time
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from PIL import Image
import io
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

# Create the Google AI client
client = genai.Client(api_key=GOOGLE_API_KEY)

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
        
        # Get appropriate prompt based on analysis type
        prompt_text = get_prompt(analysis_type, metadata)
        
        # Select number of pages based on model and paper length
        max_pages = min(15, len(page_images))  # Default
        
        if "pro" in model_to_use:
            # Pro models can handle more pages
            max_pages = min(20, len(page_images))
        
        selected_images = page_images[:max_pages]
        
        # Prepare content for the API
        contents = []
        
        # First add the text prompt
        contents.append(prompt_text)
        
        # Then add each image
        for img in selected_images:
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            # Add image to contents
            contents.append({
                "mime_type": "image/png",
                "data": img_bytes
            })
        
        # Set up generation parameters
        generation_config = types.GenerateContentConfig(
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            top_k=TOP_K
        )

        # Generate content using the current API
        response = client.models.generate_content(
            model=model_to_use,
            contents=contents,
            config = generation_config
        )
        
        # Process the response
        result = {
            "raw_analysis": response.text,
            "analysis_type": analysis_type,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_used": model_to_use,
        }
        
        # For comprehensive analysis, extract structured sections
        if analysis_type == "comprehensive":
            # Extract sections from the response text
            analysis_text = response.text
            summary = extract_section(analysis_text, "SUMMARY", "KEY INNOVATIONS")
            innovations = extract_section(analysis_text, "KEY INNOVATIONS", "TECHNIQUES")
            techniques = extract_section(analysis_text, "TECHNIQUES", "PRACTICAL VALUE")
            practical = extract_section(analysis_text, "PRACTICAL VALUE", "LIMITATIONS")
            limitations = extract_section(analysis_text, "LIMITATIONS", None)
            
            # Add structured data if available
            if summary:
                result["summary"] = summary
            if innovations:
                result["key_innovations"] = innovations
            if techniques:
                result["techniques"] = techniques
            if practical:
                result["practical_value"] = practical
            if limitations:
                result["limitations"] = limitations
        
        # Add processing metadata
        result["processing_time"] = time.time() - start_time
        result["pages_analyzed"] = len(selected_images)
        result["total_pages"] = len(page_images)
        
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

def extract_section(text: str, section_start: str, section_end: Optional[str]) -> str:
    """Extract a section from the text between section_start and section_end."""
    try:
        start_idx = text.find(section_start)
        if start_idx == -1:
            return ""
        
        # Move past the section header
        start_idx = text.find("\n", start_idx)
        if start_idx == -1:
            return ""
        
        # Find the end of the section
        if section_end:
            end_idx = text.find(section_end, start_idx)
            if end_idx == -1:
                # If end marker not found, take until the end
                section_text = text[start_idx:].strip()
            else:
                section_text = text[start_idx:end_idx].strip()
        else:
            # If no end marker, take until the end
            section_text = text[start_idx:].strip()
            
        return section_text
    
    except Exception:
        return ""