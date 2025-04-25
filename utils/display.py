import streamlit as st
import re
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import time

def display_tags(tags: Dict[str, Dict[str, str]], container=None):
    """
    Display field tags with clean styling
    
    Args:
        tags: Dictionary of tag data
        container: Optional container to render in (defaults to current)
    """
    target = container if container else st
    
    if not tags:
        return
        
    # Create HTML for tags
    tag_html = "<div style='margin: 0.5rem 0;'>"
    for tag, info in tags.items():
        tag_html += f"""
        <span style='display: inline-block; 
                     background-color: rgba(28, 131, 225, 0.1); 
                     padding: 0.2rem 0.6rem; 
                     border-radius: 1rem; 
                     margin-right: 0.5rem; 
                     margin-bottom: 0.5rem; 
                     font-size: 0.8rem;'>
            {tag}
        </span>"""
    tag_html += "</div>"
    
    target.markdown(tag_html, unsafe_allow_html=True)


def format_timestamp(timestamp=None):
    """
    Format a timestamp or current time
    
    Args:
        timestamp: Optional timestamp to format
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now()
    elif isinstance(timestamp, str):
        try:
            timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return timestamp  # Return as is if parsing fails
    
    return timestamp.strftime("%b %d, %Y at %H:%M")


def rating_badge(rating: int, tooltip: Optional[str] = None):
    """
    Create a visual rating badge
    
    Args:
        rating: Numerical rating (1-10)
        tooltip: Optional tooltip text
        
    Returns:
        HTML for the rating badge
    """
    # Validate rating
    if not isinstance(rating, int) or rating < 1 or rating > 10:
        return ""
    
    # Determine color based on rating
    if rating <= 3:
        color = "#ff6347"  # Tomato (low)
        bg_color = "rgba(255, 99, 71, 0.2)"
    elif rating <= 6:
        color = "#ffa500"  # Orange (medium)
        bg_color = "rgba(255, 165, 0, 0.2)"
    else:
        color = "#228b22"  # Forest Green (high)
        bg_color = "rgba(34, 139, 34, 0.2)"
    
    # Create badge HTML
    tooltip_attr = f'title="{tooltip}"' if tooltip else ''
    badge = f"""
    <span class="rating" style="display: inline-block; 
                              padding: 0.2rem 0.5rem; 
                              border-radius: 0.25rem; 
                              font-weight: bold;
                              margin-right: 0.5rem;
                              background-color: {bg_color};
                              color: {color};" {tooltip_attr}>
        {rating}/10
    </span>
    """
    
    return badge


def extract_ratings_from_text(text: str) -> List[Tuple[int, str]]:
    """
    Extract rating scores and context from text
    
    Args:
        text: Text to search for ratings
        
    Returns:
        List of (rating, context) tuples
    """
    # Look for patterns like "Rating: 7/10" or "Rating 7/10" or "(7/10)"
    patterns = [
        r'Rating:?\s*(\d+)[/]10(.*?)(?=\n|$)',
        r'\((\d+)[/]10\)(.*?)(?=\n|$)',
        r'(\d+)[/]10(.*?)(?=\n|$)'
    ]
    
    ratings = []
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            try:
                if len(match) >= 2:
                    rating = int(match[0])
                    context = match[1].strip()
                    
                    # Validate rating range
                    if 1 <= rating <= 10:
                        ratings.append((rating, context))
            except (ValueError, IndexError):
                continue
    
    return ratings


def display_paper_card(title: str, authors: str, date: Optional[str] = None, preview_image=None):
    """
    Display a paper card for the library view
    
    Args:
        title: Paper title
        authors: Paper authors
        date: Optional date/timestamp
        preview_image: Optional preview image
    """
    with st.container():
        st.markdown(
            f"""
            <div style="border: 1px solid rgba(49, 51, 63, 0.2); 
                        border-radius: 0.5rem; 
                        padding: 1rem; 
                        margin-bottom: 1rem;">
                <h3 style="margin-top: 0; margin-bottom: 0.5rem;">{title}</h3>
                <p style="margin-bottom: 0.5rem; opacity: 0.8;">{authors}</p>
                {f'<p style="font-size: 0.8rem; opacity: 0.6;">{format_timestamp(date)}</p>' if date else ''}
            </div>
            """,
            unsafe_allow_html=True
        )


def display_terminology(terminology):
    """Display terminology definitions in cards"""
    if not terminology:
        st.info("No terminology definitions available yet. They will appear here after analysis.")
        return
    
    st.markdown("## 🔑 Key Terminology")
    
    # Create grid layout 
    num_terms = len(terminology)
    num_cols = min(3, max(1, num_terms))
    cols = st.columns(num_cols)
    
    for i, (term, info) in enumerate(terminology.items()):
        with cols[i % num_cols]:
            # Create a card-style expander for each term
            with st.expander(term):
                if isinstance(info, dict):
                    st.markdown(f"**Definition:** {info.get('definition', 'No definition available')}")
                    
                    if 'explanation' in info:
                        st.markdown(f"**Simplified:** {info.get('explanation')}")
                else:
                    # Handle the case where info might not be a dictionary
                    st.markdown(f"**Definition:** {info}")
    
    st.markdown("---")


class ProgressManager:
    """Manage progress display with detailed steps"""
    
    def __init__(self, total_steps=5, key_prefix=""):
        self.container = st.empty()
        self.progress_bar = None
        self.status_text = None
        self.total_steps = total_steps
        self.current_step = 0
        self.key_prefix = key_prefix
        self._create_elements()
    
    def _create_elements(self):
        """Create progress elements"""
        with self.container.container():
            self.progress_bar = st.progress(0)
            self.status_text = st.empty()
    
    def update(self, message, step=None):
        """Update progress with message"""
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
        
        progress_value = min(self.current_step / self.total_steps, 1.0)
        self.progress_bar.progress(progress_value)
        self.status_text.info(message)
    
    def complete(self, success=True, message="Completed successfully!"):
        """Mark process as complete"""
        self.progress_bar.progress(1.0)
        if success:
            self.status_text.success(message)
        else:
            self.status_text.error(message)
        
        # Auto-clear after delay
        time.sleep(2)
        self.clear()
    
    def clear(self):
        """Clear the progress elements"""
        self.container.empty()