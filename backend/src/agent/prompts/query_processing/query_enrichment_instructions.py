"""Query enrichment instructions prompt"""

QUERY_ENRICHMENT_PROMPT = """
        I want to buy something. Agent are gonna search step by step for it.
        For that reason about this extra information.

        Relevant search time: If very high tech, fast evolving field or AI based then last year is relevant, for stable stuff like dumbbells, leave empty "".

        Sources hint: Where do nerdy users of this product hang out? Reddit for apps, country-specific price comparison platforms like Geizhals, Hacker News for niche tech, Amazon for simple retail, and the best local source you can think of.

        How many products to show: When product is undifferentiated and depend highly on taste show 10, like shoes. If product is niche and really differentiated show 3, like e-reading device.

        Use cases and customer segments list: One product category serves many customer segments and many use cases, if not completely clear by user query list possible segments max 4 so the user can choose.

        offer usecases only if you think is really unclear and customer segments need different options. Do not be unreasonable/annoying in your suggestions. only if it helps the search significantly. 

        Example query "best noise cancelling device"
        Relevant search time: 2 years
        Sources hint: reddit, wired, youtube,
        how many products to show: 4
        use cases and customer segments list: [Travelers, Office worker, Sleep aid, Factory Workers]

        Example query "Dumbbells for strength training at home under 100 euros up to 4 kilo"
        Relevant search time: None
        sources hint: amazon
        how many products to show: 6
        use cases and customer segments list: None

        what i want to buy is: {user_query}
    """