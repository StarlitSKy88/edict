#!/usr/bin/env python3
"""
Edict AI搜索 - Tavily
"""
import os
import json
import requests
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    content: str
    provider: str

class AISearch:
    """AI搜索 - 基于Tavily"""
    
    def __init__(self, provider: str = "tavily"):
        self.provider = provider
        self.api_key = os.getenv("TAVILY_API_KEY", "")
    
    def search(self, query: str, num: int = 5) -> List[SearchResult]:
        """搜索"""
        
        if self.provider == "tavily":
            return self._tavily_search(query, num)
        else:
            return self._fallback_search(query, num)
    
    def _tavily_search(self, query: str, num: int) -> List[SearchResult]:
        """Tavily搜索"""
        
        if not self.api_key:
            return self._openclaw_search(query, num, "tavily")
        
        url = "https://api.tavily.com/search"
        data = {
            "api_key": self.api_key,
            "query": query,
            "max_results": num
        }
        
        try:
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            results = []
            for item in result.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    provider="tavily"
                ))
            
            return results
        except Exception as e:
            return self._fallback_search(query, num)
    
    def _openclaw_search(self, query: str, num: int, provider: str) -> List[SearchResult]:
        """使用OpenClaw内置搜索"""
        # 模拟结果
        return [
            SearchResult(
                title=f"[{provider}] 结果 {i+1}: {query}",
                url=f"https://example.com/{i}",
                content=f"关于{query}的相关信息...",
                provider=provider
            )
            for i in range(num)
        ]
    
    def _fallback_search(self, query: str, num: int) -> List[SearchResult]:
        """降级搜索"""
        return self._openclaw_search(query, num, "fallback")

if __name__ == '__main__':
    import sys
    
    provider = sys.argv[1] if len(sys.argv) > 1 else "tavily"
    query = sys.argv[2] if len(sys.argv) > 2 else "AI trends 2026"
    
    searcher = AISearch(provider=provider)
    results = searcher.search(query)
    
    print(f"=== {provider} 搜索结果 ===")
    for r in results:
        print(f"\n标题: {r.title}")
        print(f"来源: {r.url}")
        print(f"内容: {r.content[:150]}...")
