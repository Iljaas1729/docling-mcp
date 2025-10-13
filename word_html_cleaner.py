"""
Word HTML Cleaner - Enhanced with Smart Table Detection
========================================================

Built on concepts from HtmlRAG (WWW 2025, MIT License)
Source: https://github.com/plageon/HtmlRAG
Paper: "HtmlRAG: HTML is Better Than Plain Text for Modeling Retrieval Results in RAG Systems"

Core concepts from HtmlRAG:
- In-place DOM operations (preserves document order)
- Iterative empty tag removal
- Basic cleaning (scripts, styles, comments)

Our enhancements for Word HTML:
- Smart wrapper table detection and removal
- Data table preservation with semantic structure
- Word export pattern recognition
- Generic heuristics for all Word versions

MIT License
"""

import re
from bs4 import BeautifulSoup, Comment
from typing import Optional


def concat_text(text: str) -> str:
    """Helper function to normalize text by removing whitespace (from HtmlRAG)"""
    text = "".join(text.split("\n"))
    text = "".join(text.split("\t"))
    text = "".join(text.split(" "))
    return text


def is_wrapper_table(table) -> bool:
    """
    Detect if a table is a layout wrapper vs actual data table.
    
    Word HTML exports use tables for page layout. This function distinguishes:
    - Wrapper tables: Used for layout, should be removed
    - Data tables: Contain actual tabular data, should be preserved
    
    Args:
        table: BeautifulSoup table element
        
    Returns:
        True if table is a wrapper (should be removed), False if data table (keep)
    """
    # Get rows
    rows = table.find_all('tr', recursive=False)
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr', recursive=False)
    
    # Heuristic 1: No rows = wrapper
    if len(rows) == 0:
        return True
    
    # Heuristic 2: Single row with single cell (classic Word layout wrapper)
    if len(rows) == 1:
        cells = rows[0].find_all(['td', 'th'], recursive=False)
        if len(cells) <= 1:
            return True
    
    # Heuristic 3: Check if every cell contains a nested table (pure layout)
    cells = table.find_all(['td', 'th'], recursive=False)
    if len(cells) > 0:
        nested_tables = [cell.find('table') for cell in cells]
        if all(nested_tables):
            # Every cell has a table = this is a layout container
            return True
    
    # Heuristic 4: Very few cells without data patterns
    total_cells = sum(len(row.find_all(['td', 'th'], recursive=False)) 
                     for row in rows)
    if total_cells < 4:
        if not contains_tabular_data_pattern(table):
            return True
    
    # Default: Keep the table (data table)
    return False


def contains_tabular_data_pattern(table) -> bool:
    """
    Detect if table contains actual data vs just layout.
    
    Uses multiple heuristics to identify data tables:
    - Multiple numbers (prices, quantities, IDs)
    - Date/time patterns
    - Consistent row structure
    - Header cells
    
    Args:
        table: BeautifulSoup table element
        
    Returns:
        True if table contains data patterns
    """
    text = table.get_text()
    
    # Pattern 1: Multiple numbers (financial data, IDs, quantities)
    numbers = re.findall(r'\d+[.,]\d+|\d{3,}', text)
    if len(numbers) > 5:
        return True
    
    # Pattern 2: Date/time patterns
    if re.search(r'\d{1,2}[:/]\d{1,2}[:/]\d{2,4}', text) or \
       re.search(r'\d{1,2}:\d{2}:\d{2}', text) or \
       re.search(r'(AM|PM)', text):
        return True
    
    # Pattern 3: Consistent row structure (repeating data)
    rows = table.find_all('tr', recursive=False)
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr', recursive=False)
    
    if len(rows) >= 3:
        cell_counts = [len(row.find_all(['td', 'th'], recursive=False)) 
                       for row in rows]
        # Consistent cell counts = structured data
        if len(set(cell_counts)) <= 2 and max(cell_counts) >= 2:
            return True
    
    # Pattern 4: Headers (th tags or semantic indicators)
    if table.find('th'):
        return True
    
    return False


def get_table_depth(table) -> int:
    """Calculate nesting depth of a table (how many parent elements)"""
    depth = 0
    parent = table.parent
    while parent:
        depth += 1
        parent = parent.parent
    return depth


def clean_word_html(html_content: str, keep_attr: bool = True) -> str:
    """
    Clean Word-exported HTML while preserving semantic structure.
    
    Combines HtmlRAG's in-place operations with smart table detection:
    1. Removes scripts, styles, comments (HtmlRAG)
    2. Unwraps layout wrapper tables (our enhancement)
    3. Preserves data tables (our enhancement)
    4. Removes redundant wrappers (HtmlRAG)
    5. Removes empty tags except table structure (modified from HtmlRAG)
    
    Args:
        html_content: Raw HTML string
        keep_attr: Whether to preserve HTML attributes (default: True for semantics)
        
    Returns:
        Cleaned HTML string with:
        - Preserved document order (in-place operations)
        - Removed layout tables
        - Preserved data tables
        - Reduced file size
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Step 1: Remove scripts and styles (from HtmlRAG)
    for script in soup(['script', 'style', 'meta', 'link']):
        script.decompose()
    
    # Step 2: Remove comments (from HtmlRAG)
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()
    
    # Step 3: Smart table unwrapping (our enhancement)
    # Process from deepest to shallowest to avoid conflicts
    tables = soup.find_all('table')
    tables_with_depth = [(table, get_table_depth(table)) for table in tables]
    tables_with_depth.sort(key=lambda x: x[1], reverse=True)
    
    wrapper_tables_removed = 0
    for table, depth in tables_with_depth:
        if is_wrapper_table(table):
            # This is a layout wrapper - unwrap it AND its tbody/thead
            # First unwrap any tbody/thead inside this table
            for tbody in table.find_all(['tbody', 'thead'], recursive=False):
                tbody.unwrap()
            # Then unwrap the table itself
            table.unwrap()
            wrapper_tables_removed += 1
    
    # Step 4: Remove href attributes (from HtmlRAG - security/privacy)
    for tag in soup.find_all("a"):
        if "href" in tag.attrs:
            del tag["href"]
    
    # Step 5: Clean attributes if requested
    if not keep_attr:
        for tag in soup.find_all(True):
            # Keep semantic attributes even if keep_attr=False
            attrs_to_keep = {}
            if 'colspan' in tag.attrs:
                attrs_to_keep['colspan'] = tag.attrs['colspan']
            if 'rowspan' in tag.attrs:
                attrs_to_keep['rowspan'] = tag.attrs['rowspan']
            
            tag.attrs = attrs_to_keep
    
    # Step 6: Remove redundant single-child wrappers (from HtmlRAG, modified)
    for tag in soup.find_all():
        # Skip table structure
        if tag.name in ['table', 'tbody', 'thead', 'tr', 'td', 'th']:
            continue
            
        children = [child for child in tag.contents if not isinstance(child, str)]
        if len(children) == 1:
            tag_text = tag.get_text()
            child_text = ''.join([child.get_text() for child in tag.contents 
                                  if not isinstance(child, str)])
            if concat_text(child_text) == concat_text(tag_text):
                tag.replace_with_children()
    
    # Step 7: Remove empty tags EXCEPT table structure (modified from HtmlRAG)
    while True:
        removed = False
        for tag in soup.find_all():
            # PRESERVE table structure tags even if empty
            if tag.name in ['table', 'tbody', 'thead', 'tr', 'td', 'th']:
                continue
            
            # Remove other empty tags
            if not tag.text.strip():
                tag.decompose()
                removed = True
        if not removed:
            break
    
    # Step 8: Clean XML declarations (from HtmlRAG)
    html = str(soup)
    html = re.sub(r"<\?xml.*?>", "", html)
    html = re.sub(r"<!DOCTYPE.*?>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<!doctype.*?>", "", html, flags=re.IGNORECASE)
    
    # Step 9: Remove empty lines (from HtmlRAG)
    lines = [line for line in html.split("\n") if line.strip()]
    html = "\n".join(lines)
    
    return html, wrapper_tables_removed


def analyze_cleaning(original_html: str, cleaned_html: str) -> dict:
    """
    Analyze the cleaning results.
    
    Returns:
        Dictionary with statistics and validation results
    """
    orig_soup = BeautifulSoup(original_html, 'html.parser')
    clean_soup = BeautifulSoup(cleaned_html, 'html.parser')
    
    orig_tables = orig_soup.find_all('table')
    clean_tables = clean_soup.find_all('table')
    
    return {
        'original_size': len(original_html),
        'cleaned_size': len(cleaned_html),
        'reduction_percent': ((len(original_html) - len(cleaned_html)) / len(original_html)) * 100,
        'original_tables': len(orig_tables),
        'cleaned_tables': len(clean_tables),
        'tables_removed': len(orig_tables) - len(clean_tables),
        'max_nesting_depth': max([get_table_nesting_depth(t) for t in clean_tables]) if clean_tables else 0
    }


def get_table_nesting_depth(table) -> int:
    """Count how many parent tables this table has"""
    depth = 0
    parent = table.parent
    while parent:
        if parent.name == 'table':
            depth += 1
        parent = parent.parent
    return depth
