# Base template for all paper analysis
BASE_ANALYSIS_TEMPLATE = """
You are an expert academic researcher analyzing a research paper.
Paper Title: {title}
Authors: {authors}

I'm showing you images of this paper. Please analyze the content carefully, 
focusing on text, figures, tables, and equations.

IMPORTANT GUIDELINES:
1. Be objective and critical - not all papers make significant contributions
2. Use a 1-10 scale for ratings, where 5 is average for papers in this field
3. Support all claims with specific evidence from the paper
4. Avoid vague statements or generic praise
5. Be specific about limitations and weaknesses
"""

KEY_DEFINITIONS_PROMPT = """
Based on this paper analysis, identify 5-10 key terms, concepts, or techniques that are important for understanding the paper.

For each term:
1. Provide a formal, technical definition as it would appear in a textbook or academic paper
2. Provide a simpler explanation accessible to non-experts or beginners in the field

Format your response as a JSON dictionary with the term names as keys, and each value being a dictionary with "definition" and "explanation" keys.

Example format:
{
  "Term 1": {
    "definition": "The formal, technical definition",
    "explanation": "A simplified explanation for non-experts"
  },
  "Term 2": {
    "definition": "The formal, technical definition",
    "explanation": "A simplified explanation for non-experts"
  }
}
"""

# Comprehensive analysis prompt
COMPREHENSIVE_ANALYSIS_PROMPT = BASE_ANALYSIS_TEMPLATE + """
Provide a comprehensive analysis of this paper with the following sections:

SUMMARY
A concise 3-5 sentence summary of what this paper is about. Include the problem addressed, 
approach taken, and main findings. Be factual and specific.

KEY INNOVATIONS
What are the novel contributions of this paper? What sets it apart from previous work?
Be critical - many papers contain incremental advances rather than breakthrough innovations.
Rate the innovation on a scale of 1-10 and justify your rating.
Use bullet points for clarity.

TECHNIQUES
What specific techniques or methods does the paper introduce or utilize?
Explain them with sufficient technical detail that someone could understand the implementation approach.
Identify which techniques are novel versus standard approaches.
Use bullet points with brief explanations.

PRACTICAL VALUE
Assess how practical this research is for real-world applications.
Consider:
- What resources would be needed to implement these techniques?
- What obstacles or barriers exist to practical adoption?
- What specific applications would benefit most from this work?
Rate practicality from 1-10 and justify your rating with specific factors.

LIMITATIONS
What are the main limitations, weaknesses or drawbacks of this work?
Consider theoretical limitations, experimental design flaws, missing evaluations, etc.
Be specific and detailed - all research has limitations.
Use bullet points for clarity.

Format your response with clear section headings.
"""

# Quick Summary prompt (replaces Key Insights)
QUICK_SUMMARY_PROMPT = BASE_ANALYSIS_TEMPLATE + """
Provide a quick overview of this paper for a busy reader:

1. Give a single paragraph (3-5 sentences) summarizing the paper's core contribution, approach, and significance.

2. Follow with 3-5 bullet points highlighting:
   - The specific problem addressed
   - The key innovation or method introduced
   - The main results/findings
   - The most significant limitation
   - The most promising application

Be concise but specific. The entire summary should be readable in under 2 minutes.
"""

# Technical Deep Dive prompt
TECHNICAL_DEEP_DIVE_PROMPT = BASE_ANALYSIS_TEMPLATE + """
Provide a detailed technical analysis focusing exclusively on the methods, algorithms, and implementation details:

1. Core Algorithms & Methods:
   - Describe each key algorithm or method in technical detail
   - For each, explain mathematical foundations and how it functions
   - Include any relevant equations, pseudocode, or algorithmic steps
   - Specify computational complexity if mentioned

2. Implementation Details:
   - Architectural details (network layers, components, etc.)
   - Training procedures and hyperparameters
   - Data processing pipelines
   - Hardware/software requirements mentioned

3. Technical Evaluation:
   - Benchmarking methodologies
   - Comparison metrics and their significance
   - Ablation studies or component analyses
   - Statistical significance of results

This analysis should be useful for someone looking to implement or build upon this research.
Include enough technical detail that a skilled practitioner could understand how to reproduce the core approaches.
"""

# Practical Applications prompt
PRACTICAL_APPLICATIONS_PROMPT = BASE_ANALYSIS_TEMPLATE + """
Focus exclusively on the real-world applications and practical implementation of this research:

1. Industry Relevance:
   - Which specific industries or domains could apply this research?
   - What real-world problems does it solve or improve?
   - How mature is this research for production use? (Scale: 1-10)

2. Implementation Requirements:
   - Hardware/software requirements
   - Data and computational resources needed
   - Expertise required for implementation
   - Time and cost considerations

3. Comparison to Alternatives:
   - How does this approach compare to existing solutions?
   - What are the tradeoffs (speed, accuracy, cost, etc.)?
   - When would you choose this approach over alternatives?

4. Adoption Roadmap:
   - Steps needed to implement this in a production environment
   - Potential challenges and how to overcome them
   - Timeline for practical adoption (immediate, near-term, long-term)

This analysis should help decision-makers and practitioners evaluate whether and how to apply this research.
"""

# Simplified explanation (ELI5) prompt
SIMPLIFIED_PROMPT = """
You are explaining a complex research paper to someone with no technical background in this field.
Paper Title: {title}
Authors: {authors}

I'm showing you images of this paper. Create ONLY a simplified explanation that:

1. Explains what problem the research solves in everyday terms
2. Why this matters in the real world with concrete examples
3. The main idea of the solution using analogies and simple concepts
4. How this might benefit people in practical terms

Rules:
- Use NO technical jargon without explaining it
- Write at an 8th grade reading level or simpler
- Use everyday analogies and metaphors
- Keep your explanation under 500 words total
- DO NOT include any academic analysis or review - ONLY the simplified explanation

Start with "This paper is about..." and focus on making the core ideas accessible to anyone.
"""

def get_prompt(prompt_type, metadata, simplified=False):
    """
    Get formatted prompt based on type and paper metadata.
    
    Args:
        prompt_type: Type of prompt to return
        metadata: Paper metadata dictionary
        simplified: Whether to use simplified explanation mode
        
    Returns:
        Formatted prompt string
    """
    title = metadata.get("title", "Unknown Title")
    authors = metadata.get("author", "Unknown Authors")
    
    # If simplified is True, override with simplified prompt regardless of type
    if simplified or prompt_type == "simplified":
        return SIMPLIFIED_PROMPT.format(title=title, authors=authors)
    
    prompt_templates = {
        "comprehensive": COMPREHENSIVE_ANALYSIS_PROMPT,
        "quick_summary": QUICK_SUMMARY_PROMPT,
        "technical": TECHNICAL_DEEP_DIVE_PROMPT,
        "practical": PRACTICAL_APPLICATIONS_PROMPT,
    }
    
    template = prompt_templates.get(prompt_type, COMPREHENSIVE_ANALYSIS_PROMPT)
    return template.format(title=title, authors=authors)