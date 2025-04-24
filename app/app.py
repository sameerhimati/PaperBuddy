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
from utils.ai_analysis import analyze_paper_with_gemini, get_field_tags, extract_metadata_from_pdf
from utils.display import (display_paper_metadata, display_analysis_results, 
                          display_key_definitions, display_analysis_type_tabs,
                          display_past_analyses)
from config import ACTIVE_MODEL, DEFAULT_MODEL, ALTERNATE_MODEL, PRO_MODEL, FALLBACK_MODEL, DEBUG

# Set page configuration
st.set_page_config(
    page_title="PaperBuddy - AI Paper Analysis",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add custom CSS for cleaner UI
st.markdown("""
<style>
    /* Cleaner tab styling */
    .tab-container {
        display: flex;
        border-bottom: 1px solid rgba(49, 51, 63, 0.2);
        margin-bottom: 1rem;
    }
    .tab {
        padding: 0.5rem 1rem;
        cursor: pointer;
        transition: all 0.3s;
    }
    .tab:hover {
        background-color: rgba(28, 131, 225, 0.05);
    }
    .tab.active {
        border-bottom: 2px solid rgba(28, 131, 225, 0.8);
        font-weight: bold;
    }
    
    /* Analysis type card styling */
    .analysis-type-card {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 5px;
        padding: 10px;
        transition: all 0.3s;
        height: 100%;
    }
    .analysis-type-card:hover {
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }
    .analysis-type-card.active {
        border-color: rgba(28, 131, 225, 0.8);
        background-color: rgba(28, 131, 225, 0.05);
    }
    
    /* Hide "Selected:" text */
    .hide-label .st-emotion-cache-1gulkj5 {
        display: none;
    }
    
    /* Clean divider */
    .divider {
        height: 1px;
        background-color: rgba(49, 51, 63, 0.2);
        margin: 1rem 0;
    }
    
    /* Field tag styling */
    .field-tag {
        display: inline-block;
        background-color: rgba(28, 131, 225, 0.1);
        padding: 0.2rem 0.6rem;
        border-radius: 1rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'paper_images' not in st.session_state:
    st.session_state.paper_images = None
if 'paper_metadata' not in st.session_state:
    st.session_state.paper_metadata = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'past_analyses' not in st.session_state:
    st.session_state.past_analyses = {}  # Store past analyses by type
if 'analysis_type' not in st.session_state:
    st.session_state.analysis_type = "comprehensive"
if 'show_all_sections' not in st.session_state:
    st.session_state.show_all_sections = False
if 'user_api_key' not in st.session_state:
    st.session_state.user_api_key = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'show_preview' not in st.session_state:
    st.session_state.show_preview = False  # Default to not showing preview
if 'simplified_view' not in st.session_state:
    st.session_state.simplified_view = False
if 'field_tags' not in st.session_state:
    st.session_state.field_tags = {}
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "analysis"  # Default to analysis tab
if 'model_choice' not in st.session_state:
    st.session_state.model_choice = "Default"

# Define callback for analysis type change
def on_analysis_type_change(new_type):
    st.session_state.analysis_type = new_type
    st.session_state.simplified_view = (new_type == "simplified")
    
    # Check if we already have this analysis type
    if new_type in st.session_state.past_analyses:
        st.session_state.analysis_results = st.session_state.past_analyses[new_type]
        st.rerun()

# Define callback for showing past analysis
def on_past_analysis_select(analysis_type):
    st.session_state.analysis_type = analysis_type
    st.session_state.simplified_view = (analysis_type == "simplified")
    st.session_state.analysis_results = st.session_state.past_analyses[analysis_type]
    st.rerun()

# Function to show analysis panel 
def show_analysis_panel():
    # Analysis type selection
    st.markdown("### Analysis Type")
    
    # Analysis type descriptions
    analysis_types = {
        "comprehensive": {
            "title": "Comprehensive Analysis",
            "description": "Complete academic review with summary, innovations, techniques, and limitations",
            "icon": "📊",
            "for": "Researchers and academics"
        },
        "quick_summary": {
            "title": "Quick Summary",
            "description": "Brief overview with key points in bullet format",
            "icon": "⏱️",
            "for": "Busy readers needing essentials"
        },
        "technical": {
            "title": "Technical Deep Dive",
            "description": "Detailed analysis of algorithms, methods, and implementation details",
            "icon": "🔬",
            "for": "Engineers and developers"
        },
        "practical": {
            "title": "Practical Applications",
            "description": "Focus on real-world use cases and industry relevance",
            "icon": "🛠️",
            "for": "Industry professionals"
        },
        "simplified": {
            "title": "Explain Like I'm 5",
            "description": "Simplified explanation using everyday language and analogies",
            "icon": "👶",
            "for": "Non-experts and students"
        }
    }
    
    # Display analysis type options as visual cards
    display_analysis_type_tabs(
        analysis_types,
        st.session_state.analysis_type,
        on_change_callback=on_analysis_type_change
    )
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    
    # Check if we already have this analysis type
    has_cached_analysis = st.session_state.analysis_type in st.session_state.past_analyses
    
    # Analysis button - full width since model selection is now in sidebar
    button_text = "📋 Use Existing Analysis" if has_cached_analysis else "🚀 Analyze Paper"
    
    if st.button(button_text, use_container_width=True, type="primary", help="Run analysis with Gemini AI"):
        if has_cached_analysis:
            # Just retrieve cached analysis
            st.session_state.analysis_results = st.session_state.past_analyses[st.session_state.analysis_type]
        else:
            # Run new analysis
            st.session_state.processing = True
    
    # Handle analysis processing
    if st.session_state.processing:
        # Progress indicators
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simulate progress updates
            for i in range(10):
                progress = (i + 1) / 10
                progress_bar.progress(progress)
                
                if i < 3:
                    status_text.text("Preparing paper content...")
                elif i < 6:
                    status_text.text("Processing with Gemini AI...")
                else:
                    status_text.text("Organizing results...")
                
                time.sleep(0.2)
            
            # Actual analysis
            force_pro = st.session_state.model_choice == "Pro"
            try:
                st.session_state.analysis_results = analyze_paper_with_gemini(
                    st.session_state.paper_images,
                    st.session_state.paper_metadata,
                    st.session_state.analysis_type,
                    force_pro,
                    api_key=st.session_state.user_api_key,
                    simplified=st.session_state.simplified_view
                )
                
                # Update progress indicators
                if "error" in st.session_state.analysis_results:
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"Error analyzing paper: {st.session_state.analysis_results['error']}")
                else:
                    progress_bar.progress(1.0)
                    status_text.text("Analysis complete!")
                    time.sleep(1)
                    status_text.empty()
                    progress_bar.empty()
                    
                    # Store this analysis for later use
                    st.session_state.past_analyses[st.session_state.analysis_type] = st.session_state.analysis_results
                    
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Error analyzing paper: {str(e)}")
            
            st.session_state.processing = False
            st.rerun()
    
    # Display analysis results if available
    if st.session_state.analysis_results is not None:
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        
        # Display compact model info
        model_used = st.session_state.analysis_results.get('model_used', 'Unknown model')
        processing_time = st.session_state.analysis_results.get('processing_time', 0)
        st.caption(f"Analysis by {model_used} | {processing_time:.1f} seconds")
        
        # Add download button for the analysis
        if "raw_analysis" in st.session_state.analysis_results:
            col1, col2, col3 = st.columns([2, 2, 1])
            with col3:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                paper_title = st.session_state.paper_metadata.get('title', 'paper').replace(" ", "_")[:30]
                filename = f"{paper_title}_{timestamp}_analysis.md"
                
                analysis_text = st.session_state.analysis_results.get("raw_analysis", "")
                
                st.download_button(
                    label="📥 Download",
                    data=analysis_text,
                    file_name=filename,
                    mime="text/markdown",
                    use_container_width=True
                )
        
        # Use improved display function with native Streamlit tabs
        display_analysis_results(
            st.session_state.analysis_results, 
            expand_all=False,  # Don't expand all sections by default
            simplified=st.session_state.simplified_view,
            display_mode="tabs",
            show_definitions=True
        )

# App title and branding
st.title("📚 PaperBuddy")

# Only keep API configuration and advanced options in sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Toggle for paper preview
    st.session_state.show_preview = st.toggle("Show Paper Preview", value=st.session_state.show_preview)
    
    # Model selection moved to sidebar
    st.markdown("### Model Selection")
    models = {
        "Default": f"Standard ({DEFAULT_MODEL.split('-')[0]}-{DEFAULT_MODEL.split('-')[1]})",
        "Pro": f"Best quality (requires API key)",
        "Alternate": f"Balanced",
        "Fallback": f"Most stable"
    }
    
    st.session_state.model_choice = st.selectbox(
        "Select Model",
        list(models.keys()),
        format_func=lambda x: models.get(x, x),
        index=list(models.keys()).index(st.session_state.model_choice) if st.session_state.model_choice in models else 0,
        help="Choose which Gemini model to use for analysis"
    )
    
    force_pro = st.session_state.model_choice == "Pro"
    
    # Check if Pro model is selected but no API key provided
    if force_pro and not st.session_state.user_api_key:
        st.warning("⚠️ Pro model requires your API key.")
    
    # API Key Configuration
    with st.expander("API Configuration", expanded=False):
        user_api_key = st.text_input(
            "Your Gemini API Key (optional)",
            type="password",
            help="Provide your own API key for analysis"
        )
        
        if user_api_key:
            st.session_state.user_api_key = user_api_key
            st.success("API key saved for this session")
        
        st.markdown("""
        *Need an API key?* [Get one here](https://aistudio.google.com/app/apikey)
        """)
    
    # Debug information (if enabled)
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

# Main content area - initial state
if st.session_state.paper_metadata is None:
    # First-time user state - show welcome screen with import options
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("""
        ## Welcome to PaperBuddy! 👋
        
        PaperBuddy helps you analyze academic papers using AI to extract:
        
        * Key insights and contributions
        * Technical methods and approaches
        * Practical applications and limitations
        * Simplified explanations for non-experts
        * Important terminology and definitions
        
        **Get started by uploading or importing a paper →**
        """)
    
    with col2:
        st.markdown("### Import Paper")
        
        # Tab-based input method selection
        tab1, tab2, tab3 = st.tabs(["Upload PDF", "arXiv ID", "PDF URL"])
        
        with tab1:
            uploaded_file = st.file_uploader("Upload a PDF paper", type=["pdf"])
            
            if uploaded_file is not None:
                with st.spinner("Loading PDF..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name
                    
                    try:
                        st.session_state.paper_images, st.session_state.paper_metadata = load_pdf_from_path(tmp_path)
                        
                        # Check if title is bad (ISBN or too short) and try to fix with LLM
                        paper_title = st.session_state.paper_metadata.get('title', '')
                        if paper_title.replace("-", "").isdigit() or len(paper_title) < 5:
                            with st.spinner("Extracting paper details..."):
                                better_metadata = extract_metadata_from_pdf(
                                    st.session_state.paper_images,
                                    st.session_state.user_api_key
                                )
                                st.session_state.paper_metadata.update(better_metadata)
                        
                        st.success(f"Successfully loaded paper")
                        
                        # Reset field tags and past analyses when loading a new paper
                        st.session_state.field_tags = {}
                        st.session_state.past_analyses = {}
                        st.session_state.analysis_results = None
                        
                        # Rerun to update the UI
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error loading PDF: {str(e)}")
                    finally:
                        os.unlink(tmp_path)
        
        with tab2:
            arxiv_id = st.text_input("Enter arXiv ID (e.g., 2303.08774)", placeholder="2303.08774")
            fetch_button = st.button("Fetch Paper", key="fetch_arxiv")
            
            if arxiv_id and fetch_button:
                with st.spinner("Fetching from arXiv..."):
                    try:
                        st.session_state.paper_images, st.session_state.paper_metadata = load_pdf_from_arxiv(arxiv_id)
                        st.success(f"Successfully loaded paper")
                        
                        # Reset field tags and past analyses when loading a new paper
                        st.session_state.field_tags = {}
                        st.session_state.past_analyses = {}
                        st.session_state.analysis_results = None
                        
                        # Rerun to update the UI
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error fetching from arXiv: {str(e)}")
        
        with tab3:
            pdf_url = st.text_input("Enter PDF URL", placeholder="https://example.com/paper.pdf")
            url_button = st.button("Fetch Paper", key="fetch_url")
            
            if pdf_url and url_button:
                with st.spinner("Downloading from URL..."):
                    try:
                        st.session_state.paper_images, st.session_state.paper_metadata = load_pdf_from_url(pdf_url)
                        
                        # Check if title is bad (ISBN or too short) and try to fix with LLM
                        paper_title = st.session_state.paper_metadata.get('title', '')
                        if paper_title.replace("-", "").isdigit() or len(paper_title) < 5:
                            with st.spinner("Extracting paper details..."):
                                better_metadata = extract_metadata_from_pdf(
                                    st.session_state.paper_images,
                                    st.session_state.user_api_key
                                )
                                st.session_state.paper_metadata.update(better_metadata)
                        
                        st.success(f"Successfully loaded paper")
                        
                        # Reset field tags and past analyses when loading a new paper
                        st.session_state.field_tags = {}
                        st.session_state.past_analyses = {}
                        st.session_state.analysis_results = None
                        
                        # Rerun to update the UI
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error downloading PDF: {str(e)}")

# Paper loaded state
else:
    # Paper info header
    col1, col2 = st.columns([3, 1])
    
    with col1:
        paper_title = st.session_state.paper_metadata.get('title', 'Unknown Title')
        st.markdown(f"## {paper_title}")
        
        # Paper metadata in a clean format
        authors = st.session_state.paper_metadata.get('author', 'Unknown Author')
        pages = st.session_state.paper_metadata.get('page_count', 'Unknown')
        
        st.markdown(f"**Authors:** {authors} | **Pages:** {pages}")
    
    with col2:
        # Load different paper button
        if st.button("📄 Load Different Paper", type="secondary", use_container_width=True):
            # Reset session state and redirect to welcome screen
            st.session_state.paper_images = None
            st.session_state.paper_metadata = None
            st.session_state.analysis_results = None
            st.session_state.past_analyses = {}
            st.session_state.field_tags = {}
            st.rerun()
    
    # Display field tags if available
    if st.session_state.field_tags:
        # Create field tags with clean styling
        tag_html = "<div style='margin: 1rem 0;'>"
        for tag, info in st.session_state.field_tags.items():
            tag_html += f"<span class='field-tag'>{tag}</span>"
        tag_html += "</div>"
        
        st.markdown(tag_html, unsafe_allow_html=True)
        
        # Show field tag descriptions in an expander
        with st.expander("Field Descriptions", expanded=False):
            for tag, info in st.session_state.field_tags.items():
                if 'description' in info:
                    st.markdown(f"**{tag}**: {info['description']}")
                    if 'link' in info and info['link']:
                        st.markdown(f"[Learn more]({info['link']})")
    
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    
    # Native Streamlit tabs - show only if preview is enabled
    if st.session_state.show_preview:
        # Create tabs
        tab1, tab2 = st.tabs(["📄 Paper Preview", "🔍 Analysis"])
        
        with tab1:
            # Paper preview tab
            if st.session_state.paper_images:
                total_pages = len(st.session_state.paper_images)
                
                # Page navigation
                col_prev, col_page, col_next = st.columns([1, 3, 1])
                with col_prev:
                    if st.button("◀") and st.session_state.current_page > 0:
                        st.session_state.current_page -= 1
                with col_page:
                    # Fix the slider to show page numbers starting from 1
                    page_number = st.slider(
                        "Page", 
                        1, total_pages, 
                        st.session_state.current_page + 1
                    )
                    st.session_state.current_page = page_number - 1  # Convert back to 0-index for internal use
                with col_next:
                    if st.button("▶") and st.session_state.current_page < total_pages - 1:
                        st.session_state.current_page += 1
                
                # Display current page
                st.image(
                    st.session_state.paper_images[st.session_state.current_page], 
                    caption=f"Page {st.session_state.current_page + 1} of {total_pages}",
                    use_container_width=True
                )
                
                # Optional abstract in expander
                if 'abstract' in st.session_state.paper_metadata and st.session_state.paper_metadata['abstract']:
                    with st.expander("Abstract", expanded=False):
                        st.markdown(st.session_state.paper_metadata['abstract'])
        
        with tab2:
            # Analysis tab content
            show_analysis_panel()
    else:
        # If preview is disabled, just show analysis panel
        show_analysis_panel()

# Function to get field tags based on paper title and abstract
def get_field_tags_if_missing():
    if not st.session_state.field_tags and st.session_state.paper_metadata:
        # Get field tags based on title and abstract
        title = st.session_state.paper_metadata.get('title', '')
        abstract = st.session_state.paper_metadata.get('abstract', '')
        
        # Only process if we have enough text to analyze
        if len(title) > 5 and len(abstract) > 20:
            with st.spinner("Identifying research fields..."):
                st.session_state.field_tags = get_field_tags(
                    title, 
                    abstract,
                    api_key=st.session_state.user_api_key
                )

# Call the function to get field tags if they're missing
if st.session_state.paper_metadata is not None:
    get_field_tags_if_missing()