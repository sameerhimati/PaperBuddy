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
    Display key definitions with improved styling and layout
    """
    if not definitions:
        return
    
    st.markdown("## 🔑 Key Terminology")
    st.markdown("---")
    
    # Create grid layout based on number of definitions
    num_terms = len(definitions)
    num_cols = min(3, num_terms)  # Max 3 columns
    
    if num_cols > 0:
        cols = st.columns(num_cols)
        
        for i, (term, info) in enumerate(definitions.items()):
            with cols[i % num_cols]:
                # Create an expander for each term with better styling
                with st.expander(term):
                    st.markdown(f"**Definition:** {info.get('definition', 'No definition available')}")
                    
                    if 'explanation' in info:
                        st.markdown(f"**Simplified:** {info.get('explanation')}")

def get_analysis_type_description(analysis_type: str) -> Dict[str, str]:
    """
    Get the description for a specific analysis type
    
    Args:
        analysis_type: The analysis type key
        
    Returns:
        Dictionary with analysis type details
    """
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
    
    return analysis_types.get(analysis_type, {})

def display_analysis_type_select(
    current_type: str,
    on_change_callback=None
):
    """
    Display a simple dropdown for analysis type selection
    
    Args:
        current_type: Currently selected analysis type
        on_change_callback: Function to call when selection changes
    """
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
    
    # Format options for display
    options = list(analysis_types.keys())
    
    # Create formatted labels for dropdown
    format_func = lambda x: f"{analysis_types[x]['icon']} {analysis_types[x]['title']}"
    
    # Display the dropdown and handle selection
    selected = st.selectbox(
        "Select Analysis Type",
        options,
        format_func=format_func,
        index=options.index(current_type) if current_type in options else 0,
    )
    
    # Show description of selected type
    if selected in analysis_types:
        st.info(f"{analysis_types[selected]['description']} (For: {analysis_types[selected]['for']})")
    
    # Handle change if needed
    if selected != current_type and on_change_callback:
        on_change_callback(selected)
    
    return selected

def display_analysis_results(
    results: Dict[str, Any], 
    expand_all: bool = False,
    simplified: bool = False,
    display_mode: str = "sections",
    show_definitions: bool = True
):
    """
    Display analysis results with improved section formatting
    """
    if 'error' in results:
        st.error(f"Error in analysis: {results['error']}")
        return
    
    # Display model and timing info as a caption if available, but only once
    if not show_definitions:  # Only show if we're not already showing definitions
        model_used = results.get('model_used', 'Unknown model')
        processing_time = results.get('processing_time', 0)
        st.caption(f"Analysis by {model_used} | {processing_time:.1f} seconds")
    
    # Display key definitions if available and requested
    if show_definitions and 'key_definitions' in results and results['key_definitions']:
        display_key_definitions(results['key_definitions'])
    
    # Display analysis based on type
    if simplified or results.get('analysis_type') == 'simplified':
        # Display simplified view (ELI5 mode)
        st.markdown("## Paper Analysis")
        st.markdown("---")
        if 'simplified' in results:
            st.markdown(results['simplified'])
        elif 'eli5' in results:
            st.markdown(results['eli5'])
        else:
            st.info("No simplified explanation available. Please run the analysis with 'Explain Like I'm 5' option.")
        return
    
    elif results.get('analysis_type') == 'quick_summary':
        # Display quick summary as is
        st.markdown("## Paper Summary")
        st.markdown("---")
        if 'raw_analysis' in results:
            st.markdown(results['raw_analysis'])
        return
    
    elif results.get('analysis_type') in ['technical', 'practical']:
        # Display technical or practical analysis as is
        st.markdown("## Technical Analysis" if results.get('analysis_type') == 'technical' else "## Practical Applications")
        st.markdown("---")
        if 'raw_analysis' in results:
            st.markdown(results['raw_analysis'])
        return
    
    # Standard view with well-structured sections
    # Ordered sections for consistent display
    section_order = ["summary", "key_innovations", "techniques", "practical_value", "limitations"]
    
    # Add better section titles and icons
    section_titles = {
        "summary": "1. Overview",
        "key_innovations": "2. Key Innovations",
        "techniques": "3. Technical Methods",
        "practical_value": "4. Practical Applications",
        "limitations": "5. Limitations"
    }
    
    section_icons = {
        "summary": "📝",
        "key_innovations": "💡",
        "techniques": "⚙️",
        "practical_value": "🔧", 
        "limitations": "⚠️"
    }
    
    # Check if we have structured sections
    has_structured_sections = any(section in results for section in section_order)
    
    if has_structured_sections:
        st.markdown("## Detailed Analysis")
        st.markdown("---")
        
        # Use expanders for sections
        for section in section_order:
            if section in results:
                icon = section_icons.get(section, "📄")
                title = section_titles.get(section, section.replace('_', ' ').title())
                
                # More prominent section header with better styling
                with st.expander(f"{icon} {title}", expanded=(section == "summary")):
                    # Add content
                    st.markdown(results[section])
    else:
        # If structured data isn't available, display raw analysis
        st.markdown("## Paper Analysis")
        st.markdown("---")
        if 'raw_analysis' in results:
            st.markdown(results['raw_analysis'])

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
        type_info = get_analysis_type_description(type_key)
        
        # Create a cleaner container for each past analysis
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"**{type_info.get('icon', '')} {type_name}**")
        
        with col2:
            if st.button("View", key=f"view_{type_key}"):
                # Call callback if provided
                if on_select_callback:
                    on_select_callback(type_key)
        
        st.markdown("<hr style='margin: 10px 0; opacity: 0.2;'>", unsafe_allow_html=True)

def display_paper_overview(metadata: Dict[str, Any], field_tags: Dict[str, Any] = None):
    """
    Display paper overview including title, authors, and field tags
    """
    # Paper title
    paper_title = metadata.get('title', 'Unknown Title')
    st.markdown(f"## {paper_title}")
    
    # Paper metadata in a clean format
    authors = metadata.get('author', 'Unknown Author')
    pages = metadata.get('page_count', 'Unknown')
    
    st.markdown(f"**Authors:** {authors} | **Pages:** {pages}")
    
    # Display field tags if available
    if field_tags:
        # Create field tags with clean styling
        tag_html = "<div style='margin: 1rem 0;'>"
        for tag, info in field_tags.items():
            tag_html += f"<span style='display: inline-block; background-color: rgba(28, 131, 225, 0.1); padding: 0.2rem 0.6rem; border-radius: 1rem; margin-right: 0.5rem; margin-bottom: 0.5rem; font-size: 0.8rem;'>{tag}</span>"
        tag_html += "</div>"
        
        st.markdown(tag_html, unsafe_allow_html=True)
        
        # Show field tag descriptions in an expander
        with st.expander("Field Descriptions", expanded=False):
            for tag, info in field_tags.items():
                if 'description' in info:
                    st.markdown(f"**{tag}**: {info['description']}")
                    if 'link' in info and info['link']:
                        st.markdown(f"[Learn more]({info['link']})")
    
    st.markdown("---")

def get_complexity_color(complexity: float) -> str:
    """Generate color based on complexity score"""
    if complexity < 0.3:
        return "#4CAF50"  # Green
    elif complexity < 0.7:
        return "#FFC107"  # Yellow
    else:
        return "#F44336"  # Red