from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
import json
import os

class SectionScorer:
    """
    Class to score sections of academic papers by importance.
    Uses transformer models and/or user feedback to calculate importance.
    """
    
    def __init__(self, model_name="allenai/specter", feedback_file="user_feedback.json"):
        """
        Initialize the section scorer with a pretrained model and user feedback data.
        
        Args:
            model_name (str): Name of the pretrained model to use
                              Default is SPECTER which is trained on scientific papers
            feedback_file (str): Path to the file storing user feedback data
        """
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.feedback_file = feedback_file
        self.user_feedback = self._load_user_feedback()
    
    def _load_models(self):
        """Load the transformer models if not already loaded"""
        if self.tokenizer is None or self.model is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
    
    def _load_user_feedback(self):
        """
        Load user feedback data from file.
        
        Returns:
            dict: User feedback data for sections
        """
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading user feedback: {e}")
                return {}
        return {}
    
    def _save_user_feedback(self):
        """Save user feedback data to file."""
        try:
            with open(self.feedback_file, 'w') as f:
                json.dump(self.user_feedback, f)
        except Exception as e:
            print(f"Error saving user feedback: {e}")
    
    def add_user_feedback(self, paper_id, section_title, score):
        """
        Add user feedback for a section.
        
        Args:
            paper_id (str): Identifier for the paper
            section_title (str): Title of the section
            score (float): User importance score (0-1)
            
        Returns:
            bool: True if feedback was added successfully
        """
        if paper_id not in self.user_feedback:
            self.user_feedback[paper_id] = {}
        
        if "section_scores" not in self.user_feedback[paper_id]:
            self.user_feedback[paper_id]["section_scores"] = {}
        
        self.user_feedback[paper_id]["section_scores"][section_title] = score
        self._save_user_feedback()
        return True
    
    def _get_embedding(self, text):
        """
        Get embedding for a text using the transformer model.
        
        Args:
            text (str): Text to get embedding for
            
        Returns:
            numpy.ndarray: Text embedding
        """
        self._load_models()
        
        # Truncate text if it's too long for the model
        max_length = self.tokenizer.model_max_length
        tokens = self.tokenizer.encode(text, truncation=True, max_length=max_length)
        
        # If text is empty after processing, return zero vector
        if not tokens:
            return np.zeros(768)  # Standard embedding size
        
        # Create input tensors
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)
        
        # Get model output
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Use the [CLS] token embedding as the sentence embedding
        embedding = outputs.last_hidden_state[:, 0, :].numpy().flatten()
        
        return embedding
    
    def compute_similarity(self, text1, text2):
        """
        Compute semantic similarity between two texts.
        
        Args:
            text1 (str): First text
            text2 (str): Second text
            
        Returns:
            float: Similarity score between 0 and 1
        """
        # Get embeddings
        embedding1 = self._get_embedding(text1)
        embedding2 = self._get_embedding(text2)
        
        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
        
        return float(similarity)
    
    def score_sections_model(self, sections, abstract=None):
        """
        Score sections of a paper by their importance using the model.
        
        Args:
            sections (dict): Dictionary mapping section titles to section text
            abstract (str, optional): Paper abstract for reference
            
        Returns:
            dict: Dictionary mapping section titles to importance scores
        """
        # If no abstract is provided, try to find it in the sections
        if abstract is None:
            for title in sections:
                if "abstract" in title.lower():
                    abstract = sections[title]
                    break
        
        # If still no abstract, use the introduction or first section
        if abstract is None:
            for title in sections:
                if "introduction" in title.lower():
                    abstract = sections[title]
                    break
            
            # If no introduction either, use the first section
            if abstract is None and sections:
                abstract = next(iter(sections.values()))
        
        # Prepare results
        scores = {}
        
        # Method 1: Score based on similarity to abstract
        if abstract:
            for title, text in sections.items():
                # Skip very short sections
                if len(text.split()) < 10:
                    scores[title] = 0.0
                    continue
                
                # Compute similarity to abstract
                similarity = self.compute_similarity(abstract, text)
                scores[title] = similarity
        
        # Method 2: If no abstract, score based on keywords and section position
        else:
            # Important keywords often found in significant sections
            keywords = ["method", "result", "conclusion", "discussion", "finding", 
                       "contribution", "evaluation", "experiment"]
            
            for title, text in sections.items():
                # Skip very short sections
                if len(text.split()) < 10:
                    scores[title] = 0.0
                    continue
                
                # Base score on section position (earlier = more important, except conclusions)
                position_score = 1.0
                
                # Additional score based on keywords in title or text
                keyword_score = 0.0
                for keyword in keywords:
                    if keyword in title.lower():
                        keyword_score += 0.2
                    if keyword in text.lower():
                        keyword_score += 0.1
                
                # Combined score
                scores[title] = min(position_score + keyword_score, 1.0)
        
        # Normalize scores to range [0, 1]
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {title: score / max_score for title, score in scores.items()}
        
        return scores
    
    def score_sections_user_feedback(self, paper_id, sections):
        """
        Score sections based on user feedback.
        
        Args:
            paper_id (str): Identifier for the paper
            sections (dict): Dictionary mapping section titles to section text
            
        Returns:
            dict: Dictionary mapping section titles to importance scores
        """
        scores = {}
        
        # If we have feedback for this paper, use it
        if paper_id in self.user_feedback and "section_scores" in self.user_feedback[paper_id]:
            feedback_scores = self.user_feedback[paper_id]["section_scores"]
            
            # For sections with feedback, use the feedback score
            for title in sections:
                if title in feedback_scores:
                    scores[title] = feedback_scores[title]
                else:
                    scores[title] = 0.5  # Default score for sections without feedback
        else:
            # If no feedback for this paper, assign neutral scores
            for title in sections:
                scores[title] = 0.5
        
        return scores
    
    def score_sections(self, paper_id, sections, abstract=None, use_model=True, use_feedback=True):
        """
        Score sections using model, user feedback, or both.
        
        Args:
            paper_id (str): Identifier for the paper
            sections (dict): Dictionary mapping section titles to section text
            abstract (str, optional): Paper abstract for reference
            use_model (bool): Whether to use model-based scoring
            use_feedback (bool): Whether to use feedback-based scoring
            
        Returns:
            dict: Dictionary mapping section titles to importance scores and sources
        """
        model_scores = {}
        feedback_scores = {}
        
        # Get model scores if requested
        if use_model:
            model_scores = self.score_sections_model(sections, abstract)
        
        # Get feedback scores if requested
        if use_feedback:
            feedback_scores = self.score_sections_user_feedback(paper_id, sections)
        
        # Combine scores based on which methods are enabled
        combined_scores = {}
        for title in sections:
            score_sources = {}
            
            if use_model and title in model_scores:
                score_sources["model"] = model_scores[title]
            
            if use_feedback and title in feedback_scores:
                score_sources["feedback"] = feedback_scores[title]
            
            # Calculate combined score
            if score_sources:
                combined_scores[title] = {
                    "score": sum(score_sources.values()) / len(score_sources),
                    "sources": score_sources
                }
            else:
                combined_scores[title] = {
                    "score": 0.5,  # Default score
                    "sources": {"default": 0.5}
                }
        
        return combined_scores
    
    def get_important_sentences(self, text, top_n=5):
        """
        Get the most important sentences from a text.
        
        Args:
            text (str): Text to analyze
            top_n (int): Number of sentences to return
            
        Returns:
            list: List of important sentences
        """
        # Split text into sentences
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
        
        # If we have very few sentences, return them all
        if len(sentences) <= top_n:
            return sentences
        
        # Create a representation of the entire text
        full_text = ' '.join(sentences)
        full_text_embedding = self._get_embedding(full_text)
        
        # Score each sentence by similarity to the full text
        sentence_scores = []
        for sentence in sentences:
            # Skip very short sentences
            if len(sentence.split()) < 5:
                continue
                
            # Get embedding and compute similarity
            sentence_embedding = self._get_embedding(sentence)
            similarity = np.dot(full_text_embedding, sentence_embedding) / (
                np.linalg.norm(full_text_embedding) * np.linalg.norm(sentence_embedding))
            
            sentence_scores.append((sentence, similarity))
        
        # Sort by score and take top_n
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        important_sentences = [sentence for sentence, _ in sentence_scores[:top_n]]
        
        return important_sentences