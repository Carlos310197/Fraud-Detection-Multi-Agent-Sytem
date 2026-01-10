"""Governed web search providers."""
from abc import ABC, abstractmethod
from typing import Any

from app.web.allowlist import Allowlist
from app.core.logging import logger


class SearchResult:
    """Web search result."""
    
    def __init__(self, url: str, summary: str):
        self.url = url
        self.summary = summary
    
    def to_dict(self) -> dict[str, str]:
        return {"url": self.url, "summary": self.summary}


class SearchProvider(ABC):
    """Abstract interface for web search providers."""
    
    @abstractmethod
    def search(self, query: str, max_results: int = 3) -> list[SearchResult]:
        """
        Search the web for a query.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        pass


class MockSearchProvider(SearchProvider):
    """
    Mock search provider for local development.
    
    Returns deterministic results based on merchant_id patterns.
    """
    
    # Mock database of fraud alerts by merchant pattern
    MOCK_ALERTS: dict[str, list[dict[str, str]]] = {
        "M-FRAUD": [
            {
                "url": "https://example.com/alerts/fraud-ring-2025",
                "summary": "Alerta de fraude reciente: red de fraude detectada operando con comercios similares. Múltiples reportes de transacciones no autorizadas."
            },
            {
                "url": "https://owasp.org/security-alert-2025-001",
                "summary": "Aviso de seguridad: Endpoints de comercios comprometidos detectados en la región de América Latina."
            }
        ],
        "M-SUSPICIOUS": [
            {
                "url": "https://mitre.org/cve/2025/merchant-fraud",
                "summary": "CVE-2025-XXXX: Vulnerabilidad en sistemas de pago que permite transacciones fraudulentas."
            }
        ]
    }
    
    def __init__(self, allowlist: Allowlist):
        """
        Initialize the mock search provider.
        
        Args:
            allowlist: Allowlist for URL filtering
        """
        self.allowlist = allowlist
    
    def search(self, query: str, max_results: int = 3) -> list[SearchResult]:
        """
        Search for alerts related to the query.
        
        Returns mock results based on merchant patterns in the query.
        """
        results = []
        query_upper = query.upper()
        
        # Check for known patterns in query
        for pattern, alerts in self.MOCK_ALERTS.items():
            if pattern in query_upper:
                for alert in alerts:
                    if self.allowlist.is_allowed(alert["url"]):
                        results.append(SearchResult(
                            url=alert["url"],
                            summary=alert["summary"]
                        ))
        
        # Limit results
        results = results[:max_results]
        
        logger.info(f"Mock search for '{query}' returned {len(results)} results")
        return results


class CustomHttpProvider(SearchProvider):
    """
    Custom HTTP-based search provider.
    
    For integration with external search APIs in production.
    """
    
    def __init__(self, allowlist: Allowlist, api_url: str | None = None, api_key: str | None = None):
        """
        Initialize the HTTP search provider.
        
        Args:
            allowlist: Allowlist for URL filtering
            api_url: Base URL for the search API
            api_key: API key for authentication
        """
        self.allowlist = allowlist
        self.api_url = api_url
        self.api_key = api_key
    
    def search(self, query: str, max_results: int = 3) -> list[SearchResult]:
        """
        Search using external API.
        
        Note: This is a placeholder for production implementation.
        """
        import httpx
        
        if not self.api_url:
            logger.warning("CustomHttpProvider: No API URL configured")
            return []
        
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    self.api_url,
                    params={"q": query, "limit": max_results * 2},
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
            
            results = []
            for item in data.get("results", []):
                url = item.get("url", "")
                if self.allowlist.is_allowed(url):
                    results.append(SearchResult(
                        url=url,
                        summary=item.get("snippet", "")
                    ))
            
            return results[:max_results]
        
        except Exception as e:
            logger.error(f"CustomHttpProvider search failed: {e}")
            return []


class GovernedSearchService:
    """
    Governed web search service that enforces allowlist rules.
    """
    
    def __init__(self, provider: SearchProvider, max_results: int = 3):
        """
        Initialize the governed search service.
        
        Args:
            provider: Search provider implementation
            max_results: Maximum results to return
        """
        self.provider = provider
        self.max_results = max_results
    
    def search(self, query: str) -> list[dict[str, str]]:
        """
        Execute a governed web search.
        
        Args:
            query: Search query
            
        Returns:
            List of {url, summary} dicts
        """
        results = self.provider.search(query, self.max_results)
        return [r.to_dict() for r in results]


def get_search_provider(
    provider_type: str,
    allowlist: Allowlist,
    **kwargs
) -> SearchProvider:
    """
    Factory function to get a search provider.
    
    Args:
        provider_type: "mock" or "custom"
        allowlist: Allowlist instance
        **kwargs: Additional provider arguments
        
    Returns:
        SearchProvider instance
    """
    if provider_type == "mock":
        return MockSearchProvider(allowlist)
    elif provider_type == "custom":
        return CustomHttpProvider(allowlist, **kwargs)
    else:
        raise ValueError(f"Unknown search provider: {provider_type}")
