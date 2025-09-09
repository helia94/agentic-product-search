from langchain_community.document_loaders import RedditPostsLoader

from langchain_community.tools.reddit_search.tool import RedditSearchRun
from langchain_community.utilities.reddit_search import RedditSearchAPIWrapper
from langchain_community.tools.reddit_search.tool import RedditSearchSchema

import os
from dotenv import load_dotenv  
load_dotenv()
client_id = os.getenv("REDDIT_CLIENT_ID")
client_secret = os.getenv("REDDIT_CLIENT_SECRET")
user_agent = os.getenv("REDDIT_USER_AGENT")

query = "mattress sensors for sleep tracking do they work?"



search = RedditSearchRun(
    api_wrapper=RedditSearchAPIWrapper(
        reddit_client_id=client_id,
        reddit_client_secret=client_secret,
        reddit_user_agent=user_agent,
    )
)


search_params = RedditSearchSchema(
    query=query, sort="new", time_filter="year", limit="2", subreddit="sleepnumber",
)

#result = search.run(tool_input=search_params.dict())
#print(result)