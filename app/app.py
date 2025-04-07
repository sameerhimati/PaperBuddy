import streamlit as st
import os
import tempfile
import uuid
from pathlib import Path
import sys

# Set environment variables
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Add the parent directory to the path to import from src
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import after setting path
from src.extractors import PDFExtractor, TerminologyExtractor, SectionScorer

# Set page configuration
st.set_page_config(
    page_title="PaperBuddy - NLP Paper Analysis",
    page_icon="📄",
    layout="wide"
)

# Create a session ID if not already present
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = str(uuid.uuid4())

# Create a temporary directory for this session
temp_dir = Path(tempfile.gettempdir()) / f"paperbuddy_{st.session_state['session_id']}"
temp_dir.mkdir(exist_ok=True)

def main():
    # Sidebar navigation
    st.sidebar.title("PaperBuddy")
    st.sidebar.markdown("---")
    
    # Navigation options
    page = st.sidebar.selectbox(
        "Choose a page:", 
        ["Upload & Process", "Paper Analysis", "About"]
    )
    
    # Display the selected page
    if page == "Upload & Process":
        upload_page()
    elif page == "Paper Analysis":
        analysis_page()
    else:
        about_page()

def upload_page():
    st.title("Upload Academic Paper")
    st.write("Upload a PDF of an academic paper to analyze its content using NLP techniques.")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        # Save the uploaded file to our temp directory
        file_path = temp_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        # Display options for processing
        st.subheader("Processing Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Extraction Options**")
            extract_sections = st.checkbox("Extract Paper Sections", value=True)
            identify_terminology = st.checkbox("Identify Key Terminology", value=True)
            score_sections = st.checkbox("Score Section Importance", value=True)
        
        with col2:
            st.write("**Advanced Options**")
            use_llm = st.checkbox("Use LLM for Enhanced Extraction", value=True)
            llm_model = st.selectbox(
                "Select LLM Model:",
                ["google/gemma-3-4b-it", "google/gemma-3-1b-it", "google/gemma-3-12b-it"],
                disabled=not use_llm
            )
        
        # Process the PDF
        if st.button("Process Paper"):
            with st.spinner("Processing paper..."):
                try:
                    # Update session state with model choice
                    st.session_state['llm_model'] = llm_model if use_llm else None
                    
                    # Process based on selected options
                    results = process_paper(
                        str(file_path), 
                        extract_sections, 
                        identify_terminology, 
                        score_sections,
                        use_llm=use_llm,
                        llm_model=llm_model if use_llm else None
                    )
                    
                    # Store the results in session state
                    st.session_state['paper_results'] = results
                    st.session_state['paper_id'] = uploaded_file.name
                    
                    st.success("Paper processed successfully!")
                    st.markdown("Go to the **Paper Analysis** page to view the results.")
                except Exception as e:
                    st.error(f"Error processing paper: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())

def process_paper(pdf_path, extract_sections=True, identify_terminology=True, score_sections=True, use_llm=False, llm_model=None):
    """Process the paper based on selected options"""
    results = {'pdf_path': pdf_path}
    
    # Extract document structure
    extractor = PDFExtractor(pdf_path)
    document_structure = extractor.get_document_structure()
    results['document_structure'] = document_structure
    
    # Get sections
    sections = document_structure.get('sections', {})
    
    # Extract full text for LLM processing
    full_text = extractor.extract_text()
    
    # Use LLM for enhanced extraction if selected
    if use_llm:
        try:
            from src.extractors import LLMExtractor
            llm = LLMExtractor(model_name=llm_model or "google/gemma-3-4b-it")
            
            # If traditional section extraction failed or produced poor results
            if extract_sections and (not sections or len(sections) <= 2):
                llm_sections_result = llm.extract_sections(full_text)
                llm_sections = llm_sections_result.get("sections", {})
                section_confidence = llm_sections_result.get("section_confidence", {})
                
                if llm_sections:
                    # Replace with LLM-extracted sections
                    document_structure['sections'] = llm_sections
                    document_structure['section_confidence'] = section_confidence
                    sections = llm_sections
                    results['document_structure'] = document_structure
            
            # Extract terminology with LLM if selected
            if identify_terminology:
                terminology_result = llm.extract_terminology(full_text)
                results['terminology'] = terminology_result
                # Skip traditional terminology extraction
                identify_terminology = False
                
        except Exception as e:
            st.warning(f"LLM extraction failed, falling back to traditional methods: {str(e)}")
            import traceback
            st.warning(traceback.format_exc())
    
    # Extract terminology using traditional method if not done by LLM
    if identify_terminology and sections:
        # Combine all text for terminology extraction
        all_text = " ".join(sections.values())
        terminology_extractor = TerminologyExtractor()
        terminology = terminology_extractor.extract_terminology(all_text)
        results['terminology'] = terminology
    
    # Score sections if selected
    if score_sections and sections:
        # Find abstract if available
        abstract = None
        for title, text in sections.items():
            if "abstract" in title.lower():
                abstract = text
                break
        
        # Score sections
        section_scorer = SectionScorer()
        paper_id = os.path.basename(pdf_path)
        section_scores = section_scorer.score_sections(
            paper_id, 
            sections, 
            abstract=abstract
        )
        results['section_scores'] = section_scores
    
    return results

def analysis_page():
    st.title("Paper Analysis")
    
    if 'paper_results' not in st.session_state:
        st.info("Please upload and process a paper first.")
        return
    
    # Get the results from session state
    results = st.session_state['paper_results']
    document_structure = results.get('document_structure', {})
    
    # Display paper metadata
    st.header("Paper Information")
    metadata = document_structure.get('metadata', {})
    st.write(f"**Title:** {metadata.get('title', 'Not available')}")
    st.write(f"**Author:** {metadata.get('author', 'Not available')}")
    st.write(f"**Pages:** {metadata.get('page_count', 0)}")
    
    # Tabs for different analysis views
    tab1, tab2, tab3 = st.tabs(["Interactive Paper View", "Terminology", "Section Importance"])
    
    # Tab 1: Interactive Paper View with PDF
    with tab1:
        sections = document_structure.get('sections', {})
        section_confidence = document_structure.get('section_confidence', {})
        terminology = results.get('terminology', {'terms': [], 'definitions': {}})
        
        # Convert section scores to correct format for the viewer
        section_scores = {}
        if 'section_scores' in results:
            for section, score_info in results['section_scores'].items():
                section_scores[section] = score_info
        
        # Use two columns for PDF and interactive content
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("PDF Document")
            pdf_path = results['pdf_path']
            from components.pdf_viewer import render_pdf
            render_pdf(pdf_path)
        
        with col2:
            st.subheader("Section Content")
            if sections and section_scores:
                # Check if we have confidence data from LLM
                has_confidence = len(section_confidence) > 0
                if has_confidence:
                    st.info("Content extracted with AI assistance. Confidence scores are shown for each section.")
                
                from components.pdf_viewer import display_interactive_text
                display_interactive_text(sections, terminology, section_scores, section_confidence if has_confidence else None)
            else:
                st.info("Section data not available for interactive view.")
    
    # Tab 2: Terminology
    with tab2:
        if 'terminology' in results:
            terminology = results['terminology']
            terms = terminology.get('terms', [])
            definitions = terminology.get('definitions', {})
            
            st.subheader("Key Terminology")
            
            # Display terms in a table
            if terms:
                term_data = []
                for term_info in terms:
                    term = term_info['term']
                    definition = definitions.get(term, "No definition found")
                    term_data.append({"Term": term, "Definition": definition})
                
                st.table(term_data)
            else:
                st.info("No terminology was extracted from this paper.")
        else:
            st.info("Terminology extraction was not selected during processing.")
    
    # Tab 3: Section Importance
    with tab3:
        if 'section_scores' in results:
            section_scores = results['section_scores']
            
            st.subheader("Section Importance Scores")
            
            # Create a dataframe for display
            import pandas as pd
            score_data = []
            for section, score_info in section_scores.items():
                score_data.append({
                    "Section": section,
                    "Importance Score": f"{score_info['score']:.2f}",
                    "Score Sources": ", ".join(score_info['sources'].keys())
                })
            
            score_df = pd.DataFrame(score_data)
            st.dataframe(score_df.sort_values(by="Importance Score", ascending=False))
            
            # User feedback option
            st.subheader("Provide Feedback on Section Importance")
            feedback_section = st.selectbox(
                "Select a section to rate:", 
                [row["Section"] for row in score_data]
            )
            feedback_score = st.slider(
                "Rate the importance of this section:", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.5, 
                step=0.1
            )
            
            if st.button("Submit Feedback"):
                paper_id = st.session_state['paper_id']
                section_scorer = SectionScorer()
                success = section_scorer.add_user_feedback(
                    paper_id, 
                    feedback_section, 
                    feedback_score
                )
                if success:
                    st.success("Feedback submitted successfully!")
                else:
                    st.error("Failed to submit feedback.")
        else:
            st.info("Section scoring was not selected during processing.")

def about_page():
    st.title("About PaperBuddy")
    st.write("""
    PaperBuddy is an application that uses modern NLP techniques to help researchers 
    analyze, understand, and extract insights from academic papers.
    
    ### Features
    - Extract and structure content from academic PDFs
    - Apply NLP techniques to identify key terminology and concepts
    - Score and highlight important sections for focused reading
    - Incorporate user feedback to improve scoring
    
    ### How It Works
    1. **Upload** your academic paper in PDF format
    2. **Process** the paper using NLP techniques
    3. **Explore** the extracted sections, terminology, and importance scores
    4. **Provide feedback** to help improve the section scoring
    """)

if __name__ == "__main__":
    main()