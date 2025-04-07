from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import spacy
import numpy as np
from collections import Counter

class TerminologyExtractor:
    """
    Class to extract important terminology from academic papers.
    Uses NLP models to identify domain-specific terms and provide definitions.
    """
    
    def __init__(self, model_name="distilbert-base-uncased"):
        """
        Initialize the terminology extractor with a pretrained model.
        
        Args:
            model_name (str): Name of the pretrained model to use
        """
        self.model_name = model_name
        # Load SpaCy for linguistic processing
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            import subprocess
            subprocess.call("python -m spacy download en_core_web_sm", shell=True)
            self.nlp = spacy.load("en_core_web_sm")
            
        # We'll initialize the transformer model when needed to save memory
        self.tokenizer = None
        self.model = None
        self.ner_pipeline = None
    
    def _load_models(self):
        """Load the transformer models if not already loaded"""
        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        
        if self.model is None:
            self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
            
        if self.ner_pipeline is None:
            # Create a named entity recognition pipeline
            self.ner_pipeline = pipeline("ner", model=self.model, tokenizer=self.tokenizer)
    
    def extract_candidate_terms(self, text):
        """
        Extract candidate terms from text using linguistic patterns.
        Focuses on noun phrases that are likely to be technical terms.
        
        Args:
            text (str): Text to extract terms from
            
        Returns:
            list: List of candidate terms
        """
        doc = self.nlp(text)
        
        # Extract noun phrases and technical terms
        candidate_terms = []
        
        # Get noun chunks (noun phrases)
        for chunk in doc.noun_chunks:
            # Filter for terms that might be technical (e.g., more than one word, or capitalized)
            if len(chunk.text.split()) > 1 or chunk.text[0].isupper():
                candidate_terms.append(chunk.text.strip())
        
        # Add named entities that might be technical terms
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PRODUCT", "GPE", "LOC", "PERSON"]:
                candidate_terms.append(ent.text.strip())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = [term for term in candidate_terms if term.lower() not in seen and not seen.add(term.lower())]
        
        return unique_terms
    
    def rank_terms_by_importance(self, text, candidate_terms, top_n=20):
        """
        Rank candidate terms by importance using frequency and context.
        
        Args:
            text (str): Original text
            candidate_terms (list): List of candidate terms to rank
            top_n (int): Number of top terms to return
            
        Returns:
            list: List of top terms with importance scores
        """
        # Simple frequency-based ranking
        doc = self.nlp(text)
        
        # Count occurrences of each term
        term_counts = Counter()
        for term in candidate_terms:
            # Count how many times this term appears in the text
            # We use a simple case-insensitive match here
            term_counts[term] = text.lower().count(term.lower())
        
        # Get the most common terms
        top_terms = term_counts.most_common(top_n)
        
        # Convert to list of dictionaries with term and score
        ranked_terms = [{"term": term, "score": count} for term, count in top_terms]
        
        return ranked_terms
    
    def find_term_definitions(self, text, terms):
        """
        Find potential definitions for terms in the text.
        Looks for patterns like "Term is a..." or "Term refers to..."
        
        Args:
            text (str): Text to search for definitions
            terms (list): List of terms to find definitions for
            
        Returns:
            dict: Dictionary mapping terms to their definitions
        """
        definitions = {}
        
        doc = self.nlp(text)
        sentences = list(doc.sents)
        
        for term_info in terms:
            term = term_info["term"]
            definition = ""
            
            # Look for sentences that might contain definitions
            for sentence in sentences:
                sentence_text = sentence.text.strip()
                
                # Check if the term is in this sentence
                if term.lower() in sentence_text.lower():
                    # Check for definition patterns
                    patterns = [
                        f"{term} is ", 
                        f"{term} are ",
                        f"{term} refers to ",
                        f"{term} is defined as ",
                        f"{term} means ",
                        f"{term}, which is ",
                        f"{term} which is ",
                    ]
                    
                    for pattern in patterns:
                        if pattern.lower() in sentence_text.lower():
                            definition = sentence_text
                            break
                
                if definition:
                    break
            
            if definition:
                definitions[term] = definition
            else:
                # If no definition found, get a sentence that uses the term
                for sentence in sentences:
                    sentence_text = sentence.text.strip()
                    if term.lower() in sentence_text.lower() and len(sentence_text.split()) > 5:
                        definitions[term] = f"Context: {sentence_text}"
                        break
        
        return definitions
    
    def extract_terminology(self, text, top_n=20):
        """
        Extract important terminology from text with definitions.
        
        Args:
            text (str): Text to extract terminology from
            top_n (int): Number of top terms to extract
            
        Returns:
            dict: Dictionary with ranked terms and their definitions
        """
        # Extract candidate terms
        candidate_terms = self.extract_candidate_terms(text)
        
        # Rank terms by importance
        ranked_terms = self.rank_terms_by_importance(text, candidate_terms, top_n)
        
        # Find definitions for top terms
        definitions = self.find_term_definitions(text, ranked_terms)
        
        # Create result with terms and their definitions
        terminology = {
            "terms": ranked_terms,
            "definitions": definitions
        }
        
        return terminology