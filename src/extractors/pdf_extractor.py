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
    
    def extract_sections(self):
        """
        Extract the document's sections based on headings.
        
        Returns:
            dict: Dictionary of sections with their text content
                {section_title: section_text}
        """
        if not self.document:
            success = self.load_document()
            if not success:
                return {}
        
        # Get structured text and headings
        structured_pages = self.extract_structured_text()
        potential_headings = self.identify_potential_headings(structured_pages)
        
        # Sort headings by page and vertical position (y-coordinate)
        sorted_headings = sorted(potential_headings, 
                                key=lambda h: (h["page"], h["bbox"][1]))
        
        sections = {}
        
        # If no headings were found, treat the entire document as one section
        if not sorted_headings:
            sections["Document"] = self.extract_text()
            return sections
        
        # Process each heading and extract the text until the next heading
        for i in range(len(sorted_headings)):
            current_heading = sorted_headings[i]
            heading_text = current_heading["text"].strip()
            
            # Skip if heading is empty or just whitespace
            if not heading_text:
                continue
            
            # Determine the range of text to extract
            start_page = current_heading["page"]
            start_y = current_heading["bbox"][3]  # Bottom of the heading
            
            # If this is the last heading, extract until the end of the document
            if i == len(sorted_headings) - 1:
                end_page = len(self.document) - 1
                end_y = float('inf')
            else:
                # Otherwise, extract until the next heading
                next_heading = sorted_headings[i + 1]
                end_page = next_heading["page"]
                end_y = next_heading["bbox"][1]  # Top of the next heading
            
            # Extract the text for this section
            section_text = ""
            
            for page_num in range(start_page, end_page + 1):
                page = self.document[page_num]
                
                # For the starting page, only get text below the heading
                if page_num == start_page:
                    # We use a custom dictionary extraction and filter by position
                    blocks = page.get_text("dict")["blocks"]
                    for block in blocks:
                        if "lines" in block:
                            for line in block["lines"]:
                                # Check if the line is below the heading
                                if line["bbox"][1] >= start_y:
                                    for span in line["spans"]:
                                        section_text += span["text"] + " "
                                    section_text += "\n"
                
                # For the ending page, only get text above the next heading
                elif page_num == end_page and end_y != float('inf'):
                    blocks = page.get_text("dict")["blocks"]
                    for block in blocks:
                        if "lines" in block:
                            for line in block["lines"]:
                                # Check if the line is above the next heading
                                if line["bbox"][3] <= end_y:
                                    for span in line["spans"]:
                                        section_text += span["text"] + " "
                                    section_text += "\n"
                
                # For pages in between, get all text
                else:
                    section_text += page.get_text()
            
            sections[heading_text] = section_text.strip()
        
        return sections
    
    def get_document_structure(self):
        """
        Get the complete structure of the document including metadata, sections, and potential figures.
        
        Returns:
            dict: Document structure with metadata and content
        """
        if not self.document:
            success = self.load_document()
            if not success:
                return {}
        
        # Get basic metadata
        metadata = {
            "title": self.document.metadata.get("title", ""),
            "author": self.document.metadata.get("author", ""),
            "subject": self.document.metadata.get("subject", ""),
            "keywords": self.document.metadata.get("keywords", ""),
            "page_count": len(self.document),
            "file_path": self.pdf_path
        }
        
        # Get sections
        sections = self.extract_sections()
        
        # Basic detection of potential figures (areas with images or dense graphics)
        potential_figures = []
        for page_num in range(len(self.document)):
            page = self.document[page_num]
            img_list = page.get_images()
            
            for img in img_list:
                xref = img[0]  # Image reference number
                try:
                    base_image = self.document.extract_image(xref)
                    if base_image:
                        potential_figures.append({
                            "page": page_num,
                            "xref": xref,
                            "bbox": page.get_image_bbox(xref)
                        })
                except Exception:
                    # Some images might be problematic to extract
                    pass
        
        return {
            "metadata": metadata,
            "sections": sections,
            "potential_figures": potential_figures
        }