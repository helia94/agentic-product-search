"""Final info conversion prompt"""

FINAL_INFO_CONVERSION_PROMPT = """
    Convert this product information into a properly structured ProductFull object.
    Ensure all fields are correctly typed and formatted.
    
    Product information to convert:
    {final_output}
    """