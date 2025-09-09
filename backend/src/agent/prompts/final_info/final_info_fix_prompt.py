"""Final info fix prompt"""

FINAL_INFO_FIX_PROMPT = """
        The following text should be valid JSON but it's malformed. 
        Fix it to be valid JSON without changing the content meaning.
        Return only the fixed JSON, no explanations or markdown.
        
        Text to fix:
        {final_output}
        """