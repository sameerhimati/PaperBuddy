"""
Prompt templates for different analysis types in PaperBuddy
"""

from typing import Dict, Any, Optional

# Base template for all paper analysis
BASE_ANALYSIS_TEMPLATE = """
You are an expert academic researcher analyzing a research paper.

Paper Title: {title}
Authors: {authors}

I'm showing you images of this paper. Please analyze the content carefully, 
focusing on text, figures, tables, and equations.

IMPORTANT GUIDELINES:
1. Be objective and critically evaluate the work - NOT all papers make significant contributions
2. Use the FULL range of the 1-10 scale for ratings:
   - 1-3: Below average contributions/approaches
   - 4-6: Average quality for the field
   - 7-8: Good contributions, but not revolutionary
   - 9-10: Exceptional, field-changing work (rare)
3. Support ALL ratings with specific evidence from the paper
4. Identify at least 2-3 SPECIFIC limitations or weaknesses
5. Format all ratings as: Rating: X/10 - followed by justification
"""

# Comprehensive analysis prompt
COMPREHENSIVE_ANALYSIS_PROMPT = """
{base_template}

REQUIRED OUTPUT FORMAT:
SUMMARY
[A concise 3-5 sentence summary]

KEY INNOVATIONS (Rate novelty X/10)
* [Key innovation 1]
* [Key innovation 2]
...

TECHNIQUES (Rate technical quality X/10)
* [Technique 1]
* [Technique 2]
...

PRACTICAL VALUE (Rate practicality X/10)
* [Application point 1]
* [Application point 2]
...

LIMITATIONS
* [Limitation 1]
* [Limitation 2]
...
"""

# Quick Summary prompt
QUICK_SUMMARY_PROMPT = """
{base_template}

Provide a quick overview of this paper for a busy reader:

1. Give a single paragraph (3-5 sentences) summarizing the paper's core contribution and significance.

2. Provide 5 bullet points:
   - The specific problem addressed
   - The key innovation introduced (Rate novelty X/10)
   - The main results/findings
   - The most significant limitation
   - The most promising application

Be concise but specific. The entire summary should be readable in under 1 minute.
"""

# Technical Deep Dive prompt
TECHNICAL_DEEP_DIVE_PROMPT = """
{base_template}

Provide a detailed technical analysis focusing on methods, algorithms, and implementation:

CORE ALGORITHMS & METHODS (Rate technical sophistication X/10)
* [Describe each algorithm in technical detail]
* [Include pseudocode or equations if present]

IMPLEMENTATION DETAILS
* [Architectural details]
* [Training procedures/hyperparameters]
* [Data processing pipeline]

TECHNICAL EVALUATION & RESULTS
* [Benchmarking methodology]
* [Performance metrics and their significance]
* [Ablation studies or component analyses]

TECHNICAL LIMITATIONS
* [Mathematical or theoretical limitations]
* [Implementation constraints]
* [Evaluation gaps]

This analysis should provide enough detail for replication or adaptation of the methods.
"""

# Practical Applications prompt
PRACTICAL_APPLICATIONS_PROMPT = """
{base_template}

Focus exclusively on the real-world applications and practical implementation:

INDUSTRY RELEVANCE (Rate commercial potential X/10)
* [Specific industries or domains that could apply this]
* [Real-world problems it addresses]

IMPLEMENTATION REQUIREMENTS
* [Hardware/software requirements]
* [Data and computational resources needed]
* [Expertise required]

COMPARISON TO ALTERNATIVES
* [How this approach compares to existing solutions]
* [Tradeoffs (speed, accuracy, cost, etc.)]

ADOPTION ROADMAP
* [Steps needed for production implementation]
* [Potential challenges and solutions]
* [Timeline for practical adoption]

LIMITATIONS FOR PRACTICAL USE
* [Specific barriers to real-world adoption]
* [Missing components for production readiness]
"""

# Simplified explanation (ELI5) prompt
SIMPLIFIED_PROMPT = """
You are explaining a complex research paper to someone with no technical background in this field.

Paper Title: {title}
Authors: {authors}

I'm showing you images of this paper. Create a simplified explanation that:

1. Explains what problem the research solves in everyday terms
2. Why this matters in the real world with concrete examples
3. The main idea of the solution using analogies and simple concepts
4. How this might benefit people in practical terms
5. Any limitations in simple terms

Rules:
- Use NO technical jargon without explaining it
- Write at an 8th grade reading level
- Use everyday analogies and metaphors
- Keep your explanation under 500 words total

Start with "This paper is about..." and focus on making the core ideas accessible to anyone.
"""

# Terminology extraction prompt
TERMINOLOGY_PROMPT = """
You are analyzing an academic paper to extract key terminology and concepts.

Paper Title: {title}
Authors: {authors}

I'm showing you images of this paper. Extract 5-10 key technical terms, concepts or methods that are important for understanding this paper.

For each term, provide:
1. A formal definition (as it would appear in a textbook)
2. A simplified explanation for non-experts

FORMAT YOUR RESPONSE AS JSON ONLY:
{{
  "Term Name": {{
    "definition": "Formal/technical definition",
    "explanation": "Simpler explanation for non-experts"
  }},
  "Another Term": {{
    "definition": "Formal/technical definition",
    "explanation": "Simpler explanation for non-experts"
  }}
}}
"""

# Field tags prompt
FIELD_TAGS_PROMPT = """
Based on this paper title and abstract, identify 2-4 main research fields or subfields.
Return ONLY a JSON object with field names as keys, where each field has a short description and link.

Title: {title}
Abstract: {abstract}

Example response:
{{
  "Computer Vision": {{
    "description": "Field focused on enabling computers to derive information from images",
    "link": "https://en.wikipedia.org/wiki/Computer_vision"
  }},
  "Deep Learning": {{
    "description": "Machine learning approach using neural networks with many layers",
    "link": "https://en.wikipedia.org/wiki/deep_learning"
  }}
}}

IMPORTANT: Respond with JSON ONLY, no extra text.
"""

# Citation format prompt
PAPER_CITATION_PROMPT = """
Create a proper academic citation for this paper in the following formats:
1. APA
2. MLA
3. Chicago
4. BibTeX

Paper Title: {title}
Authors: {authors}
Year: {year}
URL: {url}
DOI: {doi}

FORMAT YOUR RESPONSE AS JSON ONLY:
{{
  "APA": "Complete APA citation",
  "MLA": "Complete MLA citation",
  "Chicago": "Complete Chicago citation",
  "BibTeX": "Complete BibTeX citation"
}}
"""

# Paper comparison prompt
PAPER_COMPARISON_PROMPT = """
You are analyzing the relationship between two academic papers.

Paper 1:
Title: {title1}
Authors: {authors1}

Paper 2:
Title: {title2}
Authors: {authors2}

Compare these papers on the following dimensions:
1. Core approaches and methodologies
2. Contributions and innovations
3. Performance and results
4. Strengths and limitations
5. How Paper 2 builds upon or differs from Paper 1

FORMAT YOUR ANALYSIS USING THESE HEADINGS:
RELATIONSHIP SUMMARY
[Brief overview of how these papers relate]

METHODOLOGICAL COMPARISON
[Comparison of approaches]

KEY DIFFERENCES
[Main differences in contributions]

EVOLUTIONARY PROGRESS
[How the field advanced between these papers]

COMBINED INSIGHTS
[What insights we gain from considering both papers together]
"""

# Q&A prompt
PAPER_QA_PROMPT = """
You are an expert who has deeply read and understood this academic paper.

Paper Title: {title}
Authors: {authors}

Based on the paper content, provide a detailed and accurate answer to the following question:

QUESTION: {question}

In your answer:
1. Cite specific sections, figures, or tables from the paper
2. Explain technical concepts if needed for comprehension
3. Be objective and accurate based only on what's in the paper
4. Note any limitations or uncertainties in the paper related to this question
5. If the paper doesn't address the question, clearly state this rather than speculate

ANSWER:
"""


def get_prompt(prompt_type: str, metadata: Dict[str, Any], **kwargs) -> str:
    """
    Get formatted prompt based on type and paper metadata
    
    Args:
        prompt_type: Type of prompt to return
        metadata: Paper metadata dictionary
        **kwargs: Additional keyword arguments for specific prompts
        
    Returns:
        Formatted prompt string
    """
    title = metadata.get("title", "Unknown Title")
    authors = metadata.get("author", "Unknown Authors")
    abstract = metadata.get("abstract", "")[:500]  # Limit abstract length
    
    # Handle simplified override
    if kwargs.get("simplified", False) or prompt_type == "simplified":
        return SIMPLIFIED_PROMPT.format(title=title, authors=authors)
    
    # Base template with metadata
    base = BASE_ANALYSIS_TEMPLATE.format(title=title, authors=authors)
    
    # Select appropriate template based on analysis type
    if prompt_type == "comprehensive":
        return COMPREHENSIVE_ANALYSIS_PROMPT.format(base_template=base)
    elif prompt_type == "quick_summary":
        return QUICK_SUMMARY_PROMPT.format(base_template=base)
    elif prompt_type == "technical":
        return TECHNICAL_DEEP_DIVE_PROMPT.format(base_template=base)
    elif prompt_type == "practical":
        return PRACTICAL_APPLICATIONS_PROMPT.format(base_template=base)
    elif prompt_type == "terminology":
        return TERMINOLOGY_PROMPT.format(title=title, authors=authors)
    elif prompt_type == "field_tags":
        return FIELD_TAGS_PROMPT.format(title=title, abstract=abstract)
    elif prompt_type == "citation":
        return PAPER_CITATION_PROMPT.format(
            title=title,
            authors=authors,
            year=metadata.get("year", kwargs.get("year", "Unknown")),
            url=metadata.get("url", kwargs.get("url", "")),
            doi=metadata.get("doi", kwargs.get("doi", ""))
        )
    elif prompt_type == "comparison":
        # For paper comparison prompt
        return PAPER_COMPARISON_PROMPT.format(
            title1=title,
            authors1=authors,
            title2=kwargs.get("title2", "Unknown Title"),
            authors2=kwargs.get("authors2", "Unknown Authors")
        )
    elif prompt_type == "qa":
        # For paper Q&A prompt
        return PAPER_QA_PROMPT.format(
            title=title,
            authors=authors,
            question=kwargs.get("question", "What is the main contribution of this paper?")
        )
    else:
        # Default to comprehensive for unknown types
        return COMPREHENSIVE_ANALYSIS_PROMPT.format(base_template=base)


def get_section_markers(analysis_type: str) -> Dict[str, str]:
    """
    Get section markers for extracting content from analysis
    
    Args:
        analysis_type: Type of analysis
        
    Returns:
        Dictionary mapping section names to their markers
    """
    markers = {
        "comprehensive": {
            "summary": "SUMMARY",
            "key_innovations": "KEY INNOVATIONS",
            "techniques": "TECHNIQUES",
            "practical_value": "PRACTICAL VALUE",
            "limitations": "LIMITATIONS"
        },
        "technical": {
            "algorithms": "CORE ALGORITHMS & METHODS",
            "implementation": "IMPLEMENTATION DETAILS",
            "evaluation": "TECHNICAL EVALUATION & RESULTS",
            "limitations": "TECHNICAL LIMITATIONS"
        },
        "practical": {
            "relevance": "INDUSTRY RELEVANCE",
            "requirements": "IMPLEMENTATION REQUIREMENTS",
            "comparison": "COMPARISON TO ALTERNATIVES",
            "roadmap": "ADOPTION ROADMAP",
            "limitations": "LIMITATIONS FOR PRACTICAL USE"
        },
        "comparison": {
            "summary": "RELATIONSHIP SUMMARY",
            "methodological": "METHODOLOGICAL COMPARISON",
            "differences": "KEY DIFFERENCES",
            "evolution": "EVOLUTIONARY PROGRESS",
            "insights": "COMBINED INSIGHTS"
        }
    }
    
    return markers.get(analysis_type, markers["comprehensive"])