"""Allowlist management for governed web search."""
from urllib.parse import urlparse

from app.core.logging import logger


class Allowlist:
    """
    Manages domain allowlist for governed web search.
    """
    
    def __init__(self, domains: set[str]):
        """
        Initialize the allowlist.
        
        Args:
            domains: Set of allowed domain names
        """
        self.domains = {d.lower().strip() for d in domains}
        logger.info(f"Initialized allowlist with {len(self.domains)} domains: {self.domains}")
    
    def is_allowed(self, url: str) -> bool:
        """
        Check if a URL's domain is in the allowlist.
        
        Args:
            url: URL to check
            
        Returns:
            True if domain is allowed, False otherwise
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove port if present
            if ":" in domain:
                domain = domain.split(":")[0]
            
            # Check exact match
            if domain in self.domains:
                return True
            
            # Check if it's a subdomain of an allowed domain
            for allowed in self.domains:
                if domain.endswith("." + allowed):
                    return True
            
            return False
        
        except Exception:
            return False
    
    def filter_urls(self, urls: list[str]) -> list[str]:
        """
        Filter a list of URLs to only those in the allowlist.
        
        Args:
            urls: List of URLs to filter
            
        Returns:
            Filtered list of allowed URLs
        """
        return [url for url in urls if self.is_allowed(url)]
