import os
import tempfile
import base64
import logging
import requests
import arxiv
import fitz  # PyMuPDF
from PIL import Image
import io
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PaperContent:
    """Data class for storing paper content and metadata"""
    metadata: Dict[str, Any]
    page_images: List[Image.Image]
    pdf_bytes: Optional[bytes] = None
    pdf_path: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if paper content is valid"""
        return self.error is None and len(self.page_images) > 0
    
    @property
    def page_count(self) -> int:
        """Get the number of pages in the paper"""
        return len(self.page_images)
    
    def get_pdf_base64(self) -> Optional[str]:
        """Get PDF as base64 for embedding in HTML"""
        if self.pdf_bytes:
            return base64.b64encode(self.pdf_bytes).decode('utf-8')
        elif self.pdf_path and os.path.exists(self.pdf_path):
            with open(self.pdf_path, "rb") as file:
                return base64.b64encode(file.read()).decode('utf-8')
        return None


def extract_text_from_pdf(doc) -> Dict[str, str]:
    """
    Extract full text content from PDF document
    
    Args:
        doc: PyMuPDF document
        
    Returns:
        Dictionary with full text and first page text
    """
    full_text = ""
    first_page_text = ""
    
    try:
        # Extract text from all pages
        for i, page in enumerate(doc):
            page_text = page.get_text()
            full_text += page_text
            
            # Save first page text separately
            if i == 0:
                first_page_text = page_text
    except Exception as e:
        logger.warning(f"Error extracting text from PDF: {str(e)}")
    
    return {
        "full_text": full_text,
        "first_page_text": first_page_text
    }


def load_pdf_from_path(pdf_path: str) -> PaperContent:
    """
    Load a PDF from a file path and extract pages as images and metadata.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        PaperContent object with images and metadata
    """
    try:
        # Read PDF bytes for future use
        with open(pdf_path, "rb") as file:
            pdf_bytes = file.read()
            
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        # Extract basic metadata
        metadata = {
            "title": doc.metadata.get("title", "Unknown Title"),
            "author": doc.metadata.get("author", "Unknown Author"),
            "page_count": len(doc),
            "filename": os.path.basename(pdf_path)
        }
        
        # We'll let the AI model extract/enhance metadata rather than using regex
        # Just store the text for now
        text_data = extract_text_from_pdf(doc)
        metadata["first_page_text"] = text_data["first_page_text"]
        
        # Extract pages as images with optimized resolution
        page_images = []
        resolution = 150  # DPI for images
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(resolution/72, resolution/72))
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            page_images.append(img)
            
        result = PaperContent(
            metadata=metadata,
            page_images=page_images,
            pdf_bytes=pdf_bytes,
            pdf_path=pdf_path
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Error loading PDF: {str(e)}"
        logger.error(error_msg)
        return PaperContent(
            metadata={"title": "Error Loading PDF", "error": str(e)},
            page_images=[],
            error=error_msg
        )


def load_pdf_from_arxiv(arxiv_id: str) -> PaperContent:
    """
    Download and load a PDF from arXiv using its ID.
    
    Args:
        arxiv_id: arXiv identifier (e.g., '2303.08774')
        
    Returns:
        PaperContent object with images and metadata
    """
    try:
        # Strip version number if present
        base_id = arxiv_id.split('v')[0] if 'v' in arxiv_id else arxiv_id
        
        # Search for the paper
        search = arxiv.Search(id_list=[base_id])
        results = list(search.results())
        
        if not results:
            error_msg = f"No paper found with arXiv ID: {arxiv_id}"
            return PaperContent(
                metadata={"title": "Paper Not Found", "error": error_msg},
                page_images=[],
                error=error_msg
            )
            
        paper = results[0]
        
        # Create a temporary directory to save the PDF
        temp_dir = tempfile.mkdtemp()
        pdf_path = os.path.join(temp_dir, f"{base_id}.pdf")
        
        # Download the PDF
        paper.download_pdf(filename=pdf_path)
        
        # Gather arXiv metadata before loading
        arxiv_metadata = {
            "title": paper.title,
            "author": ', '.join(author.name for author in paper.authors),
            "abstract": paper.summary,
            "url": paper.pdf_url,
            "published": paper.published.strftime("%Y-%m-%d") if paper.published else "Unknown",
            "arxiv_id": arxiv_id,
            "source": "arxiv"
        }
        
        # Load the PDF
        paper_content = load_pdf_from_path(pdf_path)
        
        # Update with arXiv metadata (taking precedence over PDF metadata)
        paper_content.metadata.update(arxiv_metadata)
        
        return paper_content
        
    except Exception as e:
        error_msg = f"Error loading PDF from arXiv: {str(e)}"
        logger.error(error_msg)
        return PaperContent(
            metadata={"title": "Error Loading arXiv Paper", "error": str(e)},
            page_images=[],
            error=error_msg
        )


def load_pdf_from_url(url: str) -> PaperContent:
    """
    Download and load a PDF from a URL.
    
    Args:
        url: URL to the PDF file
        
    Returns:
        PaperContent object with images and metadata
    """
    try:
        # Create a temporary file to save the PDF
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp_path = tmp.name
        
        # Download the PDF with proper error handling
        try:
            # Set timeout and user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 PaperBuddy PDF Downloader'
            }
            response = requests.get(url, stream=True, headers=headers, timeout=30)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Check content type to confirm it's a PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                raise ValueError(f"URL does not point to a PDF file. Content-Type: {content_type}")
            
            # Save the PDF to the temporary file
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            
            tmp.close()
            
            # Get content as bytes for future use
            with open(tmp_path, "rb") as file:
                pdf_bytes = file.read()
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to download PDF: {str(e)}")
        
        # Load the PDF
        paper_content = load_pdf_from_path(tmp_path)
        
        # Add URL to metadata
        paper_content.metadata["url"] = url
        paper_content.metadata["source"] = "url"
        paper_content.pdf_bytes = pdf_bytes
        
        return paper_content
        
    except Exception as e:
        error_msg = f"Error loading PDF from URL: {str(e)}"
        logger.error(error_msg)
        return PaperContent(
            metadata={"title": "Error Loading PDF from URL", "error": str(e)},
            page_images=[],
            error=error_msg
        )
    finally:
        # Always clean up the temporary file
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file: {str(e)}")


def get_embedded_pdf_viewer(paper_content: PaperContent, height: int = 800) -> Optional[str]:
    """
    Generate HTML for an embedded PDF viewer with improved zoom and page settings
    
    Args:
        paper_content: PaperContent object
        height: Height of the PDF viewer in pixels
        
    Returns:
        HTML string for the PDF viewer or None if PDF is not available
    """
    base64_pdf = paper_content.get_pdf_base64()
    
    if not base64_pdf:
        return None
        
    # Create an iframe with the PDF viewer
    # Using URL parameters to set initial view:
    # - page=1 - start on first page
    # - zoom=125 - set zoom to 125%
    # - view=FitH - fit to width
    pdf_display = f"""
    <div style="display: flex; justify-content: center; width: 100%;">
        <iframe 
            src="data:application/pdf;base64,{base64_pdf}#page=1&zoom=125&view=FitH" 
            width="100%" 
            height="{height}px" 
            style="border: none; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
        </iframe>
    </div>
    """
    
    return pdf_display


def cleanup_temporary_files(paper_content: PaperContent) -> None:
    """
    Clean up any temporary files associated with the paper content
    
    Args:
        paper_content: PaperContent object
    """
    try:
        if paper_content.pdf_path and os.path.exists(paper_content.pdf_path):
            os.unlink(paper_content.pdf_path)
            
            # Also remove parent directory if it's a temp dir and now empty
            parent_dir = os.path.dirname(paper_content.pdf_path)
            if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                os.rmdir(parent_dir)
    except Exception as e:
        logger.warning(f"Failed to clean up temporary files: {str(e)}")