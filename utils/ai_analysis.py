import time
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from PIL import Image
import io
import logging
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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    force_pro: bool = False,
    pdf_bytes: Optional[bytes] = None
) -> Dict[str, Any]:
    """
    Analyze a paper using Google's Gemini model with adaptive model selection.
    
    Args:
        page_images: List of PIL images of the paper pages
        metadata: Paper metadata dictionary
        analysis_type: Type of analysis to perform
        force_pro: Whether to force using the Pro model
        pdf_bytes: Raw PDF bytes for direct PDF processing (if available)
        
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
        
        # Set up generation parameters
        generation_config = types.GenerateContentConfig(
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            top_k=TOP_K
        )
        
        # Prepare content for the API
        contents = []
        processing_method = "unknown"
        
        # First add the text prompt
        contents.append(prompt_text)
        
        # Try direct PDF processing if PDF bytes are available
        if pdf_bytes is not None:
            try:
                logger.info("Attempting to process document as PDF")
                # Add PDF as a Part using from_bytes method
                contents.append(
                    types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type="application/pdf"
                    )
                )
                
                # Generate content using the PDF
                response = client.models.generate_content(
                    model=model_to_use,
                    contents=contents,
                    config=generation_config
                )
                
                processing_method = "direct_pdf"
                logger.info("Successfully processed document as PDF")
                
            except Exception as e:
                # If PDF processing fails, log the error and fall back to image-based approach
                logger.warning(f"PDF processing failed: {str(e)}. Falling back to image-based approach.")
                
                # Reset contents for image-based approach
                contents = [prompt_text]
                
                # Select number of pages based on model and paper length
                max_pages = min(15, len(page_images))  # Default
                
                if "pro" in model_to_use:
                    # Pro models can handle more pages
                    max_pages = min(20, len(page_images))
                
                selected_images = page_images[:max_pages]
                
                # Then add each image using Part.from_bytes
                for img in selected_images:
                    # Convert PIL image to bytes
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    img_bytes = img_byte_arr.getvalue()
                    
                    # Add image as a Part using from_bytes method
                    contents.append(
                        types.Part.from_bytes(
                            data=img_bytes,
                            mime_type="image/png"
                        )
                    )
                
                # Generate content using images
                response = client.models.generate_content(
                    model=model_to_use,
                    contents=contents,
                    config=generation_config
                )
                
                processing_method = "image_based"
                logger.info("Successfully processed document using images")
        
        else:
            # No PDF bytes available, use image-based approach directly
            logger.info("PDF bytes not available, using image-based approach")
            
            # Select number of pages based on model and paper length
            max_pages = min(15, len(page_images))  # Default
            
            if "pro" in model_to_use:
                # Pro models can handle more pages
                max_pages = min(20, len(page_images))
            
            selected_images = page_images[:max_pages]
            
            # Then add each image using Part.from_bytes
            for img in selected_images:
                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Add image as a Part using from_bytes method
                contents.append(
                    types.Part.from_bytes(
                        data=img_bytes,
                        mime_type="image/png"
                    )
                )
            
            # Generate content using images
            response = client.models.generate_content(
                model=model_to_use,
                contents=contents,
                config=generation_config
            )
            
            processing_method = "image_based"
            logger.info("Successfully processed document using images")
        
        # Process the response
        result = {
            "raw_analysis": response.text,
            "analysis_type": analysis_type,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_used": model_to_use,
            "processing_method": processing_method
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
        
        if processing_method == "direct_pdf":
            # For PDF-based processing
            result["pdf_processed"] = True
        else:
            # For image-based processing
            result["pages_analyzed"] = len(selected_images)
            result["total_pages"] = len(page_images)
        
        if AUTO_UPGRADE_TO_PRO:
            result["paper_complexity"] = metadata.get("estimated_complexity", 0)
            result["pro_model_triggered"] = use_pro
        
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
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
        
        # Clean up section text - remove any lines that look like section numbering
        lines = section_text.split('\n')
        cleaned_lines = []
        for line in lines:
            if not line.strip().startswith('**') and not (line.strip().startswith('*') and len(line.strip()) < 5):
                cleaned_lines.append(line)
        
        section_text = '\n'.join(cleaned_lines).strip()
        return section_text
    
    except Exception:
        return ""