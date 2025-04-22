import os
import tempfile
import urllib.request
import fitz  # PyMuPDF
import requests
import arxiv
from PIL import Image
import io
from typing import Dict, List, Tuple, Optional
import base64


def load_pdf_from_path(pdf_path: str) -> Tuple[List[Image.Image], Dict]:
    """
    Load a PDF from a file path and extract pages as images and metadata.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Tuple of (list of page images, metadata dictionary)
    """
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        # Extract basic metadata
        metadata = {
            "title": doc.metadata.get("title", "Unknown Title"),
            "author": doc.metadata.get("author", "Unknown Author"),
            "page_count": len(doc),
            "filename": os.path.basename(pdf_path)
        }
        
        # Extract pages as images
        page_images = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            page_images.append(img)
            
        return page_images, metadata
        
    except Exception as e:
        raise Exception(f"Error loading PDF: {str(e)}")


def load_pdf_from_arxiv(arxiv_id: str) -> Tuple[List[Image.Image], Dict]:
    """
    Download and load a PDF from arXiv using its ID.
    
    Args:
        arxiv_id: arXiv identifier (e.g., '2303.08774')
        
    Returns:
        Tuple of (list of page images, metadata dictionary)
    """
    try:
        # Strip version number if present
        base_id = arxiv_id.split('v')[0] if 'v' in arxiv_id else arxiv_id
        
        # Search for the paper
        search = arxiv.Search(id_list=[base_id])
        paper = next(search.results())
        
        # Create a temporary file to save the PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            paper.download_pdf(tmp.name)
            tmp_path = tmp.name
        
        # Load the PDF
        page_images, file_metadata = load_pdf_from_path(tmp_path)
        
        # Add arXiv metadata
        metadata = {
            "title": paper.title,
            "author": ', '.join(paper.authors),
            "abstract": paper.summary,
            "url": paper.pdf_url,
            "published": paper.published.strftime("%Y-%m-%d"),
            "arxiv_id": arxiv_id,
            "page_count": file_metadata["page_count"]
        }
        
        # Clean up the temporary file
        os.unlink(tmp_path)
        
        return page_images, metadata
        
    except Exception as e:
        raise Exception(f"Error loading PDF from arXiv: {str(e)}")


def load_pdf_from_url(url: str) -> Tuple[List[Image.Image], Dict]:
    """
    Download and load a PDF from a URL.
    
    Args:
        url: URL to the PDF file
        
    Returns:
        Tuple of (list of page images, metadata dictionary)
    """
    try:
        # Create a temporary file to save the PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            # Download the PDF
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Save the PDF to the temporary file
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            
            tmp_path = tmp.name
        
        # Load the PDF
        page_images, metadata = load_pdf_from_path(tmp_path)
        
        # Add URL to metadata
        metadata["url"] = url
        
        # Clean up the temporary file
        os.unlink(tmp_path)
        
        return page_images, metadata
        
    except Exception as e:
        raise Exception(f"Error loading PDF from URL: {str(e)}")


def encode_image_for_api(image: Image.Image) -> str:
    """
    Encode an image as base64 for API requests.
    
    Args:
        image: PIL Image object
        
    Returns:
        Base64 encoded string
    """
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')