from typing import Any, Dict, List
import re


def resolve_urls(urls_to_resolve: List[Any], id: int) -> Dict[str, str]:
    """
    Create a map that preserves the original URLs instead of replacing them with fake internal IDs.
    This ensures citations point to real, accessible web sources.
    """
    # Extract real URLs from the search results
    urls = [site.web.uri for site in urls_to_resolve]

    # Create a dictionary that maps each unique URL to itself (preserve original URLs)
    # We only need to deduplicate, not create fake internal URLs
    resolved_map = {}
    for idx, url in enumerate(urls):
        if url not in resolved_map:
            # Keep the original URL instead of creating a fake vertexaisearch URL
            resolved_map[url] = url

    return resolved_map


def insert_citation_markers(text, citations_list):
    """
    Inserts citation markers into a text string based on start and end indices.

    Args:
        text (str): The original text string.
        citations_list (list): A list of dictionaries, where each dictionary
                               contains 'start_index', 'end_index', and
                               'segment_string' (the marker to insert).
                               Indices are assumed to be for the original text.

    Returns:
        str: The text with citation markers inserted.
    """
    # Sort citations by end_index in descending order.
    # If end_index is the same, secondary sort by start_index descending.
    # This ensures that insertions at the end of the string don't affect
    # the indices of earlier parts of the string that still need to be processed.
    sorted_citations = sorted(
        citations_list, key=lambda c: (c["end_index"], c["start_index"]), reverse=True
    )

    modified_text = text
    for citation_info in sorted_citations:
        # These indices refer to positions in the *original* text,
        # but since we iterate from the end, they remain valid for insertion
        # relative to the parts of the string already processed.
        end_idx = citation_info["end_index"]
        marker_to_insert = ""
        for segment in citation_info["segments"]:
            marker_to_insert += f" [{segment['label']}]({segment['short_url']})"
        # Insert the citation marker at the original end_idx position
        modified_text = (
            modified_text[:end_idx] + marker_to_insert + modified_text[end_idx:]
        )

    return modified_text


def get_citations(response, resolved_urls_map):
    """
    Extracts and formats citation information from a Gemini model's response.

    This function processes the grounding metadata provided in the response to
    construct a list of citation objects. Each citation object includes the
    start and end indices of the text segment it refers to, and a string
    containing formatted markdown links to the supporting web chunks.

    Args:
        response: The response object from the Gemini model, expected to have
                  a structure including `candidates[0].grounding_metadata`.
                  It also relies on a `resolved_map` being available in its
                  scope to map chunk URIs to resolved URLs.

    Returns:
        list: A list of dictionaries, where each dictionary represents a citation
              and has the following keys:
              - "start_index" (int): The starting character index of the cited
                                     segment in the original text. Defaults to 0
                                     if not specified.
              - "end_index" (int): The character index immediately after the
                                   end of the cited segment (exclusive).
              - "segments" (list[str]): A list of individual markdown-formatted
                                        links for each grounding chunk.
              - "segment_string" (str): A concatenated string of all markdown-
                                        formatted links for the citation.
              Returns an empty list if no valid candidates or grounding supports
              are found, or if essential data is missing.
    """
    citations = []

    # Ensure response and necessary nested structures are present
    if not response or not response.candidates:
        return citations

    candidate = response.candidates[0]
    if (
        not hasattr(candidate, "grounding_metadata")
        or not candidate.grounding_metadata
        or not hasattr(candidate.grounding_metadata, "grounding_supports")
    ):
        return citations

    for support in candidate.grounding_metadata.grounding_supports:
        citation = {}

        # Ensure segment information is present
        if not hasattr(support, "segment") or support.segment is None:
            continue  # Skip this support if segment info is missing

        start_index = (
            support.segment.start_index
            if support.segment.start_index is not None
            else 0
        )

        # Ensure end_index is present to form a valid segment
        if support.segment.end_index is None:
            continue  # Skip if end_index is missing, as it's crucial

        # Add 1 to end_index to make it an exclusive end for slicing/range purposes
        # (assuming the API provides an inclusive end_index)
        citation["start_index"] = start_index
        citation["end_index"] = support.segment.end_index

        citation["segments"] = []
        if (
            hasattr(support, "grounding_chunk_indices")
            and support.grounding_chunk_indices
        ):
            for ind in support.grounding_chunk_indices:
                try:
                    chunk = candidate.grounding_metadata.grounding_chunks[ind]
                    resolved_url = resolved_urls_map.get(chunk.web.uri, None)
                    citation["segments"].append(
                        {
                            "label": chunk.web.title.split(".")[:-1][0],
                            "short_url": resolved_url,
                            "value": chunk.web.uri,
                        }
                    )
                except (IndexError, AttributeError, NameError):
                    # Handle cases where chunk, web, uri, or resolved_map might be problematic
                    # For simplicity, we'll just skip adding this particular segment link
                    # In a production system, you might want to log this.
                    pass
        citations.append(citation)
    return citations


def build_source_mapping(sources_gathered):
    """Build source file mapping for citation conversion"""
    mapping = {}
    for i, source in enumerate(sources_gathered):
        # Extract domain from URL for readable citation
        original_url = source.get("value", "")
        domain = extract_domain(original_url)
        label = source.get("label", domain)
        
        # Create mapping for different citation formats
        short_url = source.get("short_url", "")
        if short_url:
            # Extract ID from short URL
            id_match = re.search(r'/id/([^/]+)', short_url)
            if id_match:
                citation_id = id_match.group(1)
                mapping[citation_id] = {
                    "label": label,
                    "domain": domain,
                    "value": original_url if original_url and not original_url.startswith('https://vertexaisearch') else ""
                }
        
        # Also try direct URL mapping if available
        if original_url and not original_url.startswith('https://vertexaisearch'):
            # Create a simple mapping using domain as key
            domain_key = domain.lower().replace(' ', '')
            mapping[domain_key] = {
                "label": label,
                "domain": domain,  
                "value": original_url
            }
    
    return mapping


def extract_domain(url):
    """Extract domain from URL"""
    if not url:
        return "Unknown"
    
    # Extract domain from URL
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if domain_match:
        domain = domain_match.group(1)
        # Simplify common domains
        if "google.com" in domain:
            return "Google"
        elif "wikipedia" in domain:
            return "Wikipedia" 
        elif "youtube" in domain:
            return "YouTube"
        else:
            return domain.split('.')[0].title()
    return "Web Source"


def convert_citations_to_readable(content, source_mapping):
    """Convert raw citation markers to readable, verifiable citation formats with complete source information"""
    
    def replace_citation(match):
        citation_id = match.group(1)
        if citation_id in source_mapping:
            source_info = source_mapping[citation_id]
            # Create comprehensive citation with verifiable information
            domain = source_info.get('domain', 'Unknown Source')
            url = source_info.get('value', '')
            label = source_info.get('label', domain)
            
            # Format: [Source: Domain (URL)] for verifiability
            if url and url.startswith('http') and 'vertexaisearch.cloud.google.com' not in url:
                return f"[Source: {label} ({url})]"
            else:
                return f"[Source: {label}]"
        return f"[Source: {citation_id}]"  # Fallback with original ID
    
    # Convert Vertex AI citations with full source information
    content = re.sub(r'\[vertexaisearch\.cloud\.google\.com/id/([^\]]+)\]', 
                     replace_citation, content)
    
    # Convert other citation formats while preserving source identification
    content = re.sub(r'\[([a-z0-9\-]+)\]', replace_citation, content)
    
    # Clean up any remaining malformed citations
    content = clean_malformed_citations(content)
    
    return content


def clean_malformed_citations(content):
    """Clean up malformed citation formats in content"""
    
    # Fix mixed citation formats like [Source: domain](https://vertexaisearch...)
    content = re.sub(r'\[Source: ([^\]]+)\]\(https://vertexaisearch\.cloud\.google\.com[^)]*\)', 
                     r'[Source: \1]', content)
    
    # Remove any remaining vertexaisearch URLs that shouldn't be there
    content = re.sub(r'\(https://vertexaisearch\.cloud\.google\.com[^)]*\)', '', content)
    
    # Fix double closing brackets
    content = re.sub(r'\]\]', ']', content)
    
    return content