"""Final info analyze prompt"""

FINAL_INFO_ANALYZE_PROMPT = """
        <SYSTEM>
        You are a product information completion agent. Analyze the last search result to extract missing ProductFull fields.
        </SYSTEM>

        <INSTRUCTIONS>
        Extract ALL product information from the search results:
        "USP": "Complete unique selling proposition with all details and context found.",
        "use_case": "ALL contexts and user segments mentioned with complete details.",
        "country": "Complete design and manufacturing information found.",
        "year": "Release year with any additional timeline information found.",
        "review_summary": "ALL user review details found - preserve complete feedback, specific issues, positive points, context.",
        "rating": "ALL rating information found from all sources with complete context.",
        "reviews_count": "ALL review count information from all sources.",
        "image_url": "ALL image URLs found, preserve all sources.",
        "product_url": "ALL retailer links and purchasing information found."
        ANY other information found - preserve everything.

        Preserve ALL factual data found, maintain complete context and details.
        Return comprehensive insights preserving ALL information as complete detailed strings.
        </INSTRUCTIONS>

        <INPUT>
        product: {product}
        last_tool_call_arguments: {last_tool_call_arguments}
        last_tool_call_output: {last_tool_call_output}
        </INPUT>
        """