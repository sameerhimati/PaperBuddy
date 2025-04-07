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
        extract_sections = st.checkbox("Extract Paper Sections", value=True)
        identify_terminology = st.checkbox("Identify Key Terminology", value=True)
        score_sections = st.checkbox("Score Section Importance", value=True)
        
        # Process the PDF
        if st.button("Process Paper"):
            with st.spinner("Processing paper..."):
                try:
                    # Process based on selected options
                    results = process_paper(
                        str(file_path), 
                        extract_sections, 
                        identify_terminology, 
                        score_sections
                    )
                    
                    # Store the results in session state
                    st.session_state['paper_results'] = results
                    st.session_state['paper_id'] = uploaded_file.name
                    
                    st.success("Paper processed successfully!")
                    st.markdown("Go to the **Paper Analysis** page to view the results.")
                except Exception as e:
                    st.error(f"Error processing paper: {str(e)}")

def process_paper(pdf_path, extract_sections=True, identify_terminology=True, score_sections=True):
    """Process the paper based on selected options"""
    results = {'pdf_path': pdf_path}
    
    # Extract document structure
    extractor = PDFExtractor(pdf_path)
    document_structure = extractor.get_document_structure()
    results['document_structure'] = document_structure
    
    # Get sections
    sections = document_structure.get('sections', {})
    
    # Extract terminology if selected
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
    tab1, tab2, tab3 = st.tabs(["Paper Sections", "Terminology", "Section Importance"])
    
    # Tab 1: Paper Sections
    with tab1:
        sections = document_structure.get('sections', {})
        if sections:
            st.subheader("Paper Sections")
            section_titles = list(sections.keys())
            selected_section = st.selectbox("Select a section to view:", section_titles)
            st.markdown(f"### {selected_section}")
            st.markdown(sections[selected_section])
        else:
            st.info("No sections were extracted from this paper.")
    
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