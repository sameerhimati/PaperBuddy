import streamlit as st
from typing import Dict, Any, List, Tuple

def display_paper_metadata(metadata: Dict[str, Any]):
    """
    Display paper metadata in a structured format.
    
    Args:
        metadata: Paper metadata dictionary
    """
    # Main metadata in 3 columns
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        authors = metadata.get('author', 'Unknown')
        st.markdown(f"**Authors:** {authors}")
    
    with col2:
        st.markdown(f"**Pages:** {metadata.get('page_count', 'Unknown')}")
        if 'published' in metadata:
            st.markdown(f"**Published:** {metadata.get('published')}")
    
    with col3:
        if 'arxiv_id' in metadata:
            st.markdown(f"**arXiv ID:** [{metadata.get('arxiv_id')}](https://arxiv.org/abs/{metadata.get('arxiv_id')})")
        elif 'url' in metadata:
            st.markdown(f"**Source:** [Link]({metadata.get('url')})")
    
    # Abstract in expander - but only if available
    if 'abstract' in metadata and metadata['abstract'] and len(metadata['abstract'].strip()) > 0:
        with st.expander("Abstract", expanded=False):
            st.markdown(metadata['abstract'])

def display_key_definitions(definitions: Dict[str, Dict[str, str]]):
    """
    Display key definitions with hover explanations
    
    Args:
        definitions: Dictionary of definitions where each key is a term and value is dict with 'definition' and 'explanation'
    """
    if not definitions:
        return
    
    st.markdown("### 📚 Key Terminology")
    
    # Create grid layout based on number of definitions
    num_terms = len(definitions)
    num_cols = min(3, num_terms)  # Max 3 columns
    
    if num_cols > 0:
        cols = st.columns(num_cols)
        
        for i, (term, info) in enumerate(definitions.items()):
            with cols[i % num_cols]:
                # Create an expander for each term
                with st.expander(term):
                    st.markdown(f"**Definition:** {info.get('definition', 'No definition available')}")
                    if 'explanation' in info:
                        st.markdown(f"**Simplified:** {info.get('explanation')}")

def display_analysis_type_tabs(
    analysis_types: Dict[str, Dict[str, str]],
    current_type: str,
    on_change_callback=None
):
    """
    Display analysis type tabs with better highlighting
    
    Args:
        analysis_types: Dictionary of analysis types and their descriptions
        current_type: Currently selected analysis type
        on_change_callback: Function to call when tab is changed
    """
    # Use custom CSS for active tab highlight
    st.markdown("""
    <style>
    .analysis-card {
        position: relative;
        text-align: left;
        border-radius: 8px;
        padding: 15px;
        margin: 0 5px 10px 5px;
        cursor: pointer;
        transition: all 0.3s;
        border: 1px solid rgba(49, 51, 63, 0.2);
        height: 100%;
        min-height: 180px;
    }
    .analysis-card:hover {
        background-color: rgba(49, 51, 63, 0.1);
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .analysis-card.active {
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(28, 131, 225, 0.8);
    }
    .card-icon {
        font-size: 1.5rem;
        margin-bottom: 8px;
    }
    .card-title {
        font-weight: 600;
        margin-bottom: 8px;
        font-size: 1rem;
    }
    .card-desc {
        font-size: 0.8rem;
        margin-bottom: 8px;
        color: rgba(49, 51, 63, 0.8);
    }
    .card-for {
        font-size: 0.75rem;
        font-style: italic;
        position: absolute;
        bottom: 15px;
        color: rgba(49, 51, 63, 0.6);
    }
                
    div[data-testid="stButton"] {
                    visibility: hidden;
                    position: absolute;
                    width: 1px;
                    height: 1px;
                    padding: 0;
                    margin: -1px;
                    overflow: hidden;
                    clip: rect(0, 0, 0, 0);
                    white-space: nowrap;
                    border-width: 0;
                }
            
                div[data-testid="stButton"]:focus {
                    visibility: visible;
                    position: unset;
                    width: unset;
                    height: unset;
                    padding: unset;
                    margin: unset;
                    overflow: unset;
                    clip: unset;
                    white-space: unset;
                    border-width: unset;
                }
    </style>
    """, unsafe_allow_html=True)
    
    # Use container to ensure equal height for all cards
    with st.container():
        cols = st.columns(len(analysis_types))
        
        # Display cards
        for i, (key, info) in enumerate(analysis_types.items()):
            with cols[i]:
                # Apply active class for selected tab
                is_active = key == current_type
                active_class = "active" if is_active else ""
                
                # Create a button with card styling
                html_card = f"""
                <div class="analysis-card {active_class}" 
                     onclick="document.getElementById('btn_{key}').click()">
                    <div class="card-icon">{info["icon"]}</div>
                    <div class="card-title">{info["title"]}</div>
                    <div class="card-desc">{info["description"]}</div>
                    <div class="card-for">For: {info["for"]}</div>
                </div>
                """
                st.markdown(html_card, unsafe_allow_html=True)
                
                # Hidden button for functionality (completely invisible)
                if st.button("", key=f"btn_{key}", 
                            help=f"{info['description']}\n\nBest for: {info['for']}"):
                    # Call callback if provided
                    if on_change_callback:
                        on_change_callback(key)

def display_analysis_results(
    results: Dict[str, Any], 
    expand_all: bool = False,
    simplified: bool = False,
    display_mode: str = "tabs",
    show_definitions: bool = True
):
    """
    Display analysis results from AI in a structured format.
    
    Args:
        results: Analysis results dictionary
        expand_all: Whether to expand all sections by default
        simplified: Whether to display in simplified mode
        display_mode: How to display sections ("tabs" or "expanders")
        show_definitions: Whether to show key definitions section
    """
    if 'error' in results:
        st.error(f"Error in analysis: {results['error']}")
        return
    
    # Display key definitions if available and requested
    if show_definitions and 'key_definitions' in results and results['key_definitions']:
        display_key_definitions(results['key_definitions'])
    
    # Display analysis based on type
    if simplified or results.get('analysis_type') == 'simplified':
        # Display simplified view (ELI5 mode)
        if 'simplified' in results:
            st.markdown(results['simplified'])
        elif 'eli5' in results:
            st.markdown(results['eli5'])
        else:
            st.info("No simplified explanation available. Please run the analysis with 'Explain Like I'm 5' option.")
    
    elif results.get('analysis_type') == 'quick_summary':
        # Display quick summary as is
        if 'raw_analysis' in results:
            st.markdown(results['raw_analysis'])
    
    elif results.get('analysis_type') in ['technical', 'practical']:
        # Display technical or practical analysis as is
        if 'raw_analysis' in results:
            st.markdown(results['raw_analysis'])
    
    else:
        # Standard view with well-structured sections
        # Ordered sections for consistent display
        section_order = ["summary", "key_innovations", "techniques", "practical_value", "limitations"]
        
        # Check if we have structured sections
        has_structured_sections = any(section in results for section in section_order)
        
        if has_structured_sections:
            if display_mode == "tabs":
                # Get available sections
                available_sections = [s for s in section_order if s in results]
                if not available_sections:
                    st.markdown(results.get('raw_analysis', 'No analysis available'))
                    return
                
                # Create tabs with section icons
                section_icons = {
                    "summary": "📝",
                    "key_innovations": "💡",
                    "techniques": "⚙️",
                    "practical_value": "🔧", 
                    "limitations": "⚠️"
                }
                
                tab_labels = [f"{section_icons.get(section, '📄')} {section.replace('_', ' ').title()}" 
                              for section in available_sections]
                
                # Use native Streamlit tabs
                tabs = st.tabs(tab_labels)
                
                # Fill each tab with content
                for i, section in enumerate(available_sections):
                    with tabs[i]:
                        st.markdown(results[section])
            
            else:
                # Use expanders for sections
                for section in section_order:
                    if section in results:
                        section_icons = {
                            "summary": "📝",
                            "key_innovations": "💡",
                            "techniques": "⚙️",
                            "practical_value": "🔧",
                            "limitations": "⚠️"
                        }
                        icon = section_icons.get(section, "📄")
                        title = section.replace('_', ' ').title()
                        with st.expander(f"{icon} {title}", expanded=expand_all):
                            st.markdown(results[section])
        else:
            # If structured data isn't available, display raw analysis
            if 'raw_analysis' in results:
                st.markdown(results['raw_analysis'])
    
    # Display processing metadata in a concise format
    with st.expander("Analysis Details", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            model_used = results.get('model_used', 'Unknown model')
            processing_time = results.get('processing_time', 0)
            st.markdown(f"**Model:** {model_used}")
            st.markdown(f"**Processing Time:** {processing_time:.2f} seconds")
            
        with col2:
            if 'pages_analyzed' in results:
                st.markdown(f"**Pages Analyzed:** {results.get('pages_analyzed', 0)} of {results.get('total_pages', 0)}")
            else:
                st.markdown(f"**Processing Method:** {'PDF Direct' if results.get('pdf_processed', False) else 'Image-Based'}")
                
            if 'paper_complexity' in results:
                # Create visual indicator for complexity
                complexity = results.get('paper_complexity', 0)
                complexity_color = get_complexity_color(complexity)
                
                st.markdown(f"**Estimated Complexity:** {complexity:.2f}")
                st.progress(min(complexity, 1.0))  # Use native progress bar

def display_past_analyses(
    past_results: Dict[str, Dict[str, Any]], 
    current_type: str = None,
    on_select_callback=None
):
    """
    Display a list of past analyses for the user to select from
    
    Args:
        past_results: Dictionary of past analysis results keyed by analysis_type
        current_type: Currently selected analysis type
        on_select_callback: Function to call when an analysis is selected
    """
    if not past_results:
        return
    
    # Don't display if only current type exists
    other_analyses = [k for k in past_results.keys() if k != current_type]
    if not other_analyses:
        return
    
    st.markdown("### Previous Analyses")
    
    # Analysis type display names
    analysis_types = {
        "comprehensive": "Comprehensive Analysis",
        "quick_summary": "Quick Summary",
        "technical": "Technical Deep Dive",
        "practical": "Practical Applications", 
        "simplified": "Explain Like I'm 5 (ELI5)"
    }
    
    # Create a cleaner UI for past analyses
    for type_key in other_analyses:
        type_name = analysis_types.get(type_key, type_key)
        
        # Create a cleaner container for each past analysis
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"**{type_name}**")
            
            # Show a brief preview
            if 'summary' in past_results[type_key]:
                preview = past_results[type_key]['summary'][:100] + "..." if len(past_results[type_key]['summary']) > 100 else past_results[type_key]['summary']
                st.caption(preview)
            elif 'raw_analysis' in past_results[type_key]:
                preview = past_results[type_key]['raw_analysis'][:100] + "..." if len(past_results[type_key]['raw_analysis']) > 100 else past_results[type_key]['raw_analysis']
                st.caption(preview)
        
        with col2:
            if st.button("View", key=f"view_{type_key}"):
                # Call callback if provided
                if on_select_callback:
                    on_select_callback(type_key)
        
        st.markdown("<hr style='margin: 10px 0; opacity: 0.2;'>", unsafe_allow_html=True)

def get_complexity_color(complexity: float) -> str:
    """Generate color based on complexity score"""
    if complexity < 0.3:
        return "#4CAF50"  # Green
    elif complexity < 0.7:
        return "#FFC107"  # Yellow
    else:
        return "#F44336"  # Red