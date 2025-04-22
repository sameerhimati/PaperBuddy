import streamlit as st
import tempfile
import time
import os
import json
from datetime import datetime
from PIL import Image
import io
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utility modules
from utils.paper_import import load_pdf_from_path, load_pdf_from_arxiv, load_pdf_from_url
from utils.ai_analysis import analyze_paper_with_gemini
from utils.display import (
    display_progress_bar, 
    simulate_progress,
    display_paper_metadata, 
    display_analysis_results
)
from config import ACTIVE_MODEL, DEFAULT_MODEL, ALTERNATE_MODEL, PRO_MODEL, FALLBACK_MODEL, DEBUG

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
if 'show_all_sections' not in st.session_state:
    st.session_state.show_all_sections = False

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
        
        # Add model selector
        model_choice = st.selectbox(
            "Select Model",
            ["Default", "Pro", "Alternate", "Fallback"],
            help="Choose which Gemini model to use for analysis"
        )
        
        force_pro = False
        if model_choice == "Pro":
            force_pro = True
            st.info(f"Using model: {PRO_MODEL}")
        elif model_choice == "Alternate":
            st.info(f"Using model: {ALTERNATE_MODEL}")
        elif model_choice == "Fallback":
            st.info(f"Using model: {FALLBACK_MODEL}")
        else:
            st.info(f"Using model: {DEFAULT_MODEL}")
        
        # Display all sections option
        st.session_state.show_all_sections = st.checkbox(
            "Expand All Sections", 
            value=st.session_state.show_all_sections,
            help="Show all sections of the analysis expanded"
        )
        
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
                
                # Check if we got an error from the API call
                if "error" in st.session_state.analysis_results:
                    progress_text.empty()
                    progress_bar.empty()
                    st.error(f"Error analyzing paper: {st.session_state.analysis_results['error']}")
                else:
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
                use_container_width=True
            )
    
    # Display analysis results if available
    if st.session_state.analysis_results is not None:
        st.markdown("---")
        st.header("Analysis Results")
        
        # Add a download button for the analysis results
        if "raw_analysis" in st.session_state.analysis_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            paper_title = st.session_state.paper_metadata.get('title', 'paper').replace(" ", "_")[:30]
            filename = f"{paper_title}_{timestamp}_analysis.md"
            
            analysis_text = st.session_state.analysis_results.get("raw_analysis", "")
            
            # Create download button
            st.download_button(
                label="📥 Download Analysis",
                data=analysis_text,
                file_name=filename,
                mime="text/markdown",
            )
        
        display_analysis_results(st.session_state.analysis_results, expand_all=st.session_state.show_all_sections)

# Debug information
if DEBUG:
    with st.expander("Debug Information", expanded=False):
        st.write("Active Model:", ACTIVE_MODEL)
        st.write("Session State Keys:", list(st.session_state.keys()))
        
        if st.session_state.paper_metadata:
            st.write("Paper Metadata:", st.session_state.paper_metadata)
        
        if st.session_state.paper_images:
            st.write("Number of Pages:", len(st.session_state.paper_images))
            
        if st.session_state.analysis_results:
            if st.checkbox("Show Raw Analysis Results"):
                st.json(st.session_state.analysis_results)