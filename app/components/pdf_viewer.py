# app/components/pdf_viewer.py
import streamlit as st
import base64
from pathlib import Path
import re

def render_pdf(pdf_path):
    """Display a PDF in the Streamlit app"""
    # Read PDF file
    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    
    # Embed PDF in HTML
    pdf_display = f"""
        <iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" 
        style="border: none;"></iframe>
    """
    
    # Display PDF
    st.markdown(pdf_display, unsafe_allow_html=True)

def highlight_terminology(text, terminology):
    """Highlight terminology in text"""
    highlighted_text = text
    for term_info in terminology.get('terms', []):
        term = term_info['term']
        # Use regex to find whole words only
        pattern = r'\b' + re.escape(term) + r'\b'
        replacement = f"<span style='background-color: #FFFF00; font-weight: bold;'>{term}</span>"
        highlighted_text = re.sub(pattern, replacement, highlighted_text, flags=re.IGNORECASE)
    
    return highlighted_text

def display_interactive_text(sections, terminology, section_scores):
    """Display text with interactive features"""
    # Get list of sections sorted by importance
    sorted_sections = sorted(
        section_scores.keys(),
        key=lambda s: section_scores[s]['score'],
        reverse=True
    )
    
    # Navigation sidebar
    st.sidebar.subheader("Navigation")
    selected_section = st.sidebar.selectbox(
        "Jump to section:", 
        sorted_sections,
        format_func=lambda s: f"{s} ({section_scores[s]['score']:.2f})"
    )
    
    # Display selected section with highlighted terminology
    st.subheader(selected_section)
    
    # Calculate color for importance
    score = section_scores[selected_section]['score']
    color = f"rgba(0, {int(255 * score)}, {int(255 * (1-score))}, 0.2)"
    
    # Apply highlighting to section text
    section_text = sections[selected_section]
    highlighted_text = highlight_terminology(section_text, terminology)
    
    # Display section with background color based on importance
    st.markdown(
        f"""
        <div style="background-color: {color}; padding: 10px; border-radius: 5px;">
        {highlighted_text}
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Term definitions as expandable sections
    st.sidebar.subheader("Terminology in this section")
    
    # Filter terms found in this section
    section_terms = []
    for term_info in terminology.get('terms', []):
        term = term_info['term']
        if term.lower() in section_text.lower():
            section_terms.append(term)
    
    # Display expandable definitions
    for term in section_terms:
        definition = terminology.get('definitions', {}).get(term, "No definition available")
        with st.sidebar.expander(term):
            st.write(definition)