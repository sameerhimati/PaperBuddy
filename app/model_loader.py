# app/model_loader.py
import os
import torch
from transformers import AutoTokenizer, AutoModel, AutoModelForTokenClassification

# Set environment variables to help avoid conflicts
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def load_section_scorer_models(model_name="allenai/specter"):
    """Load models needed for section scoring"""
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    return tokenizer, model

def load_terminology_models(model_name="distilbert-base-uncased"):
    """Load models needed for terminology extraction"""
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    return tokenizer, model