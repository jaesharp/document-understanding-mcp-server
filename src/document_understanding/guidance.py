"""
Guidance for document understanding tools.

This module contains comprehensive guidance for using the document understanding
tools, including hierarchical analysis framework, advanced strategies, and
implementation details.
"""

# Alternative Approaches to Document Analysis

ALTERNATIVE_APPROACHES = """
ALTERNATIVE APPROACHES TO PDF DOCUMENT ANALYSIS:

1. Structural-Based Extraction
   - Extract document outline/TOC first
   - Use outline to identify logical sections
   - Process each section as a complete unit
   - Adjust extraction detail based on section importance
   
   WHEN TO USE:
   * Documents with well-defined structure (chapters, sections)
   * PDFs with embedded outlines or clear heading hierarchy
   * When complete understanding of specific sections is critical
   * For technical documents, manuals, or academic papers
   
   ADVANTAGES:
   * Preserves logical document organisation
   * Ensures complete coverage of important sections
   * Maintains contextual integrity within sections

2. Content-Driven Adaptive Sampling
   - Start with low-detail scan of entire document
   - Identify content-rich areas (dense text, tables, images)
   - Increase sampling density in complex/important areas
   - Reduce sampling in repetitive or simple sections
   
   WHEN TO USE:
   * Documents with varying content density
   * When processing resources are limited
   * For initial triage of very large documents (100+ pages)
   * When document quality or formatting varies significantly
   
   ADVANTAGES:
   * Optimises resource allocation
   * Focuses attention on complex content
   * More efficient than fixed-rate sampling

3. Query-Guided Extraction
   - Start with specific search queries related to user needs
   - Identify pages containing relevant information
   - Extract and analyse only those pages in detail
   - Expand context as needed around key findings
   
   WHEN TO USE:
   * When looking for specific information
   * For targeted analysis rather than comprehensive understanding
   * When user has clear information needs
   * For large reference documents or compilations
   
   ADVANTAGES:
   * Highly efficient for specific information needs
   * Minimises processing of irrelevant content
   * Directly addresses user queries

4. Layered Progressive Analysis
   - Layer 1: Extract metadata, outline, and sample pages
   - Layer 2: Build structural map with section boundaries
   - Layer 3: Process high-priority sections in detail
   - Layer 4: Fill gaps in understanding as needed
   
   WHEN TO USE:
   * For comprehensive analysis of complex documents
   * When both overview and detailed understanding are needed
   * For documents requiring multiple levels of analysis
   * When processing time isn't severely constrained
   
   ADVANTAGES:
   * Builds understanding progressively
   * Balances broad coverage with detailed analysis
   * Provides both high-level and detailed views

5. Hybrid Visual-Textual Analysis
   - Extract layout information with visual elements
   - Create visual-textual map of document
   - Process text and images in context with each other
   - Use vision models for image-heavy sections
   
   WHEN TO USE:
   * Documents with significant visual content
   * Technical diagrams, charts, or illustrated materials
   * When visual and textual elements are interdependent
   * For presentations, brochures, or visual reports
   
   ADVANTAGES:
   * Maintains relationship between text and visuals
   * Better understanding of diagrams, charts, and figures
   * Captures information conveyed through layout and design

6. Full Sequential Processing
   - Process entire document sequentially in small chunks
   - Maintain complete context across chunk boundaries
   - Build comprehensive understanding of entire content
   - Track all cross-references and relationships
   
   WHEN TO USE:
   * When complete, detailed understanding is essential
   * For legal documents, contracts, or critical technical content
   * When document size is manageable
   * When accuracy is more important than processing speed
   
   ADVANTAGES:
   * Most comprehensive understanding
   * No missing content or context
   * Highest fidelity to original document
"""

# Issues with Basic Sampling Approach

SAMPLING_APPROACH_ISSUES = """
ISSUES WITH BASIC SAMPLING APPROACH:

1. Missing Critical Content
   - Important information may exist in pages that aren't sampled
   - Key sections, tables, or figures could be completely overlooked
   - Critical context needed to understand other parts of the document might be missed

2. Incomplete Document Structure Understanding
   - Sampling may not capture the true hierarchical structure of the document
   - Section transitions might occur between sampled pages
   - Subsections might be entirely missed, creating gaps in the structural map

3. Broken Contextual Continuity
   - Narrative flow and logical progression may be disrupted
   - References to previous content might be missed, leading to misinterpretation
   - Context-dependent information becomes difficult to interpret correctly

4. Inconsistent Terminology Tracking
   - Term definitions might be introduced in non-sampled pages
   - Acronyms may be defined in skipped sections
   - Variations in terminology usage across the document might be missed

5. Incomplete Cross-Reference Mapping
   - References between different parts of the document may be missed
   - Citations or footnotes might not be properly connected to their sources
   - Internal document links could be overlooked

6. Biased Understanding
   - Sampling may overemphasise certain document aspects while underrepresenting others
   - Could lead to incorrect conclusions about the document's main focus or purpose
   - May misrepresent the balance of content types (text, tables, images)

7. Difficulty with Sequential Content
   - Content that builds progressively across pages will be fragmented
   - Step-by-step instructions or procedures might be incomplete
   - Chronological narratives could be misunderstood

8. Challenges with Fixed Sampling Rate
   - Fixed sampling rate (every 10th page) doesn't adapt to document density
   - Some sections may require more granular sampling than others
   - No mechanism to identify when sampling rate should be adjusted
"""

# Selection Criteria for Choosing an Approach

APPROACH_SELECTION_CRITERIA = """
SELECTION CRITERIA FOR DOCUMENT ANALYSIS APPROACH:

Choose your approach based on:

1. Document Characteristics
   - Size (number of pages)
   - Complexity (structure, formatting, content types)
   - Presence of embedded outline/TOC
   - Balance of text vs. visual content
   - Content density and variation

2. Analysis Requirements
   - Need for comprehensive vs. targeted understanding
   - Importance of maintaining context
   - Specific information needs vs. general overview
   - Required accuracy and completeness

3. Resource Constraints
   - Available processing capacity (context window limitations)
   - Time constraints for analysis
   - Importance of efficiency vs. completeness

4. Document Type
   - Academic papers: Often benefit from Structural-Based Extraction
   - Technical manuals: May require Hybrid Visual-Textual Analysis
   - Legal documents: Often need Full Sequential Processing
   - Reference materials: Query-Guided Extraction works well
   - Visual reports: Hybrid Visual-Textual Analysis is ideal
   - Large textbooks: Layered Progressive Analysis is effective

The most effective strategy often combines elements from multiple approaches,
adapting to the specific document characteristics and analysis requirements.
"""

# Implementation Strategies for Each Approach

STRUCTURAL_BASED_EXTRACTION_IMPLEMENTATION = """
IMPLEMENTING STRUCTURAL-BASED EXTRACTION:

1. Initial Structure Analysis
   TOOL CALL: extract_pdf_outline
   Parameters:
     pdf_path: document.pdf
   
   If no outline exists:
     TOOL CALL: extract_pdf_layout
     Parameters:
       pdf_path: document.pdf
       detail_level: "blocks"
       pages: "1-20"  # Check first 20 pages for heading patterns
   
   Identify heading patterns based on:
   - Font size/weight variations
   - Position/alignment on page
   - Numbering patterns
   
   Create synthetic TOC based on identified headings

2. Section-by-Section Processing
   For each section in outline:
     TOOL CALL: extract_pdf_contents
     Parameters:
       pdf_path: document.pdf
       pages: <section page range>
     
     Process extracted section content

3. Adaptive Detail Level
   Determine importance of each section
   
   For high importance sections:
     TOOL CALL: extract_pdf_layout
     Parameters:
       pdf_path: document.pdf
       pages: <section page range>
       detail_level: "words"
   
   For medium importance sections:
     TOOL CALL: extract_pdf_layout
     Parameters:
       pdf_path: document.pdf
       pages: <section page range>
       detail_level: "lines"
   
   For low importance sections:
     TOOL CALL: extract_pdf_layout
     Parameters:
       pdf_path: document.pdf
       pages: <section page range>
       detail_level: "blocks"
"""

CONTENT_DRIVEN_ADAPTIVE_SAMPLING_IMPLEMENTATION = """
IMPLEMENTING CONTENT-DRIVEN ADAPTIVE SAMPLING:

1. Initial Low-Detail Scan
   TOOL CALL: extract_pdf_metadata
   Parameters:
     pdf_path: document.pdf
   
   Calculate an appropriate sample rate:
   sample_rate = max(1, page_count // 20)  # Sample at most 20 pages
   
   TOOL CALL: extract_pdf_layout
   Parameters:
     pdf_path: document.pdf
     pages: <sample pages string>
     detail_level: "blocks"

2. Content Density Analysis
   For each sampled page:
     Calculate text density:
     - Number of text blocks
     - Total character count
     
     Check for images:
     - Number of images
     - Image sizes
     
     Estimate table likelihood:
     - Regular spacing patterns
     - Grid-like text arrangement
     
     Calculate overall density score

3. Adaptive Sampling Strategy
   Group pages by density:
   - High density (score > 0.7)
   - Medium density (0.3 <= score <= 0.7)
   - Low density (score < 0.3)
   
   For high-density pages:
     TOOL CALL: extract_pdf_contents
     Parameters:
       pdf_path: document.pdf
       pages: <high density page ranges>
   
   For medium-density pages:
     TOOL CALL: extract_pdf_contents
     Parameters:
       pdf_path: document.pdf
       pages: <medium density page ranges>
   
   For low-density pages:
     Sample a small subset for verification
"""

QUERY_GUIDED_EXTRACTION_IMPLEMENTATION = """
IMPLEMENTING QUERY-GUIDED EXTRACTION:

1. Initial Query-Based Search
   Define key terms based on user query (e.g., "neural networks", "deep learning")
   
   For each term:
     TOOL CALL: search_pdf_text
     Parameters:
       pdf_path: document.pdf
       query: <search term>
     
     Collect all page numbers with matches
   
   Group consecutive pages into page ranges

2. Context Expansion
   For each page range:
     Add one page before and after for context
     
     Ensure page numbers are valid (not below 1 or above page_count)
   
   Merge overlapping page ranges

3. Targeted Extraction and Analysis
   For each page range:
     TOOL CALL: extract_pdf_contents
     Parameters:
       pdf_path: document.pdf
       pages: <page range>
     
     TOOL CALL: extract_pdf_layout
     Parameters:
       pdf_path: document.pdf
       pages: <page range>
       detail_level: "blocks"
     
     TOOL CALL: extract_tables
     Parameters:
       pdf_path: document.pdf
       pages: <page range>
     
     Analyse extracted content focusing on query terms

4. Relevance Scoring and Summarisation
   Score content based on:
     - Term frequency
     - Proximity of terms
     - Presence in headings/structural elements
   
   Sort pages by relevance score
   
   Summarise top 10 most relevant pages
"""

LAYERED_PROGRESSIVE_ANALYSIS_IMPLEMENTATION = """
IMPLEMENTING LAYERED PROGRESSIVE ANALYSIS:

1. Layer 1: Initial Assessment
   TOOL CALL: extract_pdf_metadata
   Parameters:
     pdf_path: document.pdf
   
   TOOL CALL: extract_pdf_outline
   Parameters:
     pdf_path: document.pdf
   
   Select key pages to sample:
   - First page (title, TOC)
   - Last page (conclusions, references)
   - Quarter points (25%, 50%, 75%)
   
   TOOL CALL: extract_pdf_contents
   Parameters:
     pdf_path: document.pdf
     pages: <sample pages string>

2. Layer 2: Structural Mapping
   If outline exists:
     Use it as document structure
   Else:
     Sample layout at regular intervals
     
     TOOL CALL: extract_pdf_layout
     Parameters:
       pdf_path: document.pdf
       pages: <sample pages string>
       detail_level: "blocks"
     
     Identify structural elements:
     - Heading patterns
     - Section boundaries
     - Repeated formatting patterns
     
     Create synthetic document structure

3. Layer 3: Priority Section Analysis
   Identify high-priority sections based on:
   - Position in structure (introduction, conclusion)
   - Key terms matching user's focus
   - Importance based on outline level
   
   For each priority section:
     TOOL CALL: extract_pdf_contents
     Parameters:
       pdf_path: document.pdf
       pages: <section page range>
     
     TOOL CALL: extract_pdf_layout
     Parameters:
       pdf_path: document.pdf
       pages: <section page range>
       detail_level: "blocks"
     
     Check for tables and images:
     TOOL CALL: extract_tables
     Parameters:
       pdf_path: document.pdf
       pages: <section page range>
     
     TOOL CALL: extract_images
     Parameters:
       pdf_path: document.pdf
       pages: <section page range>
       output_directory: "./extracted_images"
     
     Analyse the section in detail

4. Layer 4: Gap Filling
   Identify gaps in understanding
   
   For each gap:
     TOOL CALL: extract_pdf_contents
     Parameters:
       pdf_path: document.pdf
       pages: <gap page range>
     
     Analyse gap content
"""

HYBRID_VISUAL_TEXTUAL_ANALYSIS_IMPLEMENTATION = """
IMPLEMENTING HYBRID VISUAL-TEXTUAL ANALYSIS:

1. Create Visual-Textual Map
   TOOL CALL: extract_pdf_layout
   Parameters:
     pdf_path: document.pdf
     include_images: true
     detail_level: "blocks"
   
   For each page:
     Create page map with:
     - Text blocks
     - Image information
     - Spatial relationships
     
     For each image:
       Find related text by proximity
       Record text-image relationships

2. Process Text Content
   TOOL CALL: extract_pdf_contents
   Parameters:
     pdf_path: document.pdf
   
   Process text content with focus on:
   - References to figures/images
   - Captions and descriptions
   - Technical terminology

3. Process Visual Content
   TOOL CALL: extract_images
   Parameters:
     pdf_path: document.pdf
     output_directory: "./extracted_images"
     save_without_returning_data: true
   
   For each image:
     Get related text context
     
     Analyse image with context:
     - Image type (chart, diagram, photo)
     - Content description
     - Relationship to surrounding text
     
     For charts/graphs:
       Identify axes, legends, data points
     
     For diagrams:
       Identify components, connections, labels

4. Integrated Analysis
   Combine text and visual analyses
   
   Generate insights from combined analysis:
   - How images support textual content
   - Information conveyed primarily through visuals
   - Reconcile textual and visual information
"""

FULL_SEQUENTIAL_PROCESSING_IMPLEMENTATION = """
IMPLEMENTING FULL SEQUENTIAL PROCESSING:

1. Sequential Chunk Processing
   TOOL CALL: extract_pdf_metadata
   Parameters:
     pdf_path: document.pdf
   
   Define chunk size (5-10 pages per chunk)
   
   For each chunk:
     TOOL CALL: extract_pdf_contents
     Parameters:
       pdf_path: document.pdf
       pages: <chunk page range>
     
     Process chunk with awareness of document position

2. Maintain Cross-Chunk Context
   Initialize context tracking for:
   - Current section/topic
   - Open discussion points
   - Defined terms and acronyms
   - References and citations
   - Narrative state
   
   For each chunk:
     Update context based on chunk content
     
     Process chunk with current context
     
     Update context for next chunk

3. Cross-Reference Resolution
   Collect all references:
   - Citations
   - Footnotes
   - Figure references
   - Internal links
   
   Resolve each reference:
   - Link to source content
   - Connect related information

4. Complete Document Analysis
   Combine all processed chunks
   
   Generate complete document analysis:
   - Full structure with sections and subsections
   - Comprehensive terminology glossary
   - All resolved references
   - Complete narrative understanding
"""

# Implementation Strategies - combined

IMPLEMENTATION_STRATEGIES = f"""
IMPLEMENTATION STRATEGIES FOR ADVANCED DOCUMENT ANALYSIS:

{STRUCTURAL_BASED_EXTRACTION_IMPLEMENTATION}

{CONTENT_DRIVEN_ADAPTIVE_SAMPLING_IMPLEMENTATION}

{QUERY_GUIDED_EXTRACTION_IMPLEMENTATION}

{LAYERED_PROGRESSIVE_ANALYSIS_IMPLEMENTATION}

{HYBRID_VISUAL_TEXTUAL_ANALYSIS_IMPLEMENTATION}

{FULL_SEQUENTIAL_PROCESSING_IMPLEMENTATION}
"""

# Hierarchical Document Analysis Framework - Individual Sections

# 1. Initial Document Assessment
INITIAL_DOCUMENT_ASSESSMENT = """
Always begin with metadata and outline extraction to understand document scope.
For documents without embedded outlines, immediately proceed to structural analysis.
Note total page count to plan chunking strategy for large documents.
Check if document contains images or vector graphics to prepare appropriate extraction tools.
""".strip()

# 2. Structural Mapping
STRUCTURAL_MAPPING = """
Look for consistent formatting patterns that indicate document structure.
Pay special attention to:
* Font size/style variations (potential headings)
* Indentation patterns (hierarchical structure)
* Page layout changes (section boundaries)
* Running headers/footers (document organisation)
Create a structural map with page ranges for each identified section.
""".strip()

# 3. Synthetic TOC Generation
SYNTHETIC_TOC_GENERATION = """
Identify heading patterns based on:
* Text formatting (size, weight, style)
* Numbering schemes (1.1, 1.2, etc.)
* Positional consistency (top of page, centred, etc.)
* Isolation from body text
Record hierarchical relationships between headings.
Generate a synthetic TOC with page ranges for each section.
Use this TOC to guide subsequent targeted extraction.
""".strip()

# 4. Terminology Extraction
TERMINOLOGY_EXTRACTION = """
Identify acronym definitions using these high-confidence patterns:
* Term (ACRONYM) pattern
* ACRONYM (Term) pattern
* "abbreviated as", "known as" phrases
Look for term introductions with these indicators:
* Typographical emphasis (bold, italic)
* Definitional phrases ("is defined as", "refers to")
* Contextual markers (followed by explanations)
Track first appearances of terms and their subsequent uses.
Record page numbers for all term occurrences.
Build a comprehensive glossary with cross-references.
""".strip()

# 5. Content Type Extraction
CONTENT_TYPE_EXTRACTION = """
Use the structural map to target specific content types:
* For text-heavy sections: extract_pdf_contents
* For tabular data: extract_tables
* For figures/diagrams: extract_images with surrounding context
Process each section with appropriate detail level and extraction method.
Maintain contextual relationships between different content types.
""".strip()

# 6. Contextual Analysis
CONTEXTUAL_ANALYSIS = """
When extracting specific elements (tables, images), always include surrounding text.
Capture captions, references, and explanatory text.
Link extracted elements to relevant terms in the glossary.
Maintain section context for all extracted content.
""".strip()

# 7. Progressive Refinement
PROGRESSIVE_REFINEMENT = """
Start with broad document understanding and progressively refine.
Sequence your analysis:
1. Document scope and structure
2. Section identification and prioritisation
3. Detailed extraction of priority sections
4. Targeted extraction of specific elements
5. Connection of related content across sections
This incremental approach balances comprehensive coverage with efficiency.
""".strip()

# Document Structure Analysis - Tool Selection Framework

# 1. Document Structure Analysis
DOCUMENT_STRUCTURE_ANALYSIS = """
First step: extract_pdf_metadata to get page count and check for images/drawings
Second step: extract_pdf_outline to check for embedded table of contents
If no outline exists, create synthetic TOC by analysing layout patterns:
* Extract layout on sample pages with detail_level="blocks"
* Identify potential headings based on formatting
* Map document structure with hierarchical relationships
* Record page numbers for each identified section
""".strip()

# 2. Content Location
CONTENT_LOCATION = """
Use search_pdf_text to quickly locate specific terms or sections
Apply search patterns for key terms, headings, or section markers
Create a map of content locations with page references
""".strip()

# 3. Targeted Content Extraction
TARGETED_CONTENT_EXTRACTION = """
For text content: extract_pdf_contents on specific page ranges
For tabular data: extract_tables on pages with identified tables
For images/figures: extract_images with appropriate context
""".strip()

# 4. Special Content Handling
SPECIAL_CONTENT_HANDLING = """
For multilingual documents: detect_language before extraction
For scanned documents: use OCR with appropriate language settings
For image analysis: provide surrounding text context from the document
""".strip()

# Performance Optimization - Efficient Processing Strategies

# 1. Chunking Strategies
CHUNKING_STRATEGIES = """
For documents >50 pages, always use hierarchical approach
Process in logical chunks based on document structure, never using arbitrary or periodic sampling
Consider content-aware approaches to document analysis (see ALTERNATIVE_APPROACHES)
Recommended chunk sizes:
* Initial assessment: full document metadata + strategic sample pages
* Structure mapping: 10-20 pages at a time focusing on section boundaries
* Detailed extraction: 5-10 pages at a time within identified sections
* Image extraction: 1-3 pages at a time with surrounding context
""".strip()

# 2. Efficient Retrieval
EFFICIENT_RETRIEVAL = """
Use search functionality to quickly locate sections of interest
Apply term extraction patterns during initial structural analysis
Build and refine glossary and TOC continuously throughout analysis
Use page references from synthetic TOC to target specific extractions
""".strip()

# 3. Context Management
CONTEXT_MANAGEMENT = """
Maintain cross-references between extracted content, terms, and document structure
Track document hierarchy to provide context for extracted fragments
Link related content across different sections
Build a comprehensive understanding progressively
""".strip()

# 4. Resource Conservation
RESOURCE_CONSERVATION = """
Avoid extracting entire documents at high detail levels
Use the minimum detail level required for each task
Prioritise targeted extraction over comprehensive processing
Balance between detail and context window limitations
""".strip()

# Image Analysis - Specialised Guidance

# 1. Image Identification
IMAGE_IDENTIFICATION = """
Use extract_pdf_metadata to check if document contains images
Use extract_pdf_layout with include_images=true to locate image positions
Note page numbers and positions of all images for targeted extraction
""".strip()

# 2. Contextual Extraction
IMAGE_CONTEXTUAL_EXTRACTION = """
Before extracting images, capture surrounding text context:
* Captions (typically below or beside images)
* References to the image in nearby text
* Figure numbers and titles
* Legend information for charts/graphs
Use extract_pdf_layout to identify text blocks near images
""".strip()

# 3. Efficient Image Handling
EFFICIENT_IMAGE_HANDLING = """
Use output_directory and save_without_returning_data=true to save images
Process images individually with image understanding tools
Provide the captured context when analysing each image
Link image analysis back to document structure
""".strip()

# 4. Content-Type Specific Analysis
IMAGE_CONTENT_ANALYSIS = """
For charts/graphs: focus on axis labels, legends, and data patterns
For diagrams: identify labels, connections, and structural elements
For photographs: describe visual content and relate to document context
For technical illustrations: note components, labels, and relationships
""".strip()


# Helper function for formatting sections
def _format_section(section, indent=3):
    """Format a section text with proper indentation for combined output."""
    indentation = " " * indent
    return indentation + section.replace("\n", f"\n{indentation}")


# Complete Document Analysis Framework
DOCUMENT_ANALYSIS_FRAMEWORK = f"""
HIERARCHICAL DOCUMENT ANALYSIS FRAMEWORK:

1. Initial Document Assessment:
   {_format_section(INITIAL_DOCUMENT_ASSESSMENT)}

2. Structural Mapping:
   {_format_section(STRUCTURAL_MAPPING)}

3. Synthetic TOC Generation:
   {_format_section(SYNTHETIC_TOC_GENERATION)}

4. Terminology and Acronym Extraction:
   {_format_section(TERMINOLOGY_EXTRACTION)}

5. Content-Type Specific Extraction:
   {_format_section(CONTENT_TYPE_EXTRACTION)}

6. Contextual Analysis:
   {_format_section(CONTEXTUAL_ANALYSIS)}

7. Progressive Refinement:
   {_format_section(PROGRESSIVE_REFINEMENT)}
"""

# Complete Tool Selection Workflow
TOOL_SELECTION_WORKFLOW = f"""
DOCUMENT ANALYSIS TOOL SELECTION WORKFLOW:

1. Document Structure Analysis:
   {_format_section(DOCUMENT_STRUCTURE_ANALYSIS)}

2. Content Location:
   {_format_section(CONTENT_LOCATION)}

3. Targeted Content Extraction:
   {_format_section(TARGETED_CONTENT_EXTRACTION)}

4. Special Content Handling:
   {_format_section(SPECIAL_CONTENT_HANDLING)}
"""

# Complete Performance Optimization Guidance
PERFORMANCE_OPTIMIZATION_GUIDANCE = f"""
PERFORMANCE OPTIMIZATION STRATEGIES:

1. Chunking Strategies:
   {_format_section(CHUNKING_STRATEGIES)}

2. Efficient Retrieval:
   {_format_section(EFFICIENT_RETRIEVAL)}

3. Context Management:
   {_format_section(CONTEXT_MANAGEMENT)}

4. Resource Conservation:
   {_format_section(RESOURCE_CONSERVATION)}
"""

# Complete Image Analysis Guidance
IMAGE_ANALYSIS_GUIDANCE = f"""
IMAGE ANALYSIS GUIDANCE:

1. Image Identification:
   {_format_section(IMAGE_IDENTIFICATION)}

2. Contextual Extraction:
   {_format_section(IMAGE_CONTEXTUAL_EXTRACTION)}

3. Efficient Image Handling:
   {_format_section(EFFICIENT_IMAGE_HANDLING)}

4. Content-Type Specific Analysis:
   {_format_section(IMAGE_CONTENT_ANALYSIS)}
"""

# Advanced Guidance - Comprehensive summary
ADVANCED_DOCUMENT_ANALYSIS_GUIDANCE = f"""
{ALTERNATIVE_APPROACHES}

{SAMPLING_APPROACH_ISSUES}

{APPROACH_SELECTION_CRITERIA}
"""

# Combined Guidance
COMBINED_GUIDANCE = """
COMPREHENSIVE DOCUMENT ANALYSIS GUIDANCE

This guidance merges the hierarchical framework with advanced strategies and implementation details.

HIERARCHICAL DOCUMENT ANALYSIS FRAMEWORK:
1. Initial Document Assessment
2. Structural Mapping 
3. Synthetic TOC Generation
4. Terminology and Acronym Extraction
5. Content-Type Specific Extraction
6. Contextual Analysis
7. Progressive Refinement

TOOL SELECTION WORKFLOW:
1. Document Structure Analysis
2. Content Location
3. Targeted Content Extraction
4. Special Content Handling

PERFORMANCE OPTIMIZATION STRATEGIES:
1. Chunking Strategies
2. Efficient Retrieval
3. Context Management
4. Resource Conservation

IMAGE ANALYSIS GUIDANCE:
1. Image Identification
2. Contextual Extraction
3. Efficient Image Handling
4. Content-Type Specific Analysis

ADVANCED ANALYSIS APPROACHES:
1. Structural-Based Extraction
2. Content-Driven Adaptive Sampling
3. Query-Guided Extraction
4. Layered Progressive Analysis
5. Hybrid Visual-Textual Analysis
6. Full Sequential Processing

For implementation details of these advanced strategies, see IMPLEMENTATION_STRATEGIES.
Periodic sampling approaches (every Nth page) should be avoided due to significant limitations.
Choose the most appropriate approach based on document characteristics and analysis requirements.
"""
