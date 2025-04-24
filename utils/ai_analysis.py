import time
import re
import json
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
from utils.prompts import get_prompt, KEY_DEFINITIONS_PROMPT

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the Google AI client with configurable API key
def get_client(api_key=None):
    """Get Gemini client with either user-provided or default API key"""
    return genai.Client(api_key=api_key or GOOGLE_API_KEY)

def get_available_models(api_key=None):
    """Get list of available Gemini models"""
    client = get_client(api_key)
    try:
        models = client.models.list()
        available_models = [model.name for model in models]
        return available_models
    except Exception as e:
        logger.error(f"Error getting available models: {str(e)}")
        return []

def extract_metadata_from_pdf(page_images, api_key=None):
    """
    Use Gemini to extract title and authors when PDF metadata fails
    """
    if not page_images or len(page_images) == 0:
        return {"title": "Unknown Title", "author": "Unknown Author"}
    
    # Only use the first page for metadata extraction
    first_page = page_images[0]
    
    client = get_client(api_key)
    
    prompt = """
    Extract the paper title and authors from this academic paper's first page.
    Respond in JSON format only, like this:
    {
      "title": "The full paper title",
      "authors": "Author1, Author2, Author3, etc."
    }
    """
    
    try:
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        first_page.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        # Add image as a Part using from_bytes method
        contents = [
            prompt,
            types.Part.from_bytes(data=img_bytes, mime_type="image/png")
        ]

        generation_config = types.GenerateContentConfig(
            max_output_tokens=1024,
            temperature= 0.1,
            top_p=0.95,
            top_k=40
        )
        
        # Generate content using a lightweight model - FIX: use properly configured generation parameters
        model = "gemini-2.0-flash-lite"
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generation_config
        )
        
        # Extract JSON from response
        json_pattern = r"```json\s*([\s\S]*?)\s*```|{[\s\S]*}"
        match = re.search(json_pattern, response.text)
        
        if match:
            json_str = match.group(1) if match.group(1) else match.group(0)
            # Clean the string
            json_str = re.sub(r'[^\{\}\"\':\[\],.\d\w\s_-]', '', json_str)
            metadata = json.loads(json_str)
            
            # Make sure we have the right keys
            if "authors" in metadata and "author" not in metadata:
                metadata["author"] = metadata["authors"]
                del metadata["authors"]
                
            return metadata
        else:
            logger.warning("No valid JSON found in metadata extraction")
            return {"title": "Unknown Title", "author": "Unknown Author"}
            
    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}")
        return {"title": "Unknown Title", "author": "Unknown Author"}

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
    
    # Check for math-heavy content
    equation_pattern = r"\$.*?\$|\\begin\{equation\}|\\sum|\\frac"
    math_content = 0
    
    # Check first few pages for equations
    for i, img in enumerate(page_images[:min(5, len(page_images))]):
        # This is a simplified check - in a real implementation, you'd use OCR
        # or other techniques to detect equations in images
        # For now, we'll just add some complexity for papers with many pages
        if i > 3:
            math_content += 0.05
    
    complexity += min(math_content, 0.3)  # Cap math complexity contribution
    
    # Limit to 0-1 range
    complexity = min(max(complexity, 0.0), 1.0)
    return complexity

def get_field_tags(title, abstract, api_key=None):
    """
    Use Gemini API to detect fields dynamically from paper title and abstract.
    
    Args:
        title: Paper title
        abstract: Paper abstract
        api_key: Optional API key
        
    Returns:
        Dictionary of field tags with descriptions and links
    """
    # If title and abstract are too short, return empty tags
    if len(title) < 5 or len(abstract) < 20:
        return {}
    
    # Get client with appropriate API key
    client = get_client(api_key)
    
    prompt = f"""
    Based on this paper title and abstract, identify 2-4 main research fields or subfields.
    Return only a JSON object with field names as keys, where each field has a short description and link.
    
    Title: {title}
    Abstract: {abstract[:500]}  # Using first 500 chars of abstract for brevity
    
    Example response format:
    {{
      "Computer Vision": {{
        "description": "Field focused on enabling computers to derive information from images",
        "link": "https://en.wikipedia.org/wiki/Computer_vision"
      }},
      "Deep Learning": {{
        "description": "Machine learning approach using neural networks with many layers",
        "link": "https://en.wikipedia.org/wiki/Deep_learning"
      }}
    }}
    """
    
    try:
        # Use a lightweight model for this task - FIX: use properly configured generation parameters
        generation_config = types.GenerateContentConfig(
            max_output_tokens=1024,
            temperature= 0.1,
            top_p=0.95,
            top_k=40
        )
        
        # Generate content using a lightweight model - FIX: use properly configured generation parameters
        model = "gemini-2.0-flash-lite"
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=generation_config
        )
        
        # Extract JSON from response
        json_pattern = r"```json\s*([\s\S]*?)\s*```|{[\s\S]*}"
        match = re.search(json_pattern, response.text)
        
        if match:
            json_str = match.group(1) if match.group(1) else match.group(0)
            # Clean the string - sometimes models add extra text
            json_str = re.sub(r'[^\{\}\"\':\[\],.\d\w\s_-]', '', json_str)
            field_tags = json.loads(json_str)
            return field_tags
        else:
            logger.warning("No valid JSON found in field tag response")
            return {}
            
    except Exception as e:
        logger.error(f"Error getting field tags: {str(e)}")
        return {}

def extract_key_definitions(analysis_text, api_key=None):
    """
    Extract key definitions and terminology from the paper analysis
    
    Args:
        analysis_text: The raw analysis text
        api_key: Optional API key
        
    Returns:
        Dictionary of terms and their definitions with explanations
    """
    client = get_client(api_key)
    
    prompt = f"""
    From this paper analysis, extract 5-10 key terms or concepts that would be helpful for readers to understand.
    For each term, provide a clear, concise definition and an explanation in simpler terms.
    
    Return the results as JSON only, in this format:
    {{
      "Term Name": {{
        "definition": "Formal/technical definition",
        "explanation": "Simpler explanation for non-experts"
      }},
      "Another Term": {{
        "definition": "Formal/technical definition",
        "explanation": "Simpler explanation for non-experts"
      }}
    }}
    
    Analysis text:
    {analysis_text[:4000]}  # Limit to first 4000 chars to stay within context limits
    """
    
    try:
        # FIX: Use properly configured generation parameters
        generation_config = types.GenerateContentConfig(
            max_output_tokens=1024,
            temperature= 0.1,
            top_p=0.95,
            top_k=40
        )
        
        # Generate content using a lightweight model - FIX: use properly configured generation parameters
        model = "gemini-2.0-flash-lite"
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=generation_config
        )
        
        # Extract JSON from response
        json_pattern = r"```json\s*([\s\S]*?)\s*```|{[\s\S]*}"
        match = re.search(json_pattern, response.text)
        
        if match:
            json_str = match.group(1) if match.group(1) else match.group(0)
            # Clean the string
            json_str = re.sub(r'[^\{\}\"\':\[\],.\d\w\s_-]', '', json_str)
            definitions = json.loads(json_str)
            return definitions
        else:
            logger.warning("No valid JSON found in definitions extraction")
            return {}
            
    except Exception as e:
        logger.error(f"Error extracting definitions: {str(e)}")
        return {}

def analyze_paper_with_gemini(
    page_images: List[Image.Image], 
    metadata: Dict[str, Any],
    analysis_type: str = "comprehensive",
    force_pro: bool = False,
    pdf_bytes: Optional[bytes] = None,
    api_key: Optional[str] = None,
    simplified: bool = False
) -> Dict[str, Any]:
    """
    Analyze a paper using Google's Gemini model with adaptive model selection.
    
    Args:
        page_images: List of PIL images of the paper pages
        metadata: Paper metadata dictionary
        analysis_type: Type of analysis to perform
        force_pro: Whether to force using the Pro model
        pdf_bytes: Raw PDF bytes for direct PDF processing (if available)
        api_key: Optional user-provided API key
        simplified: Whether to provide simplified explanation for non-experts
        
    Returns:
        Dictionary containing analysis results
    """
    start_time = time.time()
    
    # Try to fix bad metadata with LLM if needed
    if metadata.get("title", "").replace("-", "").isdigit() or len(metadata.get("title", "")) < 5:
        # Extract better metadata
        logger.info("Attempting to extract better metadata with LLM")
        better_metadata = extract_metadata_from_pdf(page_images, api_key)
        # Update metadata
        metadata.update(better_metadata)
    
    try:
        # Get client with appropriate API key
        client = get_client(api_key)
        
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
        prompt_text = get_prompt(analysis_type, metadata, simplified)
        
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

        # For simplified view
        if simplified or analysis_type == "simplified":
            result["simplified"] = response.text
            
        # Extract key definitions after analysis - but catch errors independently
        try:
            result["key_definitions"] = extract_key_definitions(response.text, api_key)
        except Exception as e:
            logger.error(f"Error extracting definitions (non-fatal): {str(e)}")
            result["key_definitions"] = {}
        
        # For comprehensive analysis, extract structured sections
        if analysis_type == "comprehensive":
            # Extract sections from the response text using improved extraction
            analysis_text = response.text
            
            # Define section headings for extraction
            sections = {
                "summary": ("SUMMARY", "KEY INNOVATIONS"),
                "key_innovations": ("KEY INNOVATIONS", "TECHNIQUES"),
                "techniques": ("TECHNIQUES", "PRACTICAL VALUE"),
                "practical_value": ("PRACTICAL VALUE", "LIMITATIONS"),
                "limitations": ("LIMITATIONS", None)
            }
            
            # Extract each section with improved algorithm
            for section_key, (start_marker, end_marker) in sections.items():
                section_content = extract_section_improved(analysis_text, start_marker, end_marker)
                if section_content:
                    result[section_key] = section_content
        
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

def extract_section_improved(text: str, section_start: str, section_end: Optional[str]) -> str:
    """
    Extract a section from the text between section_start and section_end with improved formatting.
    
    Args:
        text: Full text content
        section_start: Starting section header
        section_end: Ending section header or None for last section
        
    Returns:
        Extracted and cleaned section text
    """
    try:
        # Find the section start
        pattern = re.compile(f"(?:^|\n)[ ]*{re.escape(section_start)}[ ]*(?:$|\n)", re.MULTILINE)
        match = pattern.search(text)
        
        if not match:
            # Try alternate formats (e.g., ### SUMMARY)
            pattern = re.compile(f"(?:^|\n)[ ]*#{{1,6}}[ ]*{re.escape(section_start)}[ ]*(?:$|\n)", re.MULTILINE)
            match = pattern.search(text)
            
        if not match:
            return ""
            
        start_idx = match.end()
        
        # Find the end of the section
        if section_end:
            end_pattern = re.compile(f"(?:^|\n)[ ]*(?:#{{{1,6}}}[ ]*)?{re.escape(section_end)}[ ]*(?:$|\n)", re.MULTILINE)
            end_match = end_pattern.search(text, start_idx)
            
            if end_match:
                end_idx = end_match.start()
                section_text = text[start_idx:end_idx].strip()
            else:
                section_text = text[start_idx:].strip()
        else:
            # If no end marker, take until the end
            section_text = text[start_idx:].strip()
        
        # Clean up formatting issues
        # 1. Remove any lines that are just bullet markers
        section_text = re.sub(r'^\s*[\*\-\•]\s*$', '', section_text, flags=re.MULTILINE)
        
        # 2. Fix bullet points for consistent formatting
        section_text = re.sub(r'^\s*[\*\-\•]\s*', '* ', section_text, flags=re.MULTILINE)
        
        # 3. Fix extra newlines
        section_text = re.sub(r'\n{3,}', '\n\n', section_text)
        
        # 4. Remove any markdown section numbering artifacts
        section_text = re.sub(r'^\s*\d+\.\s+', '', section_text, flags=re.MULTILINE)
        
        # 5. Clean up bold/italic markdown issues
        section_text = re.sub(r'\*{3,}', '**', section_text)
        
        return section_text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting section: {str(e)}")
        return ""