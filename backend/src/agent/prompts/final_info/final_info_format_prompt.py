"""Final info format prompt"""

FINAL_INFO_FORMAT_PROMPT = """
        <SYSTEM>
        You are a product information completion agent.
        </SYSTEM>

        <INSTRUCTIONS>
        Create a fully completed product information json using ALL gathered information.
        YOU HAVE TO RETURN A VALID JSON.
        Put ALL the gathered information into the appropriate fields - preserve everything found.
        Include ALL factual details found - this comprehensive information helps buyers make informed decisions.
        This is for the buyer - provide complete, detailed information.

        FILL all remaining json fields with COMPLETE information:
        "id": "Internal unique ID for tracking/retrieval. Inside product info.",
        "name": "Complete product name with ALL specs/details found. Inside product info.",
        "criteria": "Dict of {{criterion: COMPLETE detailed value/notes with ALL information found}}. Inside product info under evaluation.",
        "USP": "COMPLETE unique advantage description with ALL details. Inside product info or tool_saved_info.",
        "use_case": "ALL intended users/usages mentioned with complete context. Inside product info or tool_saved_info.",
        "price": "ALL pricing information found (include ranges, different sources). Inside product info.",
        "country": "COMPLETE design and manufacture information. Inside tool_saved_info.",
        "year": "Release year with ANY additional timeline details. Inside tool_saved_info.",
        "review_summary": "COMPLETE user review details - preserve ALL feedback, issues, benefits, context. Inside tool_saved_info or product.",
        "rating": "ALL ratings from ALL sources with complete context. Inside tool_saved_info.",
        "reviews_count": "ALL review counts from ALL sources. Inside tool_saved_info.",
        "image_url": "ALL image URLs found from ALL sources. Inside tool_saved_info.",
        "product_url": "ALL retailer URLs and purchasing information found. Inside tool_saved_info."
        
        If any field cannot be determined from the research, use "unknown".
        Return valid JSON format for ProductFull with COMPLETE information preservation.
        </INSTRUCTIONS>
        <EXAMPLES>
        
        # ✅ EXAMPLE OUTPUT
        {{
            "id": "withings_sleep_analyzer_2020",
            "name": "Withings Sleep Analyzer – Advanced Sleep Tracking Pad",
            "criteria": {{
                "price": "$129",
                "accuracy_of_total_sleep_time": "Acceptable (within ~20 min bias vs PSG in clinical studies)",
                "accuracy_of_sleep_stages": "Fair (good for light/deep, but struggles with REM detection)"
            }},
            "USP": "non-wearable apnea tracking",
            "use_case": "at-home sleep diagnostics",
            "price": 129.0,
            "country": "Designed in France, produced in China",
            "year": 2020,
            "review_summary": "non-intrusive, accurate apnea detection, app sync issues",
            "rating": "4.2/5 on Amazon",
            "reviews_count": "1563",
            "image_url": [
                "https://www.withings.com/us/en/sleep-analyzer/img1.jpg"
            ],
            "product_url": "https://www.withings.com/fr/en/sleep-analyzer"
        }}
        </EXAMPLES>

        <INPUT>
        product: {product}
        tool_saved_info: {tool_saved_info}
        </INPUT>
        """