import streamlit as st
import tempfile
import time
import os
from PIL import Image
import io

# Import utility modules
from utils.paper_import import load_pdf_from_path, load_pdf_from_arxiv, load_pdf_from_url
from utils.ai_analysis import analyze_paper_with_gemini
from utils.display import (
    display_progress_bar, 
    simulate_progress,
    display_paper_metadata, 
    display_analysis_results
)
from config import ACTIVE_MODEL, DEBUG

# Set page configuration
st.set_page_config(
    page_title="PaperBuddy - AI Paper Analysis",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# App title and description
st.title("📚 PaperBuddy")
st.markdown(
    """
    Analyze academic papers with AI to extract key insights, techniques, and practical value.
    """
)

# Initialize session state
if 'paper_images' not in st.session_state:
    st.session_state.paper_images = None
if 'paper_metadata' not in st.session_state:
    st.session_state.paper_metadata = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'analysis_type' not in st.session_state:
    st.session_state.analysis_type = "comprehensive"

# Sidebar for input options
with st.sidebar:
    st.header("Paper Input")
    
    input_option = st.radio(
        "Select input method:",
        ["Upload PDF", "arXiv ID", "PDF URL"]
    )
    
    # Input form based on selected option
    if input_option == "Upload PDF":
        uploaded_file = st.file_uploader("Upload a PDF paper", type=["pdf"])
        
        if uploaded_file is not None:
            # Save uploaded file to temp location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            
            if st.button("Load Paper"):
                with st.spinner("Loading PDF..."):
                    try:
                        st.session_state.paper_images, st.session_state.paper_metadata = load_pdf_from_path(tmp_path)
                        st.success(f"Successfully loaded {st.session_state.paper_metadata.get('title', 'paper')}")
                    except Exception as e:
                        st.error(f"Error loading PDF: {str(e)}")
                    finally:
                        # Clean up temp file
                        os.unlink(tmp_path)
    
    elif input_option == "arXiv ID":
        arxiv_id = st.text_input("Enter arXiv ID (e.g., 2303.08774)")
        
        if arxiv_id and st.button("Fetch Paper"):
            with st.spinner("Fetching from arXiv..."):
                try:
                    st.session_state.paper_images, st.session_state.paper_metadata = load_pdf_from_arxiv(arxiv_id)
                    st.success(f"Successfully loaded {st.session_state.paper_metadata.get('title', 'paper')}")
                except Exception as e:
                    st.error(f"Error fetching from arXiv: {str(e)}")
    
    elif input_option == "PDF URL":
        pdf_url = st.text_input("Enter PDF URL")
        
        if pdf_url and st.button("Fetch Paper"):
            with st.spinner("Downloading from URL..."):
                try:
                    st.session_state.paper_images, st.session_state.paper_metadata = load_pdf_from_url(pdf_url)
                    st.success(f"Successfully loaded {st.session_state.paper_metadata.get('title', 'paper')}")
                except Exception as e:
                    st.error(f"Error downloading PDF: {str(e)}")
    
    # Analysis options
    if st.session_state.paper_images is not None:
        st.header("Analysis Options")
        
        st.session_state.analysis_type = st.selectbox(
            "Analysis Type",
            ["comprehensive", "key_insights", "techniques", "practical_value"],
            format_func=lambda x: {
                "comprehensive": "Comprehensive Analysis",
                "key_insights": "Key Insights",
                "techniques": "Techniques & Methods",
                "practical_value": "Practical Value Assessment"
            }.get(x, x)
        )
        
        force_pro = st.checkbox("Force Pro Model", value=False, 
                              help="Use the more powerful Pro model even if it's not automatically selected")
        
        if st.button("Analyze Paper"):
            progress_text, progress_bar = display_progress_bar()
            
            # Perform analysis
            try:
                simulate_progress(progress_text, progress_bar)
                
                st.session_state.analysis_results = analyze_paper_with_gemini(
                    st.session_state.paper_images,
                    st.session_state.paper_metadata,
                    st.session_state.analysis_type,
                    force_pro
                )
                
                progress_text.text("Analysis complete!")
                progress_bar.progress(1.0)
                
            except Exception as e:
                progress_text.empty()
                progress_bar.empty()
                st.error(f"Error analyzing paper: {str(e)}")

# Main content area
if st.session_state.paper_metadata is not None:
    display_paper_metadata(st.session_state.paper_metadata)
    
    # Preview of first page
    if st.session_state.paper_images:
        with st.expander("Paper Preview", expanded=False):
            st.image(
                st.session_state.paper_images[0], 
                caption=f"First page of {st.session_state.paper_metadata.get('title', 'paper')}",
                use_column_width=True
            )
    
    # Display analysis results if available
    if st.session_state.analysis_results is not None:
        st.markdown("---")
        st.header("Analysis Results")
        display_analysis_results(st.session_state.analysis_results)

# Debug information
if DEBUG:
    with st.expander("Debug Information", expanded=False):
        st.write("Active Model:", ACTIVE_MODEL)
        st.write("Session State Keys:", list(st.session_state.keys()))
        if st.session_state.paper_metadata:
            st.write("Paper Metadata:", st.session_state.paper_metadata)
        if st.session_state.paper_images:
            st.write("Number of Pages:", len(st.session_state.paper_images))