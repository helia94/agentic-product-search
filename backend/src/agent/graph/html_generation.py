import os
import json
from datetime import datetime
from langchain_core.runnables import RunnableConfig

from agent.graph.state_V2 import OverallState
from agent.configuration.llm_setup import get_llm
from agent.graph.html_generation_prompt import HTML_GENERATION_PROMPT


def generate_html_results(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Generate HTML output from completed products using LLM.
    This node takes the completed_products and creates a beautiful HTML page.
    """
    try:
        # Get the completed products and other relevant data
        completed_products = state.get("completed_products", [])
        
        if not completed_products:
            print("⚠️ No completed products found, skipping HTML generation")
            return {"html_generated": False, "html_file_path": None}
        
        print(f"🎨 Generating HTML for {len(completed_products)} products...")
        
        # Prepare the data for the prompt
        products_json = json.dumps(completed_products, indent=2, default=str)
        
        # Format the prompt with the actual data
        input_prompt = """
            ## Input Data:
            Completed Products: {completed_products}
            """
        formatted_prompt = HTML_GENERATION_PROMPT + input_prompt.format(
            completed_products=products_json
        )
        
        # Generate HTML using the LLM
        print("🤖 Calling LLM to generate HTML...")
        html_response = get_llm("html_generation").invoke(formatted_prompt)
        html_content = html_response.content if hasattr(html_response, 'content') else str(html_response)
        
        # Clean up the HTML content (remove any markdown formatting if present)
        if html_content.startswith("```html"):
            html_content = html_content.replace("```html", "").replace("```", "").strip()
        elif html_content.startswith("```"):
            html_content = html_content.replace("```", "").strip()
        
        # Ensure the HTML starts with proper doctype if not present
        if not html_content.strip().lower().startswith("<!doctype"):
            if not html_content.strip().lower().startswith("<html"):
                html_content = f"<!DOCTYPE html>\n<html lang='en'>\n{html_content}\n</html>"
            else:
                html_content = f"<!DOCTYPE html>\n{html_content}"
        
        # Create results directory if it doesn't exist
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_filename = f"{results_dir}/product_results_{timestamp}.html"
        
        # Save HTML to file
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML generated successfully: {html_filename}")
        print(f"📄 HTML file size: {len(html_content)} characters")
        
        # Return updated state
        return {
            "html_generated": True,
            "html_file_path": html_filename,
            "html_content": html_content
        }
        
    except Exception as e:
        error_message = f"Error generating HTML: {str(e)}"
        print(f"❌ {error_message}")
        
        return {
            "html_generated": False,
            "html_file_path": None,
            "html_error": error_message
        }