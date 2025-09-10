"""
Simple retry utilities for LLM tool calls.
One class that breaks down the nested retry logic into clean, readable methods.
"""
import logging
import time
from typing import Any, Optional


class LLMRetryHandler:
    """Handles retry logic for LLM tool calls."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _is_validation_error(self, error_message: str) -> bool:
        """Check if error is a tool validation error."""
        error_msg = error_message.lower()
        validation_keywords = [
            'tool call validation failed',
            'parameters for tool',
            'did not match schema', 
            'expected boolean, but got string',
            'badrequest'
        ]
        return any(keyword in error_msg for keyword in validation_keywords)

    def _modify_prompt_for_retry(self, original_prompt: str, attempt: int) -> str:
        """Modify prompt based on retry attempt number."""
        if attempt == 0:
            # First retry: Add parameter type instructions
            return original_prompt + """\n\nIMPORTANT: When calling tools:
            - Use boolean values (true/false), NOT strings ("true"/"false")
            - Only use valid tool parameters
            - For TavilySearch: valid boolean params are include_answer, include_raw_content, include_images, include_image_descriptions
            - Example: {"query": "search term", "include_images": true}"""
        
        elif attempt == 1:
            # Second retry: Basic search only
            return f"""Based on this context, generate a simple web search query using only the 'query' parameter.
            
            Context: {original_prompt}

            Generate a Tavily search tool call with ONLY the query parameter. Example:
            {{"query": "your search term here"}}

            Do not use any other parameters like include_images, search_depth, etc."""
        
        return original_prompt

    def _wait_before_retry(self, attempt: int):
        """Wait with exponential backoff before retry."""
        if attempt > 0:
            sleep_time = 2 ** (attempt - 1)
            self.logger.info(f"Waiting {sleep_time}s before retry...")
            time.sleep(sleep_time)

    def retry_call(self, llm_with_tools: Any, formatted_prompt: str, max_retries: int = 3) -> Optional[Any]:
        """
        Clean retry wrapper for LLM tool calls that handles validation errors.
        """
        current_prompt = formatted_prompt
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"Attempting tool call (attempt {attempt + 1}/{max_retries + 1})")
                result = llm_with_tools.invoke(current_prompt)
                self.logger.info("Tool call succeeded")
                return result
                
            except Exception as e:
                if not self._is_validation_error(str(e)):
                    # Non-validation error - don't retry
                    if attempt >= max_retries:
                        self.logger.error(f"All retry attempts failed. Final error: {str(e)}")
                        return None
                    else:
                        self.logger.error(f"Non-validation error, not retrying: {str(e)}")
                        raise e
                
                # Validation error
                if attempt >= max_retries:
                    self.logger.error(f"All retry attempts failed. Final error: {str(e)}")
                    return None
                    
                self.logger.warning(f"Tool validation failed (attempt {attempt + 1}): {str(e)}")
                current_prompt = self._modify_prompt_for_retry(formatted_prompt, attempt)
                self._wait_before_retry(attempt)
        
        return None


# Keep same function interface for backwards compatibility
def retry_llm_tool_call(llm_with_tools: Any, formatted_prompt: str, max_retries: int = 3) -> Optional[Any]:
    """Same interface as original function."""
    handler = LLMRetryHandler()
    return handler.retry_call(llm_with_tools, formatted_prompt, max_retries)