import time
import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Tuple
from PIL import Image
import io
import concurrent.futures

from google import genai
from google.genai import types

# Config imports
from config import get_model_config, get_api_key
from utils.prompts import get_prompt

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Data class for storing analysis results"""
    analysis_type: str
    raw_analysis: str
    model_used: str
    processing_time: float
    sections: Dict[str, str] = field(default_factory=dict)
    key_definitions: Dict[str, Dict[str, str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """Check if analysis was successful"""
        return self.error is None and len(self.raw_analysis) > 0
    
    def get_section(self, section_name: str, default: str = "") -> str:
        """Get a section by name with default fallback"""
        return self.sections.get(section_name, default)


def create_genai_client(api_key: Optional[str] = None) -> genai.Client:
    """
    Create Google Generative AI client with appropriate API key
    
    Args:
        api_key: Optional user-provided API key
        
    Returns:
        Configured genai.Client object
    """
    # Get API key (user-provided or default)
    key = api_key or get_api_key()
    
    if not key:
        raise ValueError("No API key available. Please provide a valid API key.")
        
    return genai.Client(api_key=key)


def extract_structured_data(response_text: str) -> Dict[str, Any]:
    """
    Extract structured data from model response with robust error handling
    
    Args:
        response_text: Raw text response from model
        
    Returns:
        Extracted structured data or empty dict
    """
    # Strategy 1: Look for JSON blocks (```json ... ```)
    json_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
    
    for block in json_blocks:
        try:
            result = json.loads(block.strip())
            if result and isinstance(result, dict):
                return result
        except:
            pass
    
    # Strategy 2: Look for entire response as JSON
    if response_text.strip().startswith('{') and response_text.strip().endswith('}'):
        try:
            result = json.loads(response_text.strip())
            if result and isinstance(result, dict):
                return result
        except:
            pass
    
    # Strategy 3: Look for JSON-like objects anywhere in the text
    bracket_start = response_text.find('{')
    bracket_end = response_text.rfind('}')
    
    if bracket_start >= 0 and bracket_end > bracket_start:
        json_candidate = response_text[bracket_start:bracket_end + 1]
        try:
            result = json.loads(json_candidate)
            if result and isinstance(result, dict):
                return result
        except:
            pass
    
    # If all strategies fail, return empty dict
    return {}


def extract_section(text: str, section_name: str, next_section: Optional[str] = None) -> str:
    """
    Extract content of a specific section from analysis text
    
    Args:
        text: Full analysis text
        section_name: Name of section to extract
        next_section: Name of next section (to determine where section ends)
        
    Returns:
        Extracted section text or empty string
    """
    # Different heading patterns to try
    heading_patterns = [
        fr'(?:^|\n)[ ]*{re.escape(section_name)}[ ]*(?:$|\n)',  # Plain heading
        fr'(?:^|\n)[ ]*#{1,6}[ ]*{re.escape(section_name)}[ ]*(?:$|\n)',  # Markdown heading
        fr'(?:^|\n)[ ]*\d+\.[ ]*{re.escape(section_name)}[ ]*(?:$|\n)'  # Numbered heading
    ]
    
    # Try each pattern until one works
    section_start = -1
    for pattern in heading_patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            section_start = match.end()
            break
    
    if section_start == -1:
        return ""
    
    # Find end of section
    section_end = len(text)
    if next_section:
        for pattern in heading_patterns:
            next_pattern = pattern.replace(re.escape(section_name), re.escape(next_section))
            match = re.search(next_pattern, text[section_start:], re.MULTILINE)
            if match:
                section_end = section_start + match.start()
                break
    
    # Extract and clean section text
    section_text = text[section_start:section_end].strip()
    
    # Clean up formatting issues
    section_text = re.sub(r'^\s*[\*\-\•]\s*$', '', section_text, flags=re.MULTILINE)  # Remove bullet-only lines
    section_text = re.sub(r'^\s*[\*\-\•]\s*', '* ', section_text, flags=re.MULTILINE)  # Standardize bullets
    section_text = re.sub(r'\n{3,}', '\n\n', section_text)  # Fix extra newlines
    
    return section_text.strip()


def extract_all_sections(analysis_text: str) -> Dict[str, str]:
    """
    Extract all standard sections from analysis text
    
    Args:
        analysis_text: Full analysis text
        
    Returns:
        Dict mapping section names to content
    """
    # Define section structure (in order)
    sections = [
        "SUMMARY",
        "KEY INNOVATIONS",
        "TECHNIQUES",
        "PRACTICAL VALUE",
        "LIMITATIONS"
    ]
    
    result = {}
    
    # Extract each section
    for i, section in enumerate(sections):
        next_section = sections[i + 1] if i < len(sections) - 1 else None
        content = extract_section(analysis_text, section, next_section)
        
        if content:
            # Convert to lowercase with underscores for keys
            key = section.lower().replace(' ', '_')
            result[key] = content
    
    return result


def extract_key_definitions(
    model_response: str,
    min_definitions: int = 3,
    max_definitions: int = 10
) -> Dict[str, Dict[str, str]]:
    """
    Extract key terminology definitions from model response
    
    Args:
        model_response: Raw text response from model
        min_definitions: Minimum number of definitions to extract
        max_definitions: Maximum number of definitions to extract
        
    Returns:
        Dictionary of term definitions
    """
    # First try to extract as JSON
    json_data = extract_structured_data(model_response)
    
    if json_data and len(json_data) >= min_definitions:
        # Validate structure (each value should have definition/explanation)
        valid_entries = {}
        
        for term, info in json_data.items():
            if isinstance(info, dict) and "definition" in info:
                valid_entries[term] = {
                    "definition": info.get("definition", ""),
                    "explanation": info.get("explanation", "")
                }
            elif isinstance(info, str):
                # Handle cases where the model outputs a simpler format
                valid_entries[term] = {
                    "definition": info,
                    "explanation": ""
                }
        
        if len(valid_entries) >= min_definitions:
            return valid_entries
    
    # If JSON extraction failed, try heuristic extraction
    definitions = {}
    
    # Look for patterns like "Term: Definition" or "Term - Definition"
    term_patterns = [
        r'["\*_]*([A-Z][A-Za-z0-9 \-]+)["\*_]*:[ \t]*([^\n]+(?:\n(?![\n\*])[^\n]+)*)',
        r'["\*_]*([A-Z][A-Za-z0-9 \-]+)["\*_]*[ \t]*\-[ \t]*([^\n]+(?:\n(?![\n\*])[^\n]+)*)'
    ]
    
    for pattern in term_patterns:
        matches = re.findall(pattern, model_response)
        for term, definition in matches:
            term = term.strip()
            if len(term) > 2 and term not in definitions:
                definitions[term] = {
                    "definition": definition.strip(),
                    "explanation": ""  # No explanation available with this method
                }
            
            if len(definitions) >= max_definitions:
                break
    
    return definitions


def analyze_terminology(
    page_images: List[Image.Image],
    metadata: Dict[str, Any],
    api_key: Optional[str] = None
) -> Dict[str, Dict[str, str]]:
    """
    Extract key terminology from paper
    
    Args:
        page_images: List of page images
        metadata: Paper metadata
        api_key: Optional API key
        
    Returns:
        Dictionary of terminology with definitions and explanations
    """
    start_time = time.time()
    
    try:
        # Get client and model config
        client = create_genai_client(api_key)
        config = get_model_config("terminology")
        
        # Get prompt from the prompts module
        title = metadata.get("title", "Unknown Title")
        authors = metadata.get("author", "Unknown Author")
        prompt = get_prompt("terminology", metadata)
        
        # Prepare image content
        contents = [prompt]
        
        # Limit to first few pages for terminology extraction
        max_pages = min(3, len(page_images))
        
        # Add page images
        for img in page_images[:max_pages]:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            contents.append(
                types.Part.from_bytes(
                    data=img_bytes,
                    mime_type="image/png"
                )
            )
        
        # Set up generation parameters (using lower temperature for more reliable extraction)
        generation_config = types.GenerateContentConfig(
            max_output_tokens=config.get("max_output_tokens", 1024),
            temperature=0.1,  # Lower temperature for terminology extraction
            top_p=config.get("top_p", 0.95),
            top_k=config.get("top_k", 40)
        )
        
        # Generate content
        response = client.models.generate_content(
            model=config.get("model"),
            contents=contents,
            config=generation_config
        )
        
        # Extract terminology from response
        definitions = extract_key_definitions(response.text)
        
        logger.info(f"Extracted {len(definitions)} terminology definitions in {time.time() - start_time:.2f}s")
        
        return definitions
        
    except Exception as e:
        logger.error(f"Error extracting terminology: {str(e)}")
        return {}


def get_field_tags(
    title: str,
    abstract: str,
    api_key: Optional[str] = None
) -> Dict[str, Dict[str, str]]:
    """
    Get field tags for paper based on title and abstract
    
    Args:
        title: Paper title
        abstract: Paper abstract
        api_key: Optional API key
        
    Returns:
        Dictionary of field tags with descriptions and links
    """
    # Skip if title or abstract are too short
    if len(title) < 5 or len(abstract) < 20:
        return {}
    
    try:
        # Get client and config
        client = create_genai_client(api_key)
        config = get_model_config("field_tags")
        
        # Get prompt from the prompts module
        metadata = {"title": title, "abstract": abstract}
        prompt = get_prompt("field_tags", metadata)
        
        # Generate content with a lightweight model
        generation_config = types.GenerateContentConfig(
            max_output_tokens=1024,
            temperature=0.1,  # Lower temperature for more reliable JSON
            top_p=0.95,
            top_k=40
        )
        
        response = client.models.generate_content(
            model=config.get("model"),
            contents=prompt,
            config=generation_config
        )
        
        # Extract structured data from response
        field_tags = extract_structured_data(response.text)
        
        return field_tags
            
    except Exception as e:
        logger.error(f"Error getting field tags: {str(e)}")
        return {}


def analyze_paper(
    page_images: List[Image.Image],
    metadata: Dict[str, Any],
    analysis_type: str = "comprehensive",
    api_key: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None,
    simplified: bool = False
) -> AnalysisResult:
    """
    Analyze paper using Gemini model
    
    Args:
        page_images: List of page images
        metadata: Paper metadata
        analysis_type: Type of analysis to perform
        api_key: Optional API key
        pdf_bytes: Optional PDF bytes for direct PDF processing
        simplified: Whether to provide simplified explanation
        
    Returns:
        AnalysisResult object
    """
    start_time = time.time()
    
    try:
        # Get client and model config
        client = create_genai_client(api_key)
        
        # Override analysis type for simplified mode
        if simplified:
            analysis_type = "simplified"
            
        # Get model configuration
        config = get_model_config(analysis_type)
        
        # Get prompt from the prompts module
        prompt = get_prompt(analysis_type, metadata, simplified=simplified)
        
        # Prepare image content
        contents = [prompt]
        
        # Determine if we should try direct PDF processing
        if pdf_bytes and config.get("try_pdf_input", False):
            try:
                logger.info("Attempting to process document as PDF")
                # Add PDF as a Part
                contents.append(
                    types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type="application/pdf"
                    )
                )
                
                # Generate content using the PDF
                generation_config = types.GenerateContentConfig(
                    max_output_tokens=config.get("max_output_tokens", 8192),
                    temperature=config.get("temperature", 0.2),
                    top_p=config.get("top_p", 0.95),
                    top_k=config.get("top_k", 40)
                )
                
                response = client.models.generate_content(
                    model=config.get("model"),
                    contents=contents,
                    config=generation_config
                )
                
                processing_method = "direct_pdf"
                logger.info("Successfully processed document as PDF")
                
            except Exception as e:
                # If PDF processing fails, fall back to image-based approach
                logger.warning(f"PDF processing failed: {str(e)}. Falling back to image-based approach.")
                contents = [prompt]  # Reset contents
                processing_method = None  # Will be set in the image block
        else:
            # No PDF bytes or PDF processing not enabled
            processing_method = None  # Will be set in the image block
        
        # If we don't have a response yet, use image-based approach
        if not locals().get('response'):
            # Select number of pages based on model capability and paper length
            max_pages = min(config.get("max_pages", 15), len(page_images))
            selected_images = page_images[:max_pages]
            
            # Add each image
            for img in selected_images:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                contents.append(
                    types.Part.from_bytes(
                        data=img_bytes,
                        mime_type="image/png"
                    )
                )
            
            # Generate content using images
            generation_config = types.GenerateContentConfig(
                max_output_tokens=config.get("max_output_tokens", 8192),
                temperature=config.get("temperature", 0.2),
                top_p=config.get("top_p", 0.95),
                top_k=config.get("top_k", 40)
            )
            
            response = client.models.generate_content(
                model=config.get("model"),
                contents=contents,
                config=generation_config
            )
            
            processing_method = "image_based"
            logger.info(f"Processed document using {len(selected_images)} images")
        
        # Extract sections from the response
        raw_analysis = response.text
        sections = extract_all_sections(raw_analysis) if analysis_type == "comprehensive" else {}
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create result object
        result = AnalysisResult(
            analysis_type=analysis_type,
            raw_analysis=raw_analysis,
            model_used=config.get("model"),
            processing_time=processing_time,
            sections=sections,
            metadata={
                "processing_method": processing_method,
                "pages_analyzed": len(selected_images) if processing_method == "image_based" else None,
                "total_pages": len(page_images),
                "pdf_processed": processing_method == "direct_pdf"
            }
        )
        
        logger.info(f"Completed {analysis_type} analysis in {processing_time:.2f}s")
        
        return result
        
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        logger.error(error_msg)
        
        # Create error result
        return AnalysisResult(
            analysis_type=analysis_type,
            raw_analysis="",
            model_used=config.get("model") if 'config' in locals() else "unknown",
            processing_time=time.time() - start_time,
            error=error_msg
        )


def process_paper_with_parallel_analysis(
    page_images: List[Image.Image],
    metadata: Dict[str, Any],
    api_key: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None,
    analysis_types: List[str] = ["comprehensive", "quick_summary", "technical", "practical"]
) -> Dict[str, Any]:
    """
    Process paper with parallel analysis tasks
    
    Args:
        page_images: List of page images
        metadata: Paper metadata
        api_key: Optional API key
        pdf_bytes: Optional PDF bytes
        analysis_types: List of analysis types to run
        
    Returns:
        Dictionary of analysis results and metadata
    """
    # Define tasks to run in parallel
    tasks = {
        "terminology": lambda: analyze_terminology(page_images, metadata, api_key),
        "field_tags": lambda: get_field_tags(
            metadata.get("title", ""), 
            metadata.get("abstract", ""),
            api_key
        )
    }
    
    # Add requested analysis types
    for analysis_type in analysis_types:
        tasks[analysis_type] = lambda type=analysis_type: analyze_paper(
            page_images, metadata, type, api_key, pdf_bytes
        )
    
    results = {}
    
    # Run tasks in parallel with a thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(task_func): task_name 
            for task_name, task_func in tasks.items()
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_task):
            task_name = future_to_task[future]
            try:
                task_result = future.result()
                results[task_name] = task_result
            except Exception as e:
                logger.error(f"Task {task_name} generated an exception: {str(e)}")
                if task_name in analysis_types:
                    # For analysis tasks, create an error result
                    results[task_name] = AnalysisResult(
                        analysis_type=task_name,
                        raw_analysis="",
                        model_used="unknown",
                        processing_time=0,
                        error=str(e)
                    )
                else:
                    # For other tasks, store an empty result
                    results[task_name] = {} if task_name in ["terminology", "field_tags"] else None
    
    return results