"""Query parser instructions prompt"""

QUERY_PARSER_PROMPT = """
    I want to buy: {user_query} 
    Agent are gonna search step by step for it. 
    For that break down the query to these parts. 
    The Product, Use case, Conditions, and finally other is any other specification or tips, but only informative info not blant stuff like find best .
    Example: "Dummbles for strength training at home under 100 euros"
    The Product: "Dummbles"
    Use case: "strength training at home"
    Conditions: ["under 100 euros"]
    other: ""
    """