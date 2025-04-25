import streamlit as st
from streamlit.components.v1 import html as st_html
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
                          display_key_definitions, display_analysis_type_select,
                          display_paper_overview, get_analysis_type_description)
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
    
    /* Improved button contrast */
    div[data-testid="stButton"] > button {
        font-weight: 600;
    }
    
    /* Override for expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Remove extra padding around headers */
    h1, h2, h3, h4, h5, h6 {
        margin-top: 0.5rem !important;
    }
    
    /* Add space after analysis results */
    .stMarkdown {
        padding-bottom: 0.5rem;
    }
    
    /* Make container border more subtle */
    [data-testid="stDecoration"] {
        opacity: 0.2;
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
if 'key_definitions' not in st.session_state:
    st.session_state.key_definitions = {}
if 'model_choice' not in st.session_state:
    st.session_state.model_choice = "Default"

# Define callback for analysis type change
def on_analysis_type_change(new_type):
    if new_type != st.session_state.analysis_type:
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

def show_loading_status(message, progress_bar, progress_value):
    """Display loading status with progress bar"""
    progress_bar.progress(progress_value)
    return st.info(message)

# Function to extract key definitions from paper
def extract_key_definitions(paper_images, api_key=None):
    """Extract key terminology definitions from paper images"""
    try:
        # Simplified version just to extract terminology
        if not paper_images:
            return {}
            
        # Use Gemini to extract key terms
        force_pro = st.session_state.model_choice == "Pro"
        
        with st.spinner("Extracting key terminology..."):
            # Create a minimal analysis just for definitions
            definitions_analysis = analyze_paper_with_gemini(
                paper_images,
                st.session_state.paper_metadata,
                "terminology",  # Special mode just for terminology
                force_pro,
                api_key=api_key,
                simplified=False
            )
            
            if "key_definitions" in definitions_analysis:
                return definitions_analysis["key_definitions"]
            else:
                return {}
    except Exception as e:
        st.warning(f"Could not extract terminology automatically: {str(e)}")
        return {}

# Function to show analysis panel 
def show_analysis_panel():
    """
    Display the analysis panel with improved UI
    """
    # Create a layout with the dropdown and button side by side
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Analysis type selection with simple dropdown
        display_analysis_type_select(
            st.session_state.analysis_type,
            on_change_callback=on_analysis_type_change
        )
    
    with col2:
        # Simple analysis button beside the dropdown
        analyze_button = st.button(
            "🚀 Analyze Paper", 
            use_container_width=True, 
            type="primary",
            help="Analyze this paper using Gemini AI"
        )
        
        # If button is clicked, set processing flag
        if analyze_button:
            st.session_state.processing = True
            st.rerun()
    
    # Run analysis if processing flag is set
    if st.session_state.processing:
        # Create containers for progress indicators
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_message = st.empty()
        
        # Show initial status
        status = show_loading_status("Preparing paper content...", progress_bar, 0.1)
        
        # Actual analysis
        force_pro = st.session_state.model_choice == "Pro"
        try:
            # Update progress for preparation stage
            time.sleep(0.5)
            progress_bar.progress(0.3)
            status.info("Processing with Gemini AI...")
            
            # Perform the actual analysis
            st.session_state.analysis_results = analyze_paper_with_gemini(
                st.session_state.paper_images,
                st.session_state.paper_metadata,
                st.session_state.analysis_type,
                force_pro,
                api_key=st.session_state.user_api_key,
                simplified=st.session_state.simplified_view
            )
            
            # Update progress
            progress_bar.progress(0.8)
            status.info("Organizing results...")
            time.sleep(0.5)
                
            # Update progress indicators
            if "error" in st.session_state.analysis_results:
                progress_bar.empty()
                status.error(f"Error analyzing paper: {st.session_state.analysis_results['error']}")
            else:
                progress_bar.progress(1.0)
                status.success("Analysis complete!")
                
                # Store this analysis for later use
                st.session_state.past_analyses[st.session_state.analysis_type] = st.session_state.analysis_results
                
                # Show success and clean up
                time.sleep(1)
                status.empty()
                progress_bar.empty()
                    
        except Exception as e:
            progress_bar.empty()
            status.error(f"Error analyzing paper: {str(e)}")
        
        st.session_state.processing = False
        st.rerun() 

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

    options = list(models.keys())
    current_index = options.index(st.session_state.model_choice) if st.session_state.model_choice in options else 0

    selected_index = st.selectbox(
        "Select Model",
        range(len(options)),
        format_func=lambda i: models.get(options[i], options[i]),
        index=current_index,
        help="Choose which Gemini model to use for analysis"
    )
    
    if selected_index < len(options):
        st.session_state.model_choice = options[selected_index]
    
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

# Main content area - initial state (welcome screen)
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
                        
                        # Extract key definitions when the paper is uploaded
                        st.session_state.key_definitions = extract_key_definitions(
                            st.session_state.paper_images,
                            st.session_state.user_api_key
                        )
                        
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
                        
                        # Extract key definitions when the paper is fetched
                        st.session_state.key_definitions = extract_key_definitions(
                            st.session_state.paper_images,
                            st.session_state.user_api_key
                        )
                        
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
                        
                        # Extract key definitions when the paper is downloaded
                        st.session_state.key_definitions = extract_key_definitions(
                            st.session_state.paper_images,
                            st.session_state.user_api_key
                        )
                        
                        st.success(f"Successfully loaded paper")
                        
                        # Reset field tags and past analyses when loading a new paper
                        st.session_state.field_tags = {}
                        st.session_state.past_analyses = {}
                        st.session_state.analysis_results = None
                        
                        # Rerun to update the UI
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error downloading PDF: {str(e)}")

# Paper loaded state - showing analysis interface
else:  
    # Paper overview
    display_paper_overview(st.session_state.paper_metadata, st.session_state.field_tags)
    
    # Display key definitions if available
    if st.session_state.key_definitions:
        display_key_definitions(st.session_state.key_definitions)
    
    # Get field tags earlier if missing
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
    
    # Add a "Load Different Paper" button at the top right
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("📄 Load Different Paper", type="secondary", use_container_width=True):
            # Reset session state and redirect to welcome screen
            st.session_state.paper_images = None
            st.session_state.paper_metadata = None
            st.session_state.analysis_results = None
            st.session_state.past_analyses = {}
            st.session_state.field_tags = {}
            st.session_state.key_definitions = {}
            st.rerun()
    
    # Layout based on preview setting
    if st.session_state.show_preview:
        # Create two columns: one for preview, one for analysis
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Paper preview section
            st.markdown("### 📄 Paper Preview")
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
                    use_column_width=True
                )
        
        with col2:
            # Analysis section - removing the header with magnifying glass
            st.markdown("### Choose Analysis Type")
            
            # Show analysis panel
            show_analysis_panel()
    else:
        # If preview is disabled, just show analysis panel
        st.markdown("### Choose Analysis Type")
        show_analysis_panel()
    
    # Display analysis results if available - only show once
    if st.session_state.analysis_results is not None:
        # Display download button for analysis
        if "raw_analysis" in st.session_state.analysis_results:
            col1, col2, col3 = st.columns([2, 2, 1])
            with col3:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                paper_title = st.session_state.paper_metadata.get('title', 'paper').replace(" ", "_")[:30]
                filename = f"{paper_title}_{timestamp}_analysis.md"
                
                analysis_text = st.session_state.analysis_results.get("raw_analysis", "")
                
                st.download_button(
                    label="📥 Download Analysis",
                    data=analysis_text,
                    file_name=filename,
                    mime="text/markdown",
                    use_container_width=True
                )
        
        # Display the analysis results in a clean format
        display_analysis_results(
            st.session_state.analysis_results, 
            expand_all=False,
            simplified=st.session_state.simplified_view,
            show_definitions=False  # Don't show definitions again as we already showed them at the top
        )
        
        # If we have past analyses, show them at the bottom
        if len(st.session_state.past_analyses) > 1:  # More than just the current analysis
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            
            # Display past analyses selector
            past_results = {k: v for k, v in st.session_state.past_analyses.items() 
                           if k != st.session_state.analysis_type}
            
            if past_results:
                st.markdown("### Other Available Analyses")
                
                # Create a grid of buttons for past analyses
                cols = st.columns(min(3, len(past_results)))
                
                for i, (analysis_type, results) in enumerate(past_results.items()):
                    with cols[i % len(cols)]:
                        info = get_analysis_type_description(analysis_type)
                        if st.button(f"{info.get('icon', '')} {info.get('title', analysis_type)}",
                                   key=f"view_{analysis_type}"):
                            on_past_analysis_select(analysis_type)

# Function to get field tags if missing
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