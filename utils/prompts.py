"""
Centralized storage for prompts used in paper analysis.
These can be extended and refined based on testing results.
"""

# Base template for all paper analysis
BASE_ANALYSIS_TEMPLATE = """
You are an expert academic researcher analyzing a research paper.
Paper Title: {title}
Authors: {authors}

I'm showing you images of this paper. Please analyze the content carefully, 
focusing on text, figures, tables, and equations.
"""

# Comprehensive analysis prompt
COMPREHENSIVE_ANALYSIS_PROMPT = BASE_ANALYSIS_TEMPLATE + """
Provide a comprehensive analysis of this paper with the following sections:

1. SUMMARY: A concise 3-5 sentence summary of what this paper is about

2. KEY INNOVATIONS: What are the novel contributions of this paper? What sets it apart 
from previous work? (bullet points)

3. TECHNIQUES: What are the key techniques or methods introduced? Explain them concisely 
but with sufficient technical detail for implementation. (bullet points with explanations)

4. PRACTICAL VALUE: How practical is this research? Could it be implemented with reasonable 
effort? What real-world applications does it enable? Rate practicality from 1-10 and explain your rating.

5. LIMITATIONS: What are the main limitations or drawbacks? (bullet points)

Write in a clear, expert academic tone. Be specific and precise, avoiding vague statements.
"""

# Key insights analysis prompt
KEY_INSIGHTS_PROMPT = BASE_ANALYSIS_TEMPLATE + """
Focus on extracting the most important insights from this paper:

1. What's fundamentally new in this paper?
2. How does it advance the field?
3. What are its most important findings or conclusions?

Be concise but specific, avoiding general statements.
"""

# Techniques analysis prompt
TECHNIQUES_PROMPT = BASE_ANALYSIS_TEMPLATE + """
Focus on the technical methodology of this paper:

1. Identify and explain all key techniques, algorithms, or methods
2. Provide sufficient detail to understand how they could be implemented
3. Organize techniques in order of importance to the paper's contributions

Be technically precise and implementation-focused.
"""

# Practical value assessment prompt
PRACTICAL_VALUE_PROMPT = BASE_ANALYSIS_TEMPLATE + """
Assess the practical value of this research:

1. Rate practicality from 1-10 and explain your rating
2. What would be required to implement these ideas?
3. What real-world applications could benefit from this work?
4. What are the main obstacles to practical application?

Focus on real-world utility and implementation considerations.
"""

def get_prompt(prompt_type, metadata):
    """
    Get formatted prompt based on type and paper metadata.
    
    Args:
        prompt_type: Type of prompt to return
        metadata: Paper metadata dictionary
        
    Returns:
        Formatted prompt string
    """
    title = metadata.get("title", "Unknown Title")
    authors = metadata.get("author", "Unknown Authors")
    
    prompt_templates = {
        "comprehensive": COMPREHENSIVE_ANALYSIS_PROMPT,
        "key_insights": KEY_INSIGHTS_PROMPT,
        "techniques": TECHNIQUES_PROMPT,
        "practical_value": PRACTICAL_VALUE_PROMPT,
    }
    
    template = prompt_templates.get(prompt_type, COMPREHENSIVE_ANALYSIS_PROMPT)
    return template.format(title=title, authors=authors)