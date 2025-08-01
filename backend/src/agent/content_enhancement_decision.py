"""
Intelligent content enhancement decision module - decide when to use Firecrawl for deep content scraping
"""

import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableConfig
from firecrawl import FirecrawlApp

@dataclass
class EnhancementDecision:
    """Content enhancement decision result"""
    needs_enhancement: bool
    priority_urls: List[Dict[str, Any]]
    reasoning: str
    confidence_score: float  # 0-1
    enhancement_type: str  # "none", "selective", "comprehensive"


class ContentEnhancementDecisionMaker:
    """Intelligent content enhancement decision maker - similar to reflection mechanism"""
    
    def __init__(self):
        self.firecrawl_app = None
        if os.getenv("FIRECRAWL_API_KEY"):
            self.firecrawl_app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
    
    def analyze_enhancement_need(
        self, 
        research_topic: str,
        current_findings: List[str],
        grounding_sources: List[Dict[str, Any]],
        config: RunnableConfig
    ) -> EnhancementDecision:
        """
        Intelligently analyze whether content enhancement is needed - use LLM for judgment
        
        Similar to reflection mechanism, let LLM analyze current research quality and decide whether deep scraping is needed
        """
        
        # Build analysis prompt
        analysis_prompt = self._build_analysis_prompt(
            research_topic, current_findings, grounding_sources
        )
        
        # Use LLM for intelligent judgment
        from agent.configuration import Configuration
        configurable = Configuration.from_runnable_config(config)
        
        llm = ChatGoogleGenerativeAI(
            model=configurable.reflection_model,  # 使用和reflection相同的模型
            temperature=0.3,  # 低温度确保一致性
            max_retries=2,
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        
        response = llm.invoke(analysis_prompt)
        decision_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parse LLM's decision
        return self._parse_llm_decision(decision_text, grounding_sources)
    
    def _build_analysis_prompt(
        self, 
        research_topic: str, 
        current_findings: List[str], 
        grounding_sources: List[Dict[str, Any]]
    ) -> str:
        """Build analysis prompt"""
        
        findings_summary = "\n---\n".join(current_findings[-3:])  # Latest 3 results
        
        sources_list = "\n".join([
            f"- {source.get('title', 'N/A')}: {source.get('url', 'N/A')}"
            for source in grounding_sources[:5]  # First 5 sources
        ])
        
        return f"""You are a research quality assessment expert. Please analyze the quality of current research results and decide whether deep content enhancement is needed.

Research topic: {research_topic}

Current research findings:
{findings_summary}

Available information sources:
{sources_list}

Please evaluate based on the following criteria:

1. **Signals of insufficient content depth**:
   - Lack of specific data, statistical information, case studies
   - Descriptions too general, lacking technical details
   - No mention of important companies, projects, or implementation cases
   - Low quality information sources (non-authoritative websites)

2. **Situations requiring deep scraping**:
   - Research topic requires detailed technical explanations
   - Current results lack key data support
   - Authoritative information sources exist but content is truncated
   - Need to obtain complete reports or research content

3. **Evaluate the value of current information sources**:
   - Official websites/documents: High value
   - Academic papers/research reports: High value  
   - Wikipedia/encyclopedia: Medium value
   - News reports: Judge based on level of detail
   - Blogs/forums: Low value

Please answer in the following format:

**Decision**: [ENHANCE/NO_ENHANCE]
**Confidence**: [0.1-1.0]
**Enhancement type**: [selective/comprehensive/none]
**Recommended URL count**: [0-3]
**Reasoning process**: 
[Detailed explanation of your judgment reasons, including current content shortcomings and expected improvement effects]

**Priority URLs** (if enhancement needed):
[Select URLs from information sources that are most worthy of deep scraping, ranked by priority]
"""

    def _parse_llm_decision(
        self, 
        decision_text: str, 
        grounding_sources: List[Dict[str, Any]]
    ) -> EnhancementDecision:
        """Parse LLM decision results"""
        
        decision_text = decision_text.lower()
        
        # Parse basic decision
        needs_enhancement = "enhance" in decision_text and "no_enhance" not in decision_text
        
        # Parse confidence
        confidence_score = 0.5  # Default value
        import re
        confidence_match = re.search(r'confidence.*?([0-9]\.[0-9])', decision_text)
        if confidence_match:
            try:
                confidence_score = float(confidence_match.group(1))
            except:
                pass
        
        # Parse enhancement type
        enhancement_type = "none"
        if "selective" in decision_text:
            enhancement_type = "selective"
        elif "comprehensive" in decision_text:
            enhancement_type = "comprehensive"
        elif needs_enhancement:
            enhancement_type = "selective"  # Default selective enhancement
        
        # Select priority URLs (simplified version, can be improved to LLM selection later)
        priority_urls = []
        if needs_enhancement and grounding_sources:
            # Simple priority algorithm
            scored_sources = []
            for source in grounding_sources:
                score = self._calculate_url_priority(source)
                scored_sources.append((source, score))
            
            # Sort by score, select top 2-3
            scored_sources.sort(key=lambda x: x[1], reverse=True)
            max_urls = 3 if enhancement_type == "comprehensive" else 2
            
            priority_urls = [
                {
                    "title": source.get("title", ""),
                    "url": source.get("url", ""),
                    "priority_score": score,
                    "reasoning": f"Score: {score:.2f}"
                }
                for source, score in scored_sources[:max_urls]
                if score > 0.3  # Only select high-scoring ones
            ]
        
        return EnhancementDecision(
            needs_enhancement=needs_enhancement,
            priority_urls=priority_urls,
            reasoning=decision_text,
            confidence_score=confidence_score,
            enhancement_type=enhancement_type
        )
    
    def _calculate_url_priority(self, source: Dict[str, Any]) -> float:
        """Calculate priority score for URL"""
        score = 0.0
        
        url = source.get("url", "").lower()
        title = source.get("title", "").lower()
        
        # Official websites and documents
        if any(domain in url for domain in [".gov", ".edu", ".org"]):
            score += 0.4
        
        # Well-known platforms
        if any(platform in url for platform in ["wikipedia", "arxiv", "ieee", "acm"]):
            score += 0.3
        
        # Technical content indicators
        if any(keyword in title for keyword in ["report", "study", "research", "analysis", "technical"]):
            score += 0.2
        
        # Company official websites
        if any(company in url for company in ["google", "microsoft", "amazon", "tesla", "nvidia"]):
            score += 0.2
        
        # Base score
        score += 0.1
        
        return min(score, 1.0)
    
    async def enhance_content_with_firecrawl(
        self, 
        priority_urls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Use Firecrawl to enhance content"""
        
        if not self.firecrawl_app:
            return []
        
        enhanced_results = []
        
        for url_info in priority_urls:
            url = url_info.get("url")
            if not url:
                continue
            
            try:
                print(f"🔥 Firecrawl enhancement: {url_info.get('title', 'Unknown')}")
                
                result = self.firecrawl_app.scrape_url(url)
                
                if result and result.success:
                    markdown_content = result.markdown or ''
                    
                    enhanced_results.append({
                        "url": url,
                        "title": url_info.get("title", ""),
                        "original_priority": url_info.get("priority_score", 0),
                        "enhanced_content": markdown_content,
                        "content_length": len(markdown_content),
                        "enhancement_quality": self._assess_enhancement_quality(markdown_content),
                        "source_type": "firecrawl_enhanced"
                    })
                    
                    print(f"  ✅ Enhancement successful: {len(markdown_content)} characters")
                else:
                    print(f"  ❌ Enhancement failed: {result.error if hasattr(result, 'error') else 'Unknown error'}")
                    
            except Exception as e:
                print(f"  ❌ Enhancement exception: {str(e)}")
                continue
        
        return enhanced_results
    
    def _assess_enhancement_quality(self, content: str) -> str:
        """Assess the quality of enhanced content"""
        if not content:
            return "poor"
        
        length = len(content)
        has_data = any(char.isdigit() for char in content)
        has_structure = any(marker in content for marker in ['#', '##', '###'])
        
        if length > 5000 and has_data and has_structure:
            return "excellent"
        elif length > 1000 and (has_data or has_structure):
            return "good"
        elif length > 300:
            return "fair"
        else:
            return "poor"


# Delayed initialization function to avoid circular imports
def get_content_enhancement_decision_maker():
    """Get content enhancement decision maker instance (delayed initialization)"""
    if not hasattr(get_content_enhancement_decision_maker, '_instance'):
        get_content_enhancement_decision_maker._instance = ContentEnhancementDecisionMaker()
    return get_content_enhancement_decision_maker._instance

# For backward compatibility, keep original global variable name
content_enhancement_decision_maker = None  # Will be initialized on first use 