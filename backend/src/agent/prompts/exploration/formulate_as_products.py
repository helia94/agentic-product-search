FORMULATE_AS_PRODUCTS_PROMPT = """
    Extract and format the product list from this text into the required structure.
    PRESERVE ALL INFORMATION - do not summarize, shorten, or lose any details.
    Keep maximum {max_products} products based on relevance to query: {query}
    For each product, include ALL available information in the appropriate fields.
    ONLY Look for specific product models, DO NOT choose a product if it is just a category or brand. 
    Wrong example: Smartphone-based sEMG. 
    Correct example: Spren Body Composition Scanner - Pro ios app.  

    
    Text to process:
    {final_output}
    """