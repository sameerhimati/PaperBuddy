import os
import json
import tempfile
from typing import Dict, List, Any, Optional
import torch
import os
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

class LLMExtractor:
    """
    Class to use open-source LLMs for enhancing paper extraction and analysis.
    Includes confidence scoring to indicate reliability of extracted information.
    """
    
    def __init__(self, model_name: str = "google/gemma-3-4b-it"):
        """
        Initialize LLM extractor with specified model.
        
        Args:
            model_name (str): HuggingFace model name (default: google/gemma-3-4b-it)
        """

        load_dotenv()
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")

        
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.max_length = 2048  # Maximum context length for most models
        
    def _load_model(self):
        if self.tokenizer is None or self.model is None:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name, 
                    token=self.hf_token
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    token=self.hf_token,
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True,
                    device_map="auto"
                )
            except Exception as e:
                print(f"Error loading model: {e}")
                # Fallback to a smaller model if the requested one fails
                fallback_model = "google/gemma"
                print(f"Falling back to {fallback_model}")
                self.tokenizer = AutoTokenizer.from_pretrained(fallback_model)
                self.model = AutoModelForCausalLM.from_pretrained(
                    fallback_model,
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True,
                    device_map="auto"
                )
    
    def process_text(self, prompt: str, max_tokens: int = 512) -> Dict[str, Any]:
        """
        Process text with the LLM and return response with confidence.
        
        Args:
            prompt (str): Prompt to send to the model
            max_tokens (int): Maximum tokens to generate
            
        Returns:
            dict: Response with text and confidence score
        """
        self._load_model()
        
        # Truncate prompt if too long
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.max_length)
        
        # Generate response
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids.to(self.model.device),
                max_new_tokens=max_tokens,
                temperature=0.3,  # Lower temperature for more deterministic responses
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                return_dict_in_generate=True,
                output_scores=True  # Get scores for confidence calculation
            )
        
        # Decode the response
        response_ids = outputs.sequences[0, inputs.input_ids.shape[1]:]
        response_text = self.tokenizer.decode(response_ids, skip_special_tokens=True)
        
        # Calculate confidence based on average token probability
        token_scores = torch.stack(outputs.scores, dim=0)
        token_probs = torch.softmax(token_scores, dim=-1)
        selected_probs = torch.gather(
            token_probs, 
            2, 
            response_ids[1:].unsqueeze(0).unsqueeze(-1)
        ).squeeze(-1)
        avg_prob = selected_probs.mean().item()  # Average probability as confidence
        
        return {
            "text": response_text,
            "confidence": avg_prob
        }
    
    def extract_sections(self, text: str) -> Dict[str, Any]:
        """
        Extract paper sections using LLM.
        
        Args:
            text (str): Raw paper text
            
        Returns:
            dict: Dictionary with sections and confidence
        """
        # Construct prompt for section extraction
        prompt = f"""
        Task: Extract the main sections from the following academic paper text.
        
        Instructions:
        1. Identify all major section headings
        2. Extract the content for each section
        3. Return a JSON object with section titles as keys and section text as values
        4. Be precise and maintain original content structure
        5. If a section is unclear, indicate with a confidence level below 0.7
        
        Paper text:
        {text[:10000]}...  # Truncated if long
        
        Format your response as valid JSON only like this:
        {{
          "sections": {{
            "section_title_1": "section_content_1",
            "section_title_2": "section_content_2"
          }},
          "section_confidence": {{
            "section_title_1": 0.95,
            "section_title_2": 0.85
          }}
        }}
        """
        
        result = self.process_text(prompt)
        
        try:
            # Parse JSON from response
            json_start = result["text"].find("{")
            json_end = result["text"].rfind("}")
            
            if json_start >= 0 and json_end > json_start:
                json_str = result["text"][json_start:json_end+1]
                parsed = json.loads(json_str)
                
                # Add overall confidence
                parsed["overall_confidence"] = result["confidence"]
                return parsed
                
        except Exception as e:
            print(f"Failed to parse LLM section extraction output: {e}")
        
        # Return empty result if parsing fails
        return {
            "sections": {},
            "section_confidence": {},
            "overall_confidence": result["confidence"]
        }
    
    def extract_terminology(self, text: str, top_n: int = 20) -> Dict[str, Any]:
        """
        Extract important terminology with definitions.
        
        Args:
            text (str): Paper text
            top_n (int): Number of terms to extract
            
        Returns:
            dict: Dictionary with terms, definitions and confidence
        """
        prompt = f"""
        Task: Extract the {top_n} most important technical terms from this academic paper and provide definitions.
        
        Paper text:
        {text[:10000]}...  # Truncated if long
        
        Format your response as valid JSON with this structure:
        {{
          "terms": [
            {{"term": "term_1", "score": 0.95}},
            {{"term": "term_2", "score": 0.87}}
          ],
          "definitions": {{
            "term_1": "definition_1",
            "term_2": "definition_2"
          }},
          "term_confidence": {{
            "term_1": 0.95,
            "term_2": 0.82
          }}
        }}
        
        Note: Include confidence scores (0-1) for each term based on how clearly it's defined in the paper.
        """
        
        result = self.process_text(prompt)
        
        try:
            # Parse JSON from response
            json_start = result["text"].find("{")
            json_end = result["text"].rfind("}")
            
            if json_start >= 0 and json_end > json_start:
                json_str = result["text"][json_start:json_end+1]
                parsed = json.loads(json_str)
                
                # Add overall confidence
                parsed["overall_confidence"] = result["confidence"]
                return parsed
                
        except Exception as e:
            print(f"Failed to parse LLM terminology extraction output: {e}")
        
        # Return empty result if parsing fails
        return {
            "terms": [],
            "definitions": {},
            "term_confidence": {},
            "overall_confidence": result["confidence"]
        }
    
    def summarize_section(self, section_text: str, length: str = "medium") -> Dict[str, Any]:
        """
        Generate a summary of a paper section with confidence.
        
        Args:
            section_text (str): Text of the section
            length (str): Desired summary length (short/medium/long)
            
        Returns:
            dict: Summary with confidence score
        """
        # Length in sentences
        length_guide = {
            "short": "1-2 sentences",
            "medium": "3-5 sentences",
            "long": "6-8 sentences"
        }
        
        prompt = f"""
        Task: Summarize this section from an academic paper in {length_guide[length]}.
        
        Section text:
        {section_text[:5000]}...  # Truncated if long
        
        Provide a precise, factual summary with no speculation. Mark any uncertain points with [?].
        """
        
        result = self.process_text(prompt)
        
        # Clean up response
        summary = result["text"].strip()
        
        # Number of [?] markers indicates uncertainty
        uncertainty_markers = summary.count("[?]")
        
        # Adjust confidence based on uncertainty markers
        adjusted_confidence = max(0.1, result["confidence"] - (uncertainty_markers * 0.1))
        
        return {
            "summary": summary,
            "confidence": adjusted_confidence
        }