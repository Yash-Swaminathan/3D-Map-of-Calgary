"""Custom exception classes for the Calgary Urban Intelligence Dashboard"""

class UrbanDashboardError(Exception):
    """Base exception for Calgary Urban Intelligence Dashboard"""
    pass

class DataFetchError(UrbanDashboardError):
    """Raised when data fetching from external APIs fails"""
    pass

class LLMProcessingError(UrbanDashboardError):
    """Raised when LLM query processing fails"""
    pass

class BuildingProcessingError(UrbanDashboardError):
    """Raised when building data processing fails"""
    pass

class ProjectError(UrbanDashboardError):
    """Raised when project operations fail"""
    pass 