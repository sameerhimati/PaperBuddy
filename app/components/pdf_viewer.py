# app/components/pdf_viewer.py
import streamlit as st
import base64
from pathlib import Path
import re
import json

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

def apply_annotations(text, annotations):
    """Apply user annotations to text"""
    # Sort annotations by position (we'd need to track position in a real implementation)
    # For now, just highlight the exact text
    highlighted_text = text
    
    for annotation in annotations:
        if annotation['type'] == 'highlight':
            # Replace the exact text with highlighted version
            annotation_text = annotation['text']
            highlight_color = annotation['color']
            
            # Use regex to find the exact text, being careful with special characters
            pattern = re.escape(annotation_text)
            replacement = f"<span style='background-color: {highlight_color};' class='user-highlight' data-id='{annotation['id']}'>{annotation_text}</span>"
            
            highlighted_text = re.sub(pattern, replacement, highlighted_text)
            
    return highlighted_text

def display_interactive_text(sections, terminology, section_scores, section_confidence=None, annotations=None, session_manager=None, paper_id=None):
    """Display text with interactive features"""
    if annotations is None:
        annotations = []
        
    # Get list of sections sorted by importance
    sorted_sections = sorted(
        section_scores.keys(),
        key=lambda s: section_scores[s]['score'],
        reverse=True
    )
    
    # Determine current section from session state or default to first section
    current_section = st.session_state.get('current_section')
    if current_section not in sorted_sections and sorted_sections:
        current_section = sorted_sections[0]
    
    # Navigation sidebar
    st.sidebar.subheader("Navigation")
    selected_section = st.sidebar.selectbox(
        "Jump to section:", 
        sorted_sections,
        index=sorted_sections.index(current_section) if current_section in sorted_sections else 0,
        format_func=lambda s: f"{s} ({section_scores[s]['score']:.2f})"
    )
    
    # Update current section in session state
    if session_manager:
        session_manager.set_current_section(selected_section)
    else:
        st.session_state['current_section'] = selected_section
    
    # Display selected section with highlighted terminology
    if section_confidence and selected_section in section_confidence:
        conf_score = section_confidence[selected_section]
        st.subheader(f"{selected_section} (Confidence: {conf_score:.2f})")
        
        # Add confidence indicator
        if conf_score >= 0.8:
            st.success("High confidence extraction")
        elif conf_score >= 0.6:
            st.info("Medium confidence extraction")
        else:
            st.warning("Low confidence extraction - may need review")
    else:
        st.subheader(selected_section)
    
    # Calculate color for importance
    score = section_scores[selected_section]['score']
    importance_color = f"rgba(0, {int(255 * score)}, {int(255 * (1-score))}, 0.2)"
    
    # Get section text
    section_text = sections[selected_section]
    
    # Filter annotations for this section
    section_annotations = [a for a in annotations if a['section'] == selected_section]
    
    # Apply terminology highlighting
    highlighted_text = highlight_terminology(section_text, terminology)
    
    # Apply user annotations
    highlighted_text = apply_annotations(highlighted_text, section_annotations)
    
    # Add text selection capability with JavaScript
    st.markdown("""
    <script>
    document.addEventListener('mouseup', function() {
        const selection = window.getSelection();
        if (selection.toString().length > 0) {
            // Show a custom menu
            const rect = selection.getRangeAt(0).getBoundingClientRect();
            const menu = document.createElement('div');
            menu.className = 'selection-menu';
            menu.style.position = 'absolute';
            menu.style.left = `${rect.left}px`;
            menu.style.top = `${rect.bottom + window.scrollY}px`;
            menu.style.backgroundColor = 'white';
            menu.style.border = '1px solid black';
            menu.style.zIndex = 1000;
            menu.innerHTML = `
                <button onclick="addHighlight('yellow')" style="background-color:yellow">Highlight</button>
                <button onclick="addNote()">Add Note</button>
            `;
            document.body.appendChild(menu);
            
            // Remove menu when clicking elsewhere
            document.addEventListener('mousedown', function hideMenu(e) {
                if (!menu.contains(e.target)) {
                    document.body.removeChild(menu);
                    document.removeEventListener('mousedown', hideMenu);
                }
            });
        }
    });
    
    function addHighlight(color) {
        const selection = window.getSelection();
        const selectedText = selection.toString();
        
        // Send to Streamlit
        window.parent.postMessage({
            type: 'highlight',
            text: selectedText,
            color: color
        }, '*');
    }
    
    function addNote() {
        const selection = window.getSelection();
        const selectedText = selection.toString();
        
        // Prompt for note
        const note = prompt('Add a note:', '');
        if (note !== null) {
            // Send to Streamlit
            window.parent.postMessage({
                type: 'note',
                text: selectedText,
                note: note
            }, '*');
        }
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Display section with background color based on importance
    st.markdown(
        f"""
        <div style="background-color: {importance_color}; padding: 10px; border-radius: 5px;" class="paper-section" data-section="{selected_section}">
        {highlighted_text}
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Add annotation capabilities
    st.subheader("Add Annotation")
    annotation_text = st.text_area("Select text above or paste text here:")
    annotation_type = st.selectbox("Annotation type:", ["highlight", "note"])
    
    if annotation_type == "highlight":
        annotation_color = st.color_picker("Highlight color:", "#FFFF00")
        annotation_content = ""
    else:
        annotation_color = "#FFFFFF"
        annotation_content = st.text_area("Note content:")
    
    if st.button("Add Annotation") and annotation_text and session_manager:
        session_manager.save_annotation(
            paper_id, 
            selected_section, 
            annotation_text, 
            annotation_type, 
            content=annotation_content, 
            color=annotation_color
        )
        st.success("Annotation added!")
        st.experimental_rerun()
    
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
        term_confidence = terminology.get('term_confidence', {}).get(term, None)
        
        # Show confidence if available
        term_display = term
        if term_confidence is not None:
            term_display = f"{term} (Conf: {term_confidence:.2f})"
            
        with st.sidebar.expander(term_display):
            st.write(definition)