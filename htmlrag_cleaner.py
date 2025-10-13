"""
HTML Cleaning Functions from HtmlRAG
Source: https://github.com/plageon/HtmlRAG
License: MIT License
Paper: "HtmlRAG: HTML is Better Than Plain Text for Modeling Retrieval Results in RAG Systems" (WWW 2025)

Extracted and adapted for standalone use.
"""

import re
from bs4 import BeautifulSoup, Comment


def concat_text(text):
    """Helper function to normalize text by removing whitespace."""
    text = "".join(text.split("\n"))
    text = "".join(text.split("\t"))
    text = "".join(text.split(" "))
    return text


def simplify_html(soup, keep_attr=False):
    """
    Simplify HTML by removing unnecessary elements and attributes.
    Works IN-PLACE on the soup object.
    
    Args:
        soup: BeautifulSoup object
        keep_attr: Whether to keep HTML attributes (default: False)
    
    Returns:
        Cleaned HTML string
    """
    # Remove scripts and styles
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Remove all attributes if requested
    if not keep_attr:
        for tag in soup.find_all(True):
            tag.attrs = {}
    
    # Remove empty tags recursively
    while True:
        removed = False
        for tag in soup.find_all():
            if not tag.text.strip():
                tag.decompose()
                removed = True
        if not removed:
            break
    
    # Remove href attributes
    for tag in soup.find_all("a"):
        if "href" in tag.attrs:
            del tag["href"]
    
    # Remove comments
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()

    # Remove redundant wrapper tags (tags with single child that has same text)
    for tag in soup.find_all():
        children = [child for child in tag.contents if not isinstance(child, str)]
        if len(children) == 1:
            tag_text = tag.get_text()
            child_text = ''.join([child.get_text() for child in tag.contents if not isinstance(child, str)])
            if concat_text(child_text) == concat_text(tag_text):
                tag.replace_with_children()
    
    # Convert to string and remove empty lines
    res = str(soup)
    lines = [line for line in res.split("\n") if line.strip()]
    res = "\n".join(lines)
    return res


def clean_xml(html):
    """Remove XML declarations and DOCTYPE declarations."""
    html = re.sub(r"<\?xml.*?>", "", html)
    html = re.sub(r"<!DOCTYPE.*?>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<!doctype.*?>", "", html, flags=re.IGNORECASE)
    return html


def clean_html(html_content, keep_attr=False):
    """
    Main cleaning function that combines all cleaning steps.
    
    Args:
        html_content: Raw HTML string
        keep_attr: Whether to keep HTML attributes
    
    Returns:
        Cleaned HTML string
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    html = simplify_html(soup, keep_attr=keep_attr)
    html = clean_xml(html)
    return html
