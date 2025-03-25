import fitz

class PDFExtractor:
    """
    Class to extract text and structure from PDF documents.
    """
    
    def __init__(self, pdf_path):
        """
        Initialize the PDF extractor with a path to a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
        """
        self.pdf_path = pdf_path
        self.document = None
        
    def load_document(self):
        """
        Load the PDF document.
        
        Returns:
            bool: True if document was loaded successfully, False otherwise
        """
        try:
            self.document = fitz.open(self.pdf_path)
            return True
        except Exception as e:
            print(f"Error loading PDF: {e}")
            return False
    
    def extract_text(self):
        """
        Extract all text from the PDF document.
        
        Returns:
            str: Extracted text from the PDF
        """
        if not self.document:
            success = self.load_document()
            if not success:
                return ""
        
        text = ""
        for page_num in range(len(self.document)):
            page = self.document[page_num]
            text += page.get_text()
        
        return text
    
    def extract_structured_text(self):
        """
        Extract text with structural information including position, font, and block data.
        
        Returns:
            list: List of pages, where each page is a list of blocks containing text and metadata
        """
        if not self.document:
            success = self.load_document()
            if not success:
                return []
        
        structured_pages = []
        
        for page_num in range(len(self.document)):
            page = self.document[page_num]
            
            # Get blocks which contain lines of text with position and font information
            blocks = page.get_text("dict")["blocks"]
            
            # Filter to only include text blocks (not images)
            text_blocks = []
            for block in blocks:
                if "lines" in block:
                    block_data = {
                        "bbox": block["bbox"],  # Bounding box coordinates [x0, y0, x1, y1]
                        "lines": []
                    }
                    
                    for line in block["lines"]:
                        line_text = ""
                        line_fonts = set()
                        line_sizes = set()
                        
                        # Extract text and font information from spans
                        for span in line["spans"]:
                            line_text += span["text"]
                            line_fonts.add(span["font"])
                            line_sizes.add(span["size"])
                        
                        block_data["lines"].append({
                            "text": line_text,
                            "bbox": line["bbox"],
                            "fonts": list(line_fonts),
                            "sizes": list(line_sizes)
                        })
                    
                    text_blocks.append(block_data)
            
            structured_pages.append(text_blocks)
        
        return structured_pages
    
    def identify_potential_headings(self, structured_pages):
        """
        Identify lines that are likely to be headings based on font size.
        
        Args:
            structured_pages (list): The result from extract_structured_text()
            
        Returns:
            list: List of potential headings with page number, text, and size
        """
        if not structured_pages:
            return []
        
        # Find all font sizes to determine what might be headings
        all_sizes = []
        for page_idx, page in enumerate(structured_pages):
            for block in page:
                for line in block["lines"]:
                    for size in line["sizes"]:
                        all_sizes.append(size)
        
        # If there are no sizes, return empty list
        if not all_sizes:
            return []
        
        # Calculate statistics to identify heading sizes
        # Typically, headings are larger than the most common font size
        most_common_size = max(set(all_sizes), key=all_sizes.count)
        
        # Consider a heading if size is at least 10% larger than most common size
        heading_threshold = most_common_size * 1.1
        
        potential_headings = []
        
        for page_idx, page in enumerate(structured_pages):
            for block in page:
                for line in block["lines"]:
                    # If any size in the line is larger than our threshold
                    if any(size > heading_threshold for size in line["sizes"]):
                        heading = {
                            "page": page_idx,
                            "text": line["text"],
                            "size": max(line["sizes"]),
                            "bbox": line["bbox"]
                        }
                        potential_headings.append(heading)
        
        return potential_headings