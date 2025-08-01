"""
Enhanced Graph nodes - integrated intelligent Firecrawl content enhancement functionality
"""

import os
import json
from typing import List, Dict, Any
from datetime import datetime
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage

from agent.state import OverallState, ReflectionState
from agent.content_enhancement_decision import (
    get_content_enhancement_decision_maker,
    EnhancementDecision
)
from agent.utils import get_research_topic


def content_enhancement_analysis(state: OverallState, config: RunnableConfig) -> dict:
    """
    Intelligent content enhancement analysis node - decide whether to use Firecrawl for deep scraping
    
    This node will:
    1. Analyze the quality of current research results
    2. Evaluate whether deep content enhancement is needed
    3. Select priority URLs for Firecrawl scraping
    4. Execute content enhancement (if needed)
    5. Merge enhanced content into research results
    """
    
    try:
        # Get current research context
        plan = state.get("plan", [])
        current_pointer = state.get("current_task_pointer", 0)
        
        # Determine research topic
        if plan and current_pointer < len(plan):
            research_topic = plan[current_pointer]["description"]
        else:
            research_topic = state.get("user_query") or get_research_topic(state["messages"])
        
        # Get current research findings
        current_findings = state.get("web_research_result", [])
        
        # Get grounding sources (extract from recent search results)
        grounding_sources = []
        sources_gathered = state.get("sources_gathered", [])
        for source in sources_gathered[-10:]:  # Latest 10 sources
            if isinstance(source, dict):
                grounding_sources.append({
                    "title": source.get("title", ""),
                    "url": source.get("url", ""),
                    "snippet": source.get("snippet", "")
                })
        
        print(f"🤔 Analyzing content enhancement requirements...")
        print(f"  Research topic: {research_topic}")
        print(f"  Current findings count: {len(current_findings)}")
        print(f"  Available information sources: {len(grounding_sources)}")
        
        # Use intelligent decision maker for analysis
        decision = get_content_enhancement_decision_maker().analyze_enhancement_need(
            research_topic=research_topic,
            current_findings=current_findings,
            grounding_sources=grounding_sources,
            config=config
        )
        
        print(f"📊 Enhancement decision results:")
        print(f"  Needs enhancement: {decision.needs_enhancement}")
        print(f"  Confidence: {decision.confidence_score:.2f}")
        print(f"  Enhancement type: {decision.enhancement_type}")
        print(f"  Priority URL count: {len(decision.priority_urls)}")
        
        # Save decision to state
        state_update = {
            "enhancement_decision": {
                "needs_enhancement": decision.needs_enhancement,
                "confidence_score": decision.confidence_score,
                "enhancement_type": decision.enhancement_type,
                "reasoning": decision.reasoning,
                "priority_urls": decision.priority_urls
            }
        }
        
        # If enhancement is not needed, return directly
        if not decision.needs_enhancement:
            print("✅ Current content quality is sufficient, no enhancement needed")
            state_update["enhancement_status"] = "skipped"
            return state_update
        
        # If no Firecrawl API Key, skip enhancement
        if not get_content_enhancement_decision_maker().firecrawl_app:
            print("⚠️ Missing FIRECRAWL_API_KEY, skipping content enhancement")
            state_update["enhancement_status"] = "skipped_no_api"
            return state_update
        
        # Execute content enhancement
        print(f"🔥 Executing Firecrawl content enhancement...")
        enhanced_results = []
        
        # Synchronous call (temporarily simplified, can be changed to async later)
        for url_info in decision.priority_urls:
            url = url_info.get("url")
            if not url:
                continue
            
            try:
                print(f"  Scraping: {url_info.get('title', 'Unknown')}")
                
                result = get_content_enhancement_decision_maker().firecrawl_app.scrape_url(url)
                
                if result and result.success:
                    markdown_content = result.markdown or ''
                    
                    enhanced_results.append({
                        "url": url,
                        "title": url_info.get("title", ""),
                        "original_priority": url_info.get("priority_score", 0),
                        "enhanced_content": markdown_content,
                        "content_length": len(markdown_content),
                        "source_type": "firecrawl_enhanced",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"    ✅ Success: {len(markdown_content)} characters")
                else:
                    print(f"    ❌ Failed: {result.error if hasattr(result, 'error') else 'Unknown error'}")
                    
            except Exception as e:
                print(f"    ❌ Exception: {str(e)}")
                continue
        
        if enhanced_results:
            # Add enhanced content to research results
            enhanced_contents = []
            for result in enhanced_results:
                # Format enhanced content
                formatted_content = f"""

## Deep Content Enhancement - {result['title']}

Source: {result['url']}
Content length: {result['content_length']} characters

{result['enhanced_content'][:3000]}{'...' if len(result['enhanced_content']) > 3000 else ''}

---
"""
                enhanced_contents.append(formatted_content)
            
            state_update.update({
                "enhanced_content_results": enhanced_results,
                "web_research_result": enhanced_contents,  # 添加到研究结果中
                "enhancement_status": "completed",
                "enhanced_sources_count": len(enhanced_results)
            })
            
            print(f"✅ 内容增强完成: {len(enhanced_results)} 个源")
        else:
            print("❌ 内容增强失败，没有成功抓取任何内容")
            state_update["enhancement_status"] = "failed"
        
        return state_update
        
    except Exception as e:
        error_message = f"内容增强分析节点异常: {str(e)}"
        print(f"❌ {error_message}")
        return {
            "enhancement_status": "error",
            "enhancement_error": error_message
        }


def should_enhance_content(state: OverallState) -> str:
    """
    条件边函数 - 决定是否进入内容增强流程
    
    基于以下条件判断:
    1. 是否配置了Firecrawl API Key
    2. 当前研究循环次数
    3. 用户配置的增强偏好
    """
    
    # 检查Firecrawl可用性
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("⚠️ 跳过内容增强: 未配置FIRECRAWL_API_KEY")
        return "continue_without_enhancement"
    
    # 检查研究循环次数（避免在早期循环中增强）
    research_loop_count = state.get("research_loop_count", 0)
    if research_loop_count < 1:  # 至少进行一轮研究后再考虑增强
        print(f"⚠️ 跳过内容增强: 研究循环次数不足 ({research_loop_count})")
        return "continue_without_enhancement"
    
    # 检查是否已经进行过增强（避免重复增强）
    if state.get("enhancement_status") in ["completed", "skipped"]:
        print("⚠️ 跳过内容增强: 已经完成增强")
        return "continue_without_enhancement"
    
    # 检查当前发现数量（至少要有一些基础内容）
    current_findings = state.get("web_research_result", [])
    if len(current_findings) < 1:
        print("⚠️ 跳过内容增强: 缺少基础研究内容")
        return "continue_without_enhancement"
    
    print("✅ 满足增强条件，进入内容增强分析")
    return "analyze_enhancement_need"


def enhanced_reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    """
    增强版反思节点 - 在原有reflection基础上考虑内容增强的结果
    """
    
    # 先调用原有的reflection逻辑
    from agent.graph import reflection
    reflection_result = reflection(state, config)
    
    # 如果进行了内容增强，调整reflection的判断
    enhancement_status = state.get("enhancement_status")
    enhanced_sources_count = state.get("enhanced_sources_count", 0)
    
    if enhancement_status == "completed" and enhanced_sources_count > 0:
        print(f"📈 内容增强完成，调整反思判断")
        print(f"  增强了 {enhanced_sources_count} 个信息源")
        
        # 如果成功增强了内容，更倾向于认为信息充足
        # 但仍然保留LLM的判断权重
        if not reflection_result["is_sufficient"]:
            # 给增强内容一定的"加分"
            enhancement_boost = min(enhanced_sources_count * 0.3, 0.8)
            print(f"  由于内容增强，提升充足性评估 (+{enhancement_boost:.1f})")
            
            # 如果增强效果很好，可能将"不充足"改为"充足"
            if enhancement_boost >= 0.6:
                print("  ✅ 基于内容增强结果，判定信息已充足")
                reflection_result["is_sufficient"] = True
                reflection_result["knowledge_gap"] = "内容已通过深度抓取得到充分补充"
    
    elif enhancement_status == "skipped":
        print("📝 内容增强被跳过，使用原始反思结果")
    
    elif enhancement_status == "failed":
        print("⚠️ 内容增强失败，可能需要更多研究循环")
    
    return reflection_result


# 辅助函数：格式化增强决策信息用于日志
def format_enhancement_decision_log(decision: EnhancementDecision) -> str:
    """格式化增强决策信息用于日志输出"""
    
    log_lines = [
        f"📊 内容增强决策报告:",
        f"  决策: {'需要增强' if decision.needs_enhancement else '无需增强'}",
        f"  置信度: {decision.confidence_score:.2f}",
        f"  增强类型: {decision.enhancement_type}",
        f"  优先URL数量: {len(decision.priority_urls)}"
    ]
    
    if decision.priority_urls:
        log_lines.append("  优先URLs:")
        for i, url_info in enumerate(decision.priority_urls, 1):
            log_lines.append(f"    {i}. {url_info.get('title', 'N/A')} (评分: {url_info.get('priority_score', 0):.2f})")
    
    log_lines.append(f"  推理: {decision.reasoning[:200]}...")
    
    return "\n".join(log_lines) 