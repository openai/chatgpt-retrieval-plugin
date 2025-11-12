"""
Extended models for MSP/ConnectWise ticket tracking
Adds MSP-specific metadata fields to the base models
"""
from pydantic import BaseModel
from typing import List, Optional
from models.models import DocumentMetadata, DocumentMetadataFilter, Source


class MSPMetadata(DocumentMetadata):
    """
    Extended metadata for MSP tickets with ConnectWise-specific fields
    """
    # Ticket identification
    ticket_id: Optional[str] = None
    ticket_number: Optional[str] = None

    # Client information
    client_name: Optional[str] = None
    client_id: Optional[str] = None
    company_identifier: Optional[str] = None

    # Ticket categorization
    board_name: Optional[str] = None  # e.g., "IT Support", "Network Services"
    ticket_type: Optional[str] = None  # e.g., "Service Request", "Incident"
    sub_type: Optional[str] = None  # More specific categorization
    issue_category: Optional[str] = None  # e.g., "Email", "Network", "Hardware"
    priority: Optional[str] = None  # P1, P2, P3, P4
    severity: Optional[str] = None  # Critical, High, Medium, Low

    # Resolution tracking
    status: Optional[str] = None  # Closed, Resolved, etc.
    resolved_by: Optional[str] = None  # Tech who resolved it
    closed_by: Optional[str] = None
    resolution_time_hours: Optional[float] = None  # Time to resolution
    resolution_summary: Optional[str] = None  # Brief resolution description

    # Products and services
    product_name: Optional[str] = None  # e.g., "Office 365", "Firewall"
    service_location: Optional[str] = None  # Physical location if relevant
    affected_device: Optional[str] = None  # Computer name, IP, etc.

    # Technical details
    error_codes: Optional[List[str]] = None  # Any error codes mentioned
    tags: Optional[List[str]] = None  # Custom tags
    impact: Optional[str] = None  # User, Department, Company-wide

    # Time tracking
    actual_hours: Optional[float] = None
    billable_hours: Optional[float] = None
    budget_hours: Optional[float] = None

    # Additional fields
    escalation_level: Optional[int] = None  # 0 = not escalated, 1+
    customer_satisfaction: Optional[int] = None  # Rating if available
    has_remote_session: Optional[bool] = None
    requires_follow_up: Optional[bool] = None


class MSPMetadataFilter(DocumentMetadataFilter):
    """
    Extended filters for searching MSP tickets
    Allows filtering by MSP-specific fields
    """
    # Client filters
    client_name: Optional[str] = None
    client_id: Optional[str] = None

    # Ticket filters
    ticket_id: Optional[str] = None
    board_name: Optional[str] = None
    priority: Optional[str] = None
    ticket_type: Optional[str] = None
    issue_category: Optional[str] = None

    # Resolution filters
    resolved_by: Optional[str] = None
    min_resolution_hours: Optional[float] = None
    max_resolution_hours: Optional[float] = None

    # Product filters
    product_name: Optional[str] = None

    # Status filters
    severity: Optional[str] = None
    escalation_level: Optional[int] = None


class TicketSearchQuery(BaseModel):
    """
    Specialized query model for ticket searches
    """
    query: str
    filter: Optional[MSPMetadataFilter] = None
    top_k: Optional[int] = 3
    include_similar: Optional[bool] = True  # Include similar ticket suggestions
    min_relevance_score: Optional[float] = 0.7  # Minimum similarity score


class TicketSuggestion(BaseModel):
    """
    Suggested solution based on similar past tickets
    """
    ticket_id: str
    ticket_summary: str
    resolution_summary: str
    relevance_score: float
    resolved_by: Optional[str] = None
    resolution_time_hours: Optional[float] = None
    url: Optional[str] = None


class KnowledgeBaseStats(BaseModel):
    """
    Statistics about the MSP knowledge base
    """
    total_tickets: int
    total_clients: int
    tickets_by_priority: dict
    tickets_by_category: dict
    avg_resolution_time: float
    most_common_issues: List[tuple]  # (issue, count)
    top_resolvers: List[tuple]  # (tech_name, ticket_count)
    date_range: dict  # start_date, end_date
