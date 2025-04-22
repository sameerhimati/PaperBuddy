"""
Display utilities for the Streamlit application.
"""

import streamlit as st
import time
from typing import Dict, Any, List

def display_progress_bar(text: str = "Analyzing paper..."):
    """
    Display a progress bar with custom text.
    
    Args:
        text: Text to display above the progress bar
    
    Returns:
        Progress bar and text elements
    """
    progress_text = st.empty()
    progress_bar = st.progress(0)
    progress_text.text(text)
    
    return progress_text, progress_bar

def simulate_progress(progress_text, progress_bar, steps: int = 10):
    """
    Simulate progress for operations that don't provide real-time feedback.
    
    Args:
        progress_text: Text element from display_progress_bar
        progress_bar: Progress bar element from display_progress_bar
        steps: Number of steps for the simulation
    """
    for i in range(steps):
        # Update progress text based on step
        if i < steps // 3:
            progress_text.text("Processing paper and extracting content...")
        elif i < 2 * steps // 3:
            progress_text.text("Analyzing content with AI...")
        else:
            progress_text.text("Organizing results...")
            
        # Update progress bar
        progress_bar.progress((i + 1) / steps)
        time.sleep(0.2)  # Adjust time based on expected total time

def display_paper_metadata(metadata: Dict[str, Any]):
    """
    Display paper metadata in a structured format.
    
    Args:
        metadata: Paper metadata dictionary
    """
    st.subheader("Paper Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Title:** {metadata.get('title', 'Unknown')}")
        st.markdown(f"**Authors:** {metadata.get('author', 'Unknown')}")
        if 'published' in metadata:
            st.markdown(f"**Published:** {metadata.get('published')}")
    
    with col2:
        st.markdown(f"**Pages:** {metadata.get('page_count', 'Unknown')}")
        if 'arxiv_id' in metadata:
            st.markdown(f"**arXiv ID:** {metadata.get('arxiv_id')}")
        if 'url' in metadata:
            st.markdown(f"**Source:** [Link]({metadata.get('url')})")
    
    if 'abstract' in metadata and metadata['abstract']:
        with st.expander("Abstract", expanded=False):
            st.markdown(metadata['abstract'])

def display_analysis_results(results: Dict[str, Any], expand_all: bool = False):
    """
    Display analysis results from AI in a structured format.
    
    Args:
        results: Analysis results dictionary
        expand_all: Whether to expand all sections by default
    """
    if 'error' in results:
        st.error(f"Error in analysis: {results['error']}")
        return
    
    # Display model information
    model_used = results.get('model_used', 'Unknown model')
    st.caption(f"Analysis performed using: {model_used}")
    
    # Display summary if available
    if 'summary' in results:
        with st.expander("Summary", expanded=expand_all):
            st.markdown(results['summary'])
    
    # Display innovations if available
    if 'key_innovations' in results:
        with st.expander("Key Innovations", expanded=expand_all):
            st.markdown(results['key_innovations'])
    
    # Display techniques if available
    if 'techniques' in results:
        with st.expander("Techniques", expanded=expand_all):
            st.markdown(results['techniques'])
    
    # Display practical value if available
    if 'practical_value' in results:
        with st.expander("Practical Value", expanded=expand_all):
            st.markdown(results['practical_value'])
    
    # Display limitations if available
    if 'limitations' in results:
        with st.expander("Limitations", expanded=expand_all):
            st.markdown(results['limitations'])
    
    # If structured data isn't available, display raw analysis
    if 'raw_analysis' in results and not any(k in results for k in ['summary', 'key_innovations', 'techniques', 'practical_value']):
        with st.expander("Complete Analysis", expanded=True):
            st.markdown(results['raw_analysis'])
    
    # Display processing metadata
    with st.expander("Processing Details", expanded=False):
        st.markdown(f"**Processing Time:** {results.get('processing_time', 0):.2f} seconds")
        st.markdown(f"**Pages Analyzed:** {results.get('pages_analyzed', 0)} of {results.get('total_pages', 0)}")
        if 'paper_complexity' in results:
            st.markdown(f"**Estimated Paper Complexity:** {results.get('paper_complexity', 0):.2f}")
            st.markdown(f"**Pro Model Used:** {'Yes' if results.get('pro_model_triggered', False) else 'No'}")