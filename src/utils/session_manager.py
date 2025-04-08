# src/utils/session_manager.py
import streamlit as st
import json
import os
import uuid
from pathlib import Path
import tempfile
import pickle
from datetime import datetime

class SessionManager:
    """
    Manages session state, paper data, and user annotations for PaperBuddy.
    Handles persistence between page navigations and app restarts.
    """
    
    def __init__(self, cache_dir=None):
        """
        Initialize the session manager.
        
        Args:
            cache_dir (str, optional): Directory to store cached data
        """
        # Initialize session ID if not present
        if 'session_id' not in st.session_state:
            st.session_state['session_id'] = str(uuid.uuid4())
            
        # Set up cache directory
        if cache_dir is None:
            self.cache_dir = Path(tempfile.gettempdir()) / f"paperbuddy_{st.session_state['session_id']}"
        else:
            self.cache_dir = Path(cache_dir)
            
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize core session state variables if not present
        self._initialize_session_state()
        
    def _initialize_session_state(self):
        """Initialize all necessary session state variables with defaults."""
        defaults = {
            # Current paper state
            'current_paper_id': None,
            'paper_results': None,
            'processing_options': {},
            
            # User settings
            'llm_model': "google/gemma-3-4b-it",
            'use_llm': True,
            
            # Paper history (list of paper IDs viewed, most recent first)
            'paper_history': [],
            
            # User annotations (dict mapping paper_id -> annotation data)
            'annotations': {},
            
            # Current view state
            'current_page': "Upload & Process",
            'current_section': None,
            'current_tab': "Interactive Paper View",
        }
        
        # Only set values that don't already exist
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
                
    def save_paper_results(self, paper_id, results):
        """
        Save paper processing results to both session state and disk cache.
        
        Args:
            paper_id (str): Identifier for the paper
            results (dict): Processing results to save
            
        Returns:
            bool: True if saved successfully
        """
        # Update session state
        st.session_state['current_paper_id'] = paper_id
        st.session_state['paper_results'] = results
        
        # Add to paper history (removing if already exists to move to front)
        if paper_id in st.session_state['paper_history']:
            st.session_state['paper_history'].remove(paper_id)
        st.session_state['paper_history'].insert(0, paper_id)
        
        # Save to disk cache for persistence
        cache_file = self.cache_dir / f"{paper_id}.pickle"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(results, f)
            return True
        except Exception as e:
            print(f"Error saving paper results to cache: {e}")
            return False
    
    def load_paper_results(self, paper_id):
        """
        Load paper results from cache if available, otherwise from session state.
        
        Args:
            paper_id (str): Identifier for the paper
            
        Returns:
            dict: Paper results or None if not found
        """
        # Check if it's the current paper in session state
        if st.session_state['current_paper_id'] == paper_id and st.session_state['paper_results'] is not None:
            return st.session_state['paper_results']
        
        # Try loading from disk cache
        cache_file = self.cache_dir / f"{paper_id}.pickle"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    results = pickle.load(f)
                    
                # Update session state with loaded results
                st.session_state['current_paper_id'] = paper_id
                st.session_state['paper_results'] = results
                
                return results
            except Exception as e:
                print(f"Error loading paper results from cache: {e}")
                
        return None
    
    def get_paper_history(self, max_papers=10):
        """
        Get the user's paper viewing history.
        
        Args:
            max_papers (int): Maximum number of papers to return
            
        Returns:
            list: List of paper IDs, most recent first
        """
        return st.session_state['paper_history'][:max_papers]
    
    def save_annotation(self, paper_id, section, text, annotation_type, content="", color="#FFFF00"):
        """
        Save a user annotation or highlight.
        
        Args:
            paper_id (str): Identifier for the paper
            section (str): Section title where annotation occurs
            text (str): The text being annotated
            annotation_type (str): Type of annotation ('highlight', 'note', etc.)
            content (str, optional): Additional content for the annotation
            color (str, optional): Color for highlights
            
        Returns:
            str: ID of the created annotation
        """
        # Initialize annotations dict for this paper if not exists
        if paper_id not in st.session_state['annotations']:
            st.session_state['annotations'][paper_id] = []
            
        # Create annotation with unique ID and timestamp
        annotation_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        annotation = {
            'id': annotation_id,
            'paper_id': paper_id,
            'section': section,
            'text': text,
            'type': annotation_type,
            'content': content,
            'color': color,
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        # Add to session state
        st.session_state['annotations'][paper_id].append(annotation)
        
        # Save annotations to disk
        self._save_annotations_to_disk()
        
        return annotation_id
    
    def get_annotations(self, paper_id=None, section=None):
        """
        Get annotations, optionally filtered by paper ID and section.
        
        Args:
            paper_id (str, optional): Filter by paper ID
            section (str, optional): Filter by section title
            
        Returns:
            list: List of annotation dictionaries
        """
        # Load annotations from disk first to ensure we have the latest
        self._load_annotations_from_disk()
        
        # If no paper_id specified, return all annotations
        if paper_id is None:
            return st.session_state['annotations']
            
        # If paper has no annotations, return empty list
        if paper_id not in st.session_state['annotations']:
            return []
            
        annotations = st.session_state['annotations'][paper_id]
        
        # Filter by section if specified
        if section is not None:
            annotations = [a for a in annotations if a['section'] == section]
            
        return annotations
    
    def update_annotation(self, annotation_id, updates):
        """
        Update an existing annotation.
        
        Args:
            annotation_id (str): ID of the annotation to update
            updates (dict): Dictionary of fields to update
            
        Returns:
            bool: True if updated successfully
        """
        # Update timestamp
        updates['updated_at'] = datetime.now().isoformat()
        
        # Search for the annotation in all papers
        for paper_id, annotations in st.session_state['annotations'].items():
            for i, annotation in enumerate(annotations):
                if annotation['id'] == annotation_id:
                    # Update the annotation
                    for key, value in updates.items():
                        st.session_state['annotations'][paper_id][i][key] = value
                    
                    # Save to disk
                    self._save_annotations_to_disk()
                    return True
                    
        return False
    
    def delete_annotation(self, annotation_id):
        """
        Delete an annotation.
        
        Args:
            annotation_id (str): ID of the annotation to delete
            
        Returns:
            bool: True if deleted successfully
        """
        # Search for the annotation in all papers
        for paper_id, annotations in st.session_state['annotations'].items():
            for i, annotation in enumerate(annotations):
                if annotation['id'] == annotation_id:
                    # Remove the annotation
                    st.session_state['annotations'][paper_id].pop(i)
                    
                    # Save to disk
                    self._save_annotations_to_disk()
                    return True
                    
        return False
    
    def _save_annotations_to_disk(self):
        """Save all annotations to disk for persistence."""
        annotations_file = self.cache_dir / "annotations.json"
        try:
            with open(annotations_file, 'w') as f:
                json.dump(st.session_state['annotations'], f)
            return True
        except Exception as e:
            print(f"Error saving annotations to disk: {e}")
            return False
    
    def _load_annotations_from_disk(self):
        """Load annotations from disk if available."""
        annotations_file = self.cache_dir / "annotations.json"
        if annotations_file.exists():
            try:
                with open(annotations_file, 'r') as f:
                    st.session_state['annotations'] = json.load(f)
                return True
            except Exception as e:
                print(f"Error loading annotations from disk: {e}")
                
        return False
    
    def set_current_page(self, page):
        """Set the current page and store in session state."""
        st.session_state['current_page'] = page
    
    def get_current_page(self):
        """Get the current page from session state."""
        return st.session_state.get('current_page', "Upload & Process")
    
    def set_current_section(self, section):
        """Set the current section being viewed."""
        st.session_state['current_section'] = section
    
    def get_current_section(self):
        """Get the current section being viewed."""
        return st.session_state.get('current_section')
    
    def set_current_tab(self, tab):
        """Set the current tab being viewed."""
        st.session_state['current_tab'] = tab
    
    def get_current_tab(self):
        """Get the current tab being viewed."""
        return st.session_state.get('current_tab', "Interactive Paper View")