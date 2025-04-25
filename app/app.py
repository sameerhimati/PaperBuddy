import streamlit as st
import os
import sys
import tempfile
from datetime import datetime
import concurrent.futures
from PIL import Image
import io
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utility modules
from utils.paper_import import (
    load_pdf_from_path, 
    load_pdf_from_arxiv, 
    load_pdf_from_url,
    get_embedded_pdf_viewer,
    cleanup_temporary_files,
    PaperContent
)
from utils.ai_analysis import (
    analyze_paper,
    analyze_terminology,
    get_field_tags,
    process_paper_with_parallel_analysis
)
from utils.display import (
    display_terminology,
    ProgressManager,
    extract_ratings_from_text,
    rating_badge
)
from config import (
    CUSTOM_CSS,
    UI_SETTINGS,
    get_api_key,
    get_model_config,
    get_analysis_types,
    get_models
)

# Set page configuration
st.set_page_config(
    page_title="PaperBuddy - AI Paper Analysis",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    defaults = {
        "paper_content": None,
        "analysis_results": {},
        "current_analysis_type": UI_SETTINGS["default_analysis_type"],
        "user_api_key": None,
        "model_choice": UI_SETTINGS["default_model"],
        "processing": False,
        "last_action": None,
        "paper_processed": False,
        "field_tags": {},
        "terminology_loaded": False,
        "last_upload_id": None,
        "tab_index": 0,
        "analyses_running": False
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
            
    # Ensure nested structure in analysis_results exists
    if "terminology" not in st.session_state.analysis_results:
        st.session_state.analysis_results["terminology"] = {}


def display_paper_metadata(paper_content):
    """Display paper metadata in a clean format"""
    if not paper_content or not paper_content.is_valid:
        return
        
    metadata = paper_content.metadata
    
    # Paper title
    st.markdown(f"## {metadata.get('title', 'Unknown Title')}")
    
    # Main metadata in 3 columns
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        authors = metadata.get('author', 'Unknown Author')
        st.markdown(f"**Authors:** {authors}")
    
    with col2:
        st.markdown(f"**Pages:** {paper_content.page_count}")
        if 'published' in metadata:
            st.markdown(f"**Published:** {metadata.get('published')}")
    
    with col3:
        if 'arxiv_id' in metadata:
            st.markdown(f"**arXiv ID:** [{metadata.get('arxiv_id')}](https://arxiv.org/abs/{metadata.get('arxiv_id')})")
        elif 'url' in metadata:
            st.markdown(f"**Source:** [Link]({metadata.get('url')})")
    
    # Abstract in expander
    if 'abstract' in metadata and metadata['abstract'] and len(metadata['abstract'].strip()) > 0:
        with st.expander("Abstract", expanded=False):
            st.markdown(metadata['abstract'])
    
    # Display field tags if available
    if st.session_state.field_tags:
        st.markdown("### Research Fields")
        
        # Create field tags with clean styling
        cols = st.columns(3)
        for i, (tag, info) in enumerate(st.session_state.field_tags.items()):
            with cols[i % 3]:
                with st.expander(tag):
                    st.markdown(f"{info.get('description', '')}")
                    if 'link' in info and info['link']:
                        st.markdown(f"[Learn more]({info['link']})")
    
    st.markdown("---")


def display_analysis_selector(analysis_types, current_type):
    """Display analysis type selector"""
    # Format options for display
    options = list(analysis_types.keys())
    
    # Create formatted labels for dropdown
    format_func = lambda x: f"{analysis_types[x]['icon']} {analysis_types[x]['title']}"
    
    # Display the dropdown
    selected = st.selectbox(
        "Select Analysis Type",
        options,
        format_func=format_func,
        index=options.index(current_type) if current_type in options else 0,
        key="analysis_selector"
    )
    
    # Show description of selected type
    if selected in analysis_types:
        st.info(f"{analysis_types[selected]['description']} (For: {analysis_types[selected]['for']})")
    
    return selected


def display_model_selector(models, current_model):
    """Display model selector"""
    options = list(models.keys())
    
    # Create formatted labels for dropdown
    format_func = lambda x: f"{models[x]['name']} - {models[x]['description']}"
    
    # Display the dropdown
    selected = st.selectbox(
        "Select Model",
        options,
        format_func=format_func,
        index=options.index(current_model) if current_model in options else 0,
        key="model_selector"
    )
    
    # Warning for Pro model without API key
    if selected == "pro" and not st.session_state.user_api_key:
        st.warning("⚠️ Pro model requires your API key. Please add it in the sidebar.")
    
    return selected


def display_analysis_results_tabbed(result):
    """Display analysis results in a tabbed interface"""
    if not result or result.error:
        if result and result.error:
            st.error(f"Error in analysis: {result.error}")
        return
    
    # Extract all possible sections from raw analysis if not available directly
    if not result.sections and result.raw_analysis:
        from utils.ai_analysis import extract_all_sections
        result.sections = extract_all_sections(result.raw_analysis)
    
    # Get ratings from sections
    ratings = {}
    for section_name, section_text in result.sections.items():
        section_ratings = extract_ratings_from_text(section_text)
        if section_ratings:
            for rating, context in section_ratings:
                ratings[section_name] = (rating, context)
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Summary", 
        "💡 Innovations", 
        "⚙️ Techniques",
        "🔧 Applications",
        "⚠️ Limitations"
    ])
    
    # Summary tab
    with tab1:
        summary = result.get_section("summary")
        if summary:
            st.markdown(summary)
        else:
            st.markdown(result.raw_analysis[:500] + "...")
    
    # Innovations tab
    with tab2:
        innovations = result.get_section("key_innovations")
        if innovations:
            # Add rating badge if available
            if "key_innovations" in ratings:
                rating, context = ratings["key_innovations"]
                st.markdown(f'<p>Innovation Score: {rating_badge(rating)} {context}</p>', unsafe_allow_html=True)
            st.markdown(innovations)
        else:
            st.info("No specific innovations section found in the analysis.")
    
    # Techniques tab
    with tab3:
        techniques = result.get_section("techniques")
        if techniques:
            # Add rating badge if available
            if "techniques" in ratings:
                rating, context = ratings["techniques"]
                st.markdown(f'<p>Technical Score: {rating_badge(rating)} {context}</p>', unsafe_allow_html=True)
            st.markdown(techniques)
        else:
            st.info("No specific techniques section found in the analysis.")
    
    # Applications tab
    with tab4:
        applications = result.get_section("practical_value")
        if applications:
            # Add rating badge if available
            if "practical_value" in ratings:
                rating, context = ratings["practical_value"]
                st.markdown(f'<p>Practical Value: {rating_badge(rating)} {context}</p>', unsafe_allow_html=True)
            st.markdown(applications)
        else:
            st.info("No specific applications section found in the analysis.")
    
    # Limitations tab
    with tab5:
        limitations = result.get_section("limitations")
        if limitations:
            st.markdown(limitations)
        else:
            st.info("No specific limitations section found in the analysis.")
    
    # Display model and timing info as a caption
    st.caption(f"Analysis by {result.model_used} | {result.processing_time:.1f} seconds")


def display_simplified_analysis(result):
    """Display simplified explanation focused on readability"""
    if not result or result.error:
        if result and result.error:
            st.error(f"Error in analysis: {result.error}")
        return
    
    st.markdown("## Simplified Explanation")
    st.markdown("---")
    st.markdown(result.raw_analysis)
    
    # Display model and timing info as a caption
    st.caption(f"Analysis by {result.model_used} | {result.processing_time:.1f} seconds")


def display_raw_analysis(result):
    """Display raw analysis text"""
    if not result or result.error:
        if result and result.error:
            st.error(f"Error in analysis: {result.error}")
        return
    
    st.markdown("## Raw Analysis")
    st.markdown("---")
    st.markdown(result.raw_analysis)
    
    # Display model and timing info as a caption
    st.caption(f"Analysis by {result.model_used} | {result.processing_time:.1f} seconds")
    
    # Add download button for raw analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="📥 Download as Markdown",
        data=result.raw_analysis,
        file_name=f"paperbuddy_analysis_{timestamp}.md",
        mime="text/markdown"
    )


def process_paper_upload(uploaded_file):
    """Process uploaded PDF file"""
    progress = ProgressManager(total_steps=5, key_prefix="upload")
    progress.update("Uploading PDF...", step=1)
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        
        progress.update("Loading and processing PDF...", step=2)
        
        paper_content = load_pdf_from_path(tmp_path)
        if not paper_content.is_valid:
            progress.complete(False, f"Error loading PDF: {paper_content.error}")
            return None
        
        progress.update("Enriching metadata with AI...", step=3)
        
        # Use LLM to extract metadata if not available
        api_key = st.session_state.user_api_key if 'user_api_key' in st.session_state else None
        
        # Only run initial analysis if title/author/abstract are not well-defined
        title = paper_content.metadata.get('title', '')
        author = paper_content.metadata.get('author', '')
        
        if title == "Unknown Title" or author == "Unknown Author" or 'abstract' not in paper_content.metadata:
            # Use first 2 pages for metadata extraction
            initial_results = process_paper_with_parallel_analysis(
                paper_content.page_images[:min(2, len(paper_content.page_images))],
                paper_content.metadata,
                api_key,
                paper_content.pdf_bytes,
                analysis_types=["quick_summary"]  # Only run quick summary to extract basic info
            )
            
            if "quick_summary" in initial_results and initial_results["quick_summary"].is_successful:
                # Extract title and authors if they were not available
                summary = initial_results["quick_summary"].raw_analysis
                
                # First line is often the title in summaries
                if title == "Unknown Title" and summary:
                    lines = summary.split('\n')
                    if lines and len(lines[0]) > 5 and len(lines[0]) < 200:
                        paper_content.metadata["title"] = lines[0].strip()
                
                # Look for author mentions
                if author == "Unknown Author" and "author" in summary.lower():
                    author_match = re.search(r'(?:by|author[s]?:?)\s+([^\.]+)', summary, re.IGNORECASE)
                    if author_match:
                        paper_content.metadata["author"] = author_match.group(1).strip()
                
                # Look for abstract-like content
                if 'abstract' not in paper_content.metadata:
                    # Use the first paragraph as a pseudo-abstract
                    paragraphs = re.split(r'\n\s*\n', summary)
                    if len(paragraphs) > 1 and len(paragraphs[1]) > 30:
                        paper_content.metadata["abstract"] = paragraphs[1].strip()
        
        progress.update("Extracting research fields...", step=4)
        
        # Extract field tags
        title = paper_content.metadata.get('title', '')
        abstract = paper_content.metadata.get('abstract', '')
        
        if len(title) > 5 and len(abstract) > 20:
            st.session_state.field_tags = get_field_tags(
                title, 
                abstract,
                api_key
            )
        
        progress.update("Extracting terminology...", step=5)
        
        # Extract terminology
        try:
            terminology = analyze_terminology(
                paper_content.page_images[:min(3, len(paper_content.page_images))],
                paper_content.metadata,
                api_key
            )
            
            if terminology:
                st.session_state.analysis_results["terminology"] = terminology
                st.session_state.terminology_loaded = True
        except Exception as e:
            print(f"Error extracting terminology: {str(e)}")
        
        progress.complete(True, "Paper loaded successfully!")
        
        # Schedule automatic parallel analysis
        st.session_state.analyses_running = True
        
        return paper_content
        
    except Exception as e:
        progress.complete(False, f"Error processing PDF: {str(e)}")
        return None
    finally:
        # Clean up the temporary file
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception as e:
            print(f"Failed to clean up temporary file: {str(e)}")


def process_arxiv_import(arxiv_id):
    """Process arXiv import"""
    # Check if we're in a rerun after processing this arxiv ID
    if st.session_state.last_action == f"arxiv_{arxiv_id}" and st.session_state.paper_processed:
        return st.session_state.paper_content
        
    progress = ProgressManager(total_steps=3, key_prefix="arxiv")
    progress.update("Validating arXiv ID...", step=1)
    
    try:
        # Mark that we're processing this action
        st.session_state.last_action = f"arxiv_{arxiv_id}"
        st.session_state.paper_processed = False
        
        # Validate arXiv ID format
        arxiv_id = arxiv_id.strip()
        if not (arxiv_id.isdigit() or 
                (arxiv_id.replace('.', '').isdigit()) or
                ('.' in arxiv_id and arxiv_id.split('.')[0].isdigit() and arxiv_id.split('.')[1].isdigit())):
            progress.complete(False, "Invalid arXiv ID format")
            return None
        
        progress.update("Fetching paper from arXiv...", step=2)
        
        paper_content = load_pdf_from_arxiv(arxiv_id)
        if not paper_content.is_valid:
            progress.complete(False, f"Error loading paper from arXiv: {paper_content.error}")
            return None
        
        progress.update("Processing paper metadata...", step=3)
        
        # Extract field tags
        title = paper_content.metadata.get('title', '')
        abstract = paper_content.metadata.get('abstract', '')
        api_key = st.session_state.user_api_key if 'user_api_key' in st.session_state else None
        
        if len(title) > 5 and len(abstract) > 20:
            st.session_state.field_tags = get_field_tags(
                title, 
                abstract,
                api_key
            )
        
        # Extract terminology
        try:
            terminology = analyze_terminology(
                paper_content.page_images[:min(3, len(paper_content.page_images))],
                paper_content.metadata,
                api_key
            )
            
            if terminology:
                st.session_state.analysis_results["terminology"] = terminology
                st.session_state.terminology_loaded = True
        except Exception as e:
            print(f"Error extracting terminology: {str(e)}")
        
        progress.complete(True, "Paper loaded successfully!")
        
        # Mark that we've successfully processed this paper
        st.session_state.paper_processed = True
        
        # Schedule automatic parallel analysis
        st.session_state.analyses_running = True
        
        return paper_content
        
    except Exception as e:
        progress.complete(False, f"Error processing arXiv paper: {str(e)}")
        return None


def process_url_import(url):
    """Process URL import"""
    # Check if we're in a rerun after processing this URL
    if st.session_state.last_action == f"url_{url}" and st.session_state.paper_processed:
        return st.session_state.paper_content
        
    progress = ProgressManager(total_steps=4, key_prefix="url")
    progress.update("Validating URL...", step=1)
    
    try:
        # Mark that we're processing this action
        st.session_state.last_action = f"url_{url}"
        st.session_state.paper_processed = False
        
        # Very basic URL validation
        url = url.strip()
        if not (url.startswith('http://') or url.startswith('https://')) or '.pdf' not in url.lower():
            progress.complete(False, "Invalid URL format. Please provide a direct link to a PDF file.")
            return None
        
        progress.update("Downloading PDF from URL...", step=2)
        
        paper_content = load_pdf_from_url(url)
        if not paper_content.is_valid:
            progress.complete(False, f"Error downloading PDF: {paper_content.error}")
            return None
        
        progress.update("Enriching metadata with AI...", step=3)
        
        # Use LLM to extract metadata if not available
        api_key = st.session_state.user_api_key if 'user_api_key' in st.session_state else None
        
        # Only run initial analysis if title/author/abstract are not well-defined
        title = paper_content.metadata.get('title', '')
        author = paper_content.metadata.get('author', '')
        
        if title == "Unknown Title" or author == "Unknown Author" or 'abstract' not in paper_content.metadata:
            # Use first 2 pages for metadata extraction
            initial_results = process_paper_with_parallel_analysis(
                paper_content.page_images[:min(2, len(paper_content.page_images))],
                paper_content.metadata,
                api_key,
                paper_content.pdf_bytes,
                analysis_types=["quick_summary"]  # Only run quick summary to extract basic info
            )
            
            if "quick_summary" in initial_results and initial_results["quick_summary"].is_successful:
                # Extract title and authors if they were not available
                summary = initial_results["quick_summary"].raw_analysis
                
                # First line is often the title in summaries
                if title == "Unknown Title" and summary:
                    lines = summary.split('\n')
                    if lines and len(lines[0]) > 5 and len(lines[0]) < 200:
                        paper_content.metadata["title"] = lines[0].strip()
                
                # Look for author mentions
                if author == "Unknown Author" and "author" in summary.lower():
                    author_match = re.search(r'(?:by|author[s]?:?)\s+([^\.]+)', summary, re.IGNORECASE)
                    if author_match:
                        paper_content.metadata["author"] = author_match.group(1).strip()
                
                # Look for abstract-like content
                if 'abstract' not in paper_content.metadata:
                    # Use the first paragraph as a pseudo-abstract
                    paragraphs = re.split(r'\n\s*\n', summary)
                    if len(paragraphs) > 1 and len(paragraphs[1]) > 30:
                        paper_content.metadata["abstract"] = paragraphs[1].strip()
        
        progress.update("Extracting research fields and terminology...", step=4)
        
        # Extract field tags
        title = paper_content.metadata.get('title', '')
        abstract = paper_content.metadata.get('abstract', '')
        
        if len(title) > 5 and len(abstract) > 20:
            st.session_state.field_tags = get_field_tags(
                title, 
                abstract,
                api_key
            )
        
        # Extract terminology
        try:
            terminology = analyze_terminology(
                paper_content.page_images[:min(3, len(paper_content.page_images))],
                paper_content.metadata,
                api_key
            )
            
            if terminology:
                st.session_state.analysis_results["terminology"] = terminology
                st.session_state.terminology_loaded = True
        except Exception as e:
            print(f"Error extracting terminology: {str(e)}")
        
        progress.complete(True, "Paper loaded successfully!")
        
        # Mark that we've successfully processed this paper
        st.session_state.paper_processed = True
        
        # Schedule automatic parallel analysis
        st.session_state.analyses_running = True
        
        return paper_content
        
    except Exception as e:
        progress.complete(False, f"Error processing PDF from URL: {str(e)}")
        return None


def run_parallel_analysis():
    """Run parallel analysis on current paper in background"""
    if not st.session_state.paper_content or not st.session_state.paper_content.is_valid:
        return
    
    # Get API key
    api_key = st.session_state.user_api_key if 'user_api_key' in st.session_state else None
    
    # Create a progress manager
    progress = ProgressManager(total_steps=3, key_prefix="parallel_analysis")
    progress.update("Starting parallel paper analysis...", step=1)
    
    try:
        # Get available analysis types
        analysis_types = get_analysis_types()
        analysis_list = list(analysis_types.keys())
        
        # Run analyses in parallel
        progress.update("Running multiple analysis types...", step=2)
        
        results = process_paper_with_parallel_analysis(
            st.session_state.paper_content.page_images,
            st.session_state.paper_content.metadata,
            api_key,
            st.session_state.paper_content.pdf_bytes,
            analysis_types=analysis_list
        )
        
        # Store results in session state
        for analysis_type, result in results.items():
            if analysis_type in ["field_tags", "terminology"]:
                continue  # These were already processed separately
                
            st.session_state.analysis_results[analysis_type] = result
        
        progress.update("Completing analysis...", step=3)
        progress.complete(True, f"Completed {len(analysis_list)} analyses!")
        
        # Flag that analyses are complete
        st.session_state.analyses_running = False
        
        # Request app rerun to display results
        st.rerun()
        
    except Exception as e:
        progress.complete(False, f"Error during parallel analysis: {str(e)}")


def show_import_interface():
    """Show paper import interface"""
    st.markdown("## Import Paper")
    
    # Tab-based input method selection
    tab1, tab2, tab3 = st.tabs(["Upload PDF", "arXiv ID", "PDF URL"])
    
    with tab1:
        uploaded_file = st.file_uploader("Upload a PDF paper", type=["pdf"], 
                                         key=f"pdf_uploader_{st.session_state.get('file_uploader_key', 0)}")
        
        if uploaded_file is not None:
            # Generate a unique file identifier based on filename and size
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            
            # Only process if this is a new file or first time seeing it
            if file_id != st.session_state.last_upload_id:
                st.session_state.last_upload_id = file_id
                
                # Clear previous state
                st.session_state.paper_content = None
                st.session_state.analysis_results = {"terminology": {}}
                
                # Process the file
                paper_content = process_paper_upload(uploaded_file)
                
                if paper_content and paper_content.is_valid:
                    st.session_state.paper_content = paper_content
                    
                    # Add a message to confirm loading
                    st.success("Paper loaded successfully! Switching to Analysis tab...")
                    # Switch to analysis tab
                    st.session_state.tab_index = 1
                    # Force a rerun to apply the state changes
                    st.rerun()
    
    with tab2:
        arxiv_id = st.text_input("Enter arXiv ID (e.g., 2303.08774)", placeholder="2303.08774")
        fetch_button = st.button("Fetch Paper", key="fetch_arxiv", use_container_width=True)
        
        if arxiv_id and fetch_button:
            # Process the arXiv ID
            with st.spinner(f"Fetching paper with arXiv ID: {arxiv_id}..."):
                # Clear previous state
                st.session_state.paper_content = None
                st.session_state.analysis_results = {"terminology": {}}
                
                paper_content = process_arxiv_import(arxiv_id)
                
                if paper_content and paper_content.is_valid:
                    st.session_state.paper_content = paper_content
                    st.session_state.last_upload_id = f"arxiv_{arxiv_id}"
                    
                    # Add a message to confirm loading
                    st.success("Paper loaded successfully! Switching to Analysis tab...")
                    # Switch to analysis tab
                    st.session_state.tab_index = 1
                    # Force a rerun to apply the state changes
                    st.rerun()
    
    with tab3:
        pdf_url = st.text_input("Enter PDF URL", placeholder="https://example.com/paper.pdf")
        url_button = st.button("Fetch Paper", key="fetch_url", use_container_width=True)
        
        if pdf_url and url_button:
            # Process the URL
            with st.spinner(f"Fetching paper from URL: {pdf_url}..."):
                # Clear previous state
                st.session_state.paper_content = None
                st.session_state.analysis_results = {"terminology": {}}
                
                paper_content = process_url_import(pdf_url)
                
                if paper_content and paper_content.is_valid:
                    st.session_state.paper_content = paper_content
                    st.session_state.last_upload_id = f"url_{pdf_url}"
                    
                    # Add a message to confirm loading
                    st.success("Paper loaded successfully! Switching to Analysis tab...")
                    # Switch to analysis tab 
                    st.session_state.tab_index = 1
                    # Force a rerun to apply the state changes
                    st.rerun()


def show_analysis_interface():
    """Show paper analysis interface"""
    paper_content = st.session_state.paper_content
    
    if not paper_content or not paper_content.is_valid:
        st.info("Please import a paper first using the Import Paper tab.")
        return
    
    # Check if we need to run parallel analysis
    if st.session_state.analyses_running:
        # Show a placeholder while analyses are running
        with st.spinner("Running comprehensive analysis of the paper..."):
            # Run the analyses
            run_parallel_analysis()
    
    # Display paper metadata
    display_paper_metadata(paper_content)
    
    # Display terminology if available
    if "terminology" in st.session_state.analysis_results and st.session_state.analysis_results["terminology"]:
        display_terminology(st.session_state.analysis_results["terminology"])
    
    # Create a two-column layout for controls and PDF viewer
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.markdown("### Choose Analysis Type")
        
        # Get available analysis types
        analysis_types = get_analysis_types()
        
        # Display analysis type selector
        new_type = display_analysis_selector(analysis_types, st.session_state.current_analysis_type)
        if new_type != st.session_state.current_analysis_type:
            st.session_state.current_analysis_type = new_type
            st.rerun()
        
        # Display model selector in sidebar instead
        with st.sidebar:
            st.markdown("### Model Selection")
            
            models = get_models()
            new_model = display_model_selector(models, st.session_state.model_choice)
            if new_model != st.session_state.model_choice:
                st.session_state.model_choice = new_model
                st.rerun()
        
        # Analyze button - only needed if the analysis doesn't exist yet
        current_type = st.session_state.current_analysis_type
        if current_type not in st.session_state.analysis_results:
            analyze_button = st.button(
                "🚀 Analyze Paper", 
                use_container_width=True, 
                type="primary",
                key="analyze_button"
            )
            
            # Run analysis if button clicked
            if analyze_button:
                with st.spinner(f"Performing {current_type} analysis..."):
                    api_key = st.session_state.user_api_key
                    result = analyze_paper(
                        paper_content.page_images,
                        paper_content.metadata,
                        current_type,
                        api_key,
                        pdf_bytes=paper_content.pdf_bytes
                    )
                    st.session_state.analysis_results[current_type] = result
                    st.rerun()
    
    with col2:
        # Display PDF viewer
        st.markdown("### Paper Preview")
        
        # Get PDF viewer HTML
        pdf_viewer_html = get_embedded_pdf_viewer(paper_content, height=600)
        
        if pdf_viewer_html:
            st.markdown(pdf_viewer_html, unsafe_allow_html=True)
        else:
            # Fallback to showing first page image
            if paper_content.page_images:
                st.image(
                    paper_content.page_images[0],
                    caption="First page preview (PDF viewer not available)",
                    use_column_width=True
                )
    
    # Display analysis results if available
    st.markdown("### Analysis Results")
    
    # Check if we have results for the current analysis type
    current_type = st.session_state.current_analysis_type
    if current_type in st.session_state.analysis_results:
        result = st.session_state.analysis_results[current_type]
        
        # Display results based on analysis type
        if current_type == "simplified":
            display_simplified_analysis(result)
        else:
            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["Tabbed View", "Raw Analysis", "Download"])
            
            with tab1:
                display_analysis_results_tabbed(result)
            
            with tab2:
                display_raw_analysis(result)
                
            with tab3:
                st.markdown("### Download Options")
                
                # Download as Markdown
                st.download_button(
                    label="📥 Download as Markdown",
                    data=result.raw_analysis,
                    file_name=f"paperbuddy_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                
                # Download as JSON
                import json
                json_data = {
                    "title": paper_content.metadata.get("title", "Unknown"),
                    "authors": paper_content.metadata.get("author", "Unknown"),
                    "analysis_type": result.analysis_type,
                    "model_used": result.model_used,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "sections": result.sections,
                    "raw_analysis": result.raw_analysis
                }
                
                st.download_button(
                    label="📥 Download as JSON",
                    data=json.dumps(json_data, indent=2),
                    file_name=f"paperbuddy_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
    else:
        # Check if analyses are still running
        if st.session_state.analyses_running:
            st.info("Analyses are currently running in the background. Results will appear here shortly...")
        else:
            st.info(f"No analysis of type '{current_type}' available yet. Click 'Analyze Paper' to generate one.")


def show_library_interface():
    """Show paper library interface (placeholder for future)"""
    st.markdown("## Paper Library")
    st.info("The paper library feature is coming soon! It will allow you to save and manage your analyzed papers.")


def configure_sidebar():
    """Configure the sidebar with settings"""
    st.sidebar.title("⚙️ Settings")
    
    # API Key Configuration
    st.sidebar.markdown("### API Configuration")
    user_api_key = st.sidebar.text_input(
        "Your Gemini API Key (optional)",
        type="password",
        help="Provide your own API key for analysis",
        key="api_key_input"
    )
    
    if user_api_key:
        st.session_state.user_api_key = user_api_key
        st.sidebar.success("API key saved for this session")
    
    st.sidebar.markdown("""
    *Need an API key?* [Get one here](https://aistudio.google.com/app/apikey)
    """)
    
    # Add option to reset
    if st.sidebar.button("Reset Session", use_container_width=True):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def main():
    """Main application entry point"""
    # Initialize session state
    initialize_session_state()
    
    # App title
    st.title("📚 PaperBuddy")
    
    # Configure sidebar
    configure_sidebar()
    
    # Create tabs for app navigation with explicit tab index tracking
    tab_options = ["📄 Import Paper", "🔍 Analysis", "📚 Library"]
    
    # Create the tabs with the correct active tab
    tabs = st.tabs(tab_options)
    
    # Handle content for each tab
    with tabs[st.session_state.tab_index]:
        if st.session_state.tab_index == 0:
            show_import_interface()
        elif st.session_state.tab_index == 1:
            show_analysis_interface()
        elif st.session_state.tab_index == 2:
            show_library_interface()
    
    # Update tab index if user clicks a different tab
    for i, tab in enumerate(tabs):
        with tab:
            st.session_state.tab_index = i
            break

if __name__ == "__main__":
    main()