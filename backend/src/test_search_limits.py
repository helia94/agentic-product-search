#!/usr/bin/env python3
"""
Test script to verify search limits configuration is working correctly.
"""

import sys
import os

# Add the src directory to the path so we can import the agent modules
sys.path.append(os.path.join(os.path.dirname(__file__)))

from agent.search_limits import (
    SEARCH_LIMITS, 
    get_search_limit, 
    generate_search_prompt_text,
    is_search_limit_reached,
    ComponentNames,
    configure_search_limits_from_main_graph
)

def test_default_limits():
    """Test the default search limits"""
    print("🧪 Testing default search limits...")
    
    # Test default values
    assert get_search_limit(ComponentNames.PRODUCT_EXPLORATION) == 2
    assert get_search_limit(ComponentNames.PRODUCT_RESEARCH) == 3
    assert get_search_limit(ComponentNames.FINAL_PRODUCT_INFO) == 8
    
    print("✅ Default limits working correctly")

def test_loop_specific_limits():
    """Test loop-specific limits"""
    print("🧪 Testing loop-specific limits...")
    
    # Configure loop-specific limits
    configure_search_limits_from_main_graph(
        loop_limits={
            ComponentNames.PRODUCT_RESEARCH: {
                1: 2,
                2: 4,
                3: 1
            }
        }
    )
    
    # Test loop-specific values
    assert get_search_limit(ComponentNames.PRODUCT_RESEARCH, loop_number=1) == 2
    assert get_search_limit(ComponentNames.PRODUCT_RESEARCH, loop_number=2) == 4
    assert get_search_limit(ComponentNames.PRODUCT_RESEARCH, loop_number=3) == 1
    
    # Test fallback to base limit for undefined loops
    assert get_search_limit(ComponentNames.PRODUCT_RESEARCH, loop_number=99) == 3  # Base limit
    
    print("✅ Loop-specific limits working correctly")

def test_prompt_generation():
    """Test prompt text generation"""
    print("🧪 Testing prompt text generation...")
    
    # Test basic prompt
    prompt1 = generate_search_prompt_text(ComponentNames.PRODUCT_RESEARCH, current_searches=0)
    assert "MAX of 3 searches" in prompt1
    
    # Test with current searches
    prompt2 = generate_search_prompt_text(ComponentNames.PRODUCT_RESEARCH, current_searches=2)
    assert "Max 3 searches" in prompt2
    assert "already used 2 searches" in prompt2
    
    # Test with loop number
    prompt3 = generate_search_prompt_text(ComponentNames.PRODUCT_RESEARCH, current_searches=1, loop_number=2)
    assert "Max 4 searches" in prompt3  # Loop 2 limit from above configuration
    assert "(loop 2)" in prompt3
    
    print("✅ Prompt generation working correctly")

def test_limit_checking():
    """Test search limit checking"""
    print("🧪 Testing search limit checking...")
    
    # Test basic limit checking
    assert not is_search_limit_reached(ComponentNames.PRODUCT_RESEARCH, current_searches=2)  # 2 < 3
    assert is_search_limit_reached(ComponentNames.PRODUCT_RESEARCH, current_searches=3)      # 3 >= 3
    
    # Test with loop limits
    assert not is_search_limit_reached(ComponentNames.PRODUCT_RESEARCH, current_searches=1, loop_number=2)  # 1 < 4
    assert is_search_limit_reached(ComponentNames.PRODUCT_RESEARCH, current_searches=4, loop_number=2)      # 4 >= 4
    
    print("✅ Limit checking working correctly")

def test_graph_v2_integration():
    """Test that graph_v2 can import and configure limits"""
    print("🧪 Testing graph_v2 integration...")
    
    try:
        from agent.graph_v2 import (
            configure_search_limits_for_product_search,
            configure_aggressive_search_limits,
            configure_thorough_search_limits,
            initialize_graph_with_search_limits
        )
        
        # Test different configurations
        configure_aggressive_search_limits()
        assert get_search_limit(ComponentNames.PRODUCT_EXPLORATION) == 1  # Aggressive setting
        
        configure_thorough_search_limits()
        assert get_search_limit(ComponentNames.PRODUCT_EXPLORATION) == 4  # Thorough setting
        
        configure_search_limits_for_product_search()  # Reset to default
        assert get_search_limit(ComponentNames.PRODUCT_EXPLORATION) == 2  # Default setting
        
        print("✅ Graph v2 integration working correctly")
        
    except ImportError as e:
        print(f"⚠️ Could not test graph_v2 integration: {e}")

def main():
    """Run all tests"""
    print("🚀 Testing centralized search limits configuration...\n")
    
    test_default_limits()
    test_loop_specific_limits()
    test_prompt_generation()
    test_limit_checking()
    test_graph_v2_integration()
    
    print("\n🎉 All tests passed! Search limits configuration is working correctly.")
    
    # Show current configuration
    print("\n📊 Current Search Limits Configuration:")
    print(f"  Product Exploration: {get_search_limit(ComponentNames.PRODUCT_EXPLORATION)}")
    print(f"  Product Research: {get_search_limit(ComponentNames.PRODUCT_RESEARCH)}")
    print(f"  Final Product Info: {get_search_limit(ComponentNames.FINAL_PRODUCT_INFO)}")
    print(f"  General Research: {get_search_limit(ComponentNames.GENERAL_RESEARCH)}")
    
    print("\n📝 Example prompt texts:")
    print(f"  Product Research (0 searches): {generate_search_prompt_text(ComponentNames.PRODUCT_RESEARCH, 0)}")
    print(f"  Product Research (2 searches, loop 1): {generate_search_prompt_text(ComponentNames.PRODUCT_RESEARCH, 2, 1)}")

if __name__ == "__main__":
    main()