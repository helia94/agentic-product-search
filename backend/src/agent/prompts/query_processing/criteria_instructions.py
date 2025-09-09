"""Criteria finding instructions prompt"""

CRITERIA_PROMPT = """
        Give me the main criteria that matter the most when buying {product} for {use_case}, sort them by impact and how differentiated the top products are on it. 
        My extra conditions are {conditions}. 
        Max 5 criteria. But only very critical ones, do not just make a list. 
        this is not school. you will be rewarded by critical  thinking and quality of judgement, not number of words, what would a no bullshit expert say to his friend as advice.
        intentionally decide how specific or general the criteria should be.

        Task: I want to buy headphones for daily remote work calls in shared spaces, and I have these conditions: must be wireless, work with Mac, not over-ear
        Output:
        "buying_criteria": ["mic clarity in noisy environments", "latency with MacOS apps", "fit comfort for 4h+ wear", "stable Bluetooth connection", "battery life with mic use"]


        Task: I want to buy smart ring for stress tracking, and I have these conditions: must be comfortable to wear at night and discreet
        Output:
        "buying_criteria": ["HRV tracking accuracy", "real-time stress alerts", "sleep data quality", "ring size comfort", "battery life in continuous mode"]

        4.
        Task: I want to buy app-based budgeting tool for freelancer income tracking, and I have these conditions: needs EU bank integration and VAT tagging
        Output:
        "buying_criteria": ["multi-bank syncing reliability", "income/expense tagging flexibility", "VAT & invoice support", "report exports for tax filing", "mobile UX for quick edits"]

        5.
        Task: I want to buy robot vacuum for pet hair removal, and I have these conditions: must avoid poop, work with dark floors, auto-empty optional
        Output:
        "buying_criteria": ["hair pickup efficiency on hard floors", "object recognition and poop-avoidance", "suction vs noise tradeoff", "carpet edge transitions", "maintenance hassle"]

        6.
        Task: I want to buy note-taking app for daily idea capture and link-based research, and I have these conditions: must work offline, exportable to markdown
        Output:
        "buying_criteria": ["speed of quick capture", "linking and backlink UX", "offline stability", "search relevance", "export structure quality"]

       
        the current task is for:
        I want to buy {product} for {use_case}, and I have these conditions: {conditions}.

        now give list of "buying_criteria": 
    """