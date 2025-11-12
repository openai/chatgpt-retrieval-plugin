"""
ConnectWise webhook handler for real-time ticket indexing
Automatically indexes tickets as they're closed in ConnectWise
"""
import sys
import os
from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.models import Document
from models.msp_models import MSPMetadata
from models.models import Source


class ConnectWiseWebhookPayload(BaseModel):
    """
    ConnectWise webhook payload structure
    Adjust based on your actual webhook configuration
    """
    id: int
    action: str  # added, updated, deleted
    type: str  # ServiceTicket, etc.
    memberId: Optional[str] = None
    companyId: Optional[str] = None


class TicketClosedEvent(BaseModel):
    """Parsed ticket closed event"""
    ticket_id: int
    company_id: Optional[int] = None
    closed_by: Optional[str] = None
    closed_date: Optional[str] = None


class ConnectWiseWebhookHandler:
    """
    Handles ConnectWise webhooks and indexes tickets automatically
    """

    def __init__(self, cw_client, datastore, logger=None):
        """
        Initialize webhook handler

        Args:
            cw_client: ConnectWise API client (ConnectWiseImporter)
            datastore: Datastore instance for upserting documents
            logger: Logger instance
        """
        self.cw_client = cw_client
        self.datastore = datastore
        self.logger = logger

    async def handle_webhook(self, payload: Dict) -> Dict[str, any]:
        """
        Process incoming webhook from ConnectWise

        Args:
            payload: Webhook payload dict

        Returns:
            Dict with processing result
        """
        if self.logger:
            self.logger.info(
                "Received ConnectWise webhook",
                extra={"extra_fields": {"payload": payload}}
            )

        try:
            # Parse payload
            event = ConnectWiseWebhookPayload(**payload)

            # Only process ticket closed events
            if event.type != "ServiceTicket":
                return {"status": "ignored", "reason": "Not a service ticket"}

            if event.action not in ["updated", "closed"]:
                return {"status": "ignored", "reason": f"Action '{event.action}' not tracked"}

            # Fetch full ticket details from ConnectWise
            ticket = self._fetch_ticket(event.id)

            if not ticket:
                return {"status": "error", "reason": "Failed to fetch ticket details"}

            # Check if ticket is actually closed
            if not ticket.get("closedFlag"):
                return {"status": "ignored", "reason": "Ticket not closed yet"}

            # Convert to document and index
            document = self._ticket_to_document(ticket)

            if self.logger:
                self.logger.info(
                    f"Indexing ticket #{event.id}",
                    extra={"extra_fields": {"ticket_id": event.id, "client": ticket.get("company", {}).get("name")}}
                )

            # Upsert to datastore
            doc_ids = await self.datastore.upsert([document])

            return {
                "status": "success",
                "ticket_id": event.id,
                "document_id": doc_ids[0] if doc_ids else None,
                "message": f"Ticket #{event.id} indexed successfully"
            }

        except Exception as e:
            error_msg = f"Error processing webhook: {str(e)}"
            if self.logger:
                self.logger.error(error_msg, exc_info=True)

            return {
                "status": "error",
                "error": str(e)
            }

    def _fetch_ticket(self, ticket_id: int) -> Optional[Dict]:
        """
        Fetch full ticket details from ConnectWise API

        Args:
            ticket_id: The ticket ID

        Returns:
            Ticket dictionary or None if failed
        """
        try:
            import requests

            response = requests.get(
                f"{self.cw_client.api_url}/v4_6_release/apis/3.0/service/tickets/{ticket_id}",
                headers=self.cw_client.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to fetch ticket {ticket_id}: {e}")
            return None

    def _ticket_to_document(self, ticket: Dict) -> Document:
        """
        Convert ConnectWise ticket to Document with MSP metadata

        Args:
            ticket: ConnectWise ticket dictionary

        Returns:
            Document object
        """
        # Build comprehensive text
        text_parts = [
            f"Ticket #{ticket.get('id')}: {ticket.get('summary', 'No summary')}",
            f"\nClient: {ticket.get('company', {}).get('name', 'Unknown')}",
            f"Priority: {ticket.get('priority', {}).get('name', 'Unknown')}",
            f"Type: {ticket.get('type', {}).get('name', 'Unknown')}"
        ]

        if ticket.get('initialDescription'):
            text_parts.append(f"\n\nProblem:\n{ticket['initialDescription']}")

        if ticket.get('resolution'):
            text_parts.append(f"\n\nResolution:\n{ticket['resolution']}")

        # Get notes
        notes = self.cw_client.get_ticket_notes(ticket['id'])
        if notes:
            text_parts.append("\n\nTechnician Notes:")
            for note in notes:
                if note.get('text'):
                    creator = note.get('createdBy', 'Unknown')
                    text_parts.append(f"- [{creator}] {note['text']}")

        full_text = "\n".join(text_parts)

        # Calculate resolution time
        resolution_time = None
        if ticket.get('dateEntered') and ticket.get('dateClosed'):
            try:
                entered = datetime.fromisoformat(ticket['dateEntered'].replace('Z', '+00:00'))
                closed = datetime.fromisoformat(ticket['dateClosed'].replace('Z', '+00:00'))
                resolution_time = (closed - entered).total_seconds() / 3600
            except:
                pass

        # Create metadata
        metadata = MSPMetadata(
            source=Source.file,
            source_id=str(ticket.get('id')),
            created_at=ticket.get('dateEntered'),
            author=ticket.get('contactName') or ticket.get('contactEmailAddress'),
            url=self._build_ticket_url(ticket.get('id')),

            ticket_id=str(ticket.get('id')),
            ticket_number=ticket.get('ticketNumber'),

            client_name=ticket.get('company', {}).get('name'),
            client_id=str(ticket.get('company', {}).get('id')) if ticket.get('company', {}).get('id') else None,
            company_identifier=ticket.get('company', {}).get('identifier'),

            board_name=ticket.get('board', {}).get('name'),
            ticket_type=ticket.get('type', {}).get('name'),
            sub_type=ticket.get('subType', {}).get('name'),
            priority=ticket.get('priority', {}).get('name'),
            severity=ticket.get('severity'),
            status=ticket.get('status', {}).get('name'),

            resolved_by=ticket.get('closedBy'),
            resolution_time_hours=resolution_time,
            resolution_summary=ticket.get('resolution'),

            product_name=ticket.get('item', {}).get('name') if ticket.get('item') else None,
            service_location=ticket.get('serviceLocation', {}).get('name'),

            actual_hours=ticket.get('actualHours'),
            billable_hours=ticket.get('billableHours'),
            budget_hours=ticket.get('budgetHours'),

            impact=ticket.get('impact'),
        )

        return Document(
            id=f"cw_ticket_{ticket['id']}",
            text=full_text,
            metadata=metadata
        )

    def _build_ticket_url(self, ticket_id: int) -> str:
        """Build URL to view ticket in ConnectWise"""
        return f"{self.cw_client.api_url}/v4_6_release/services/system_io/Service/fv_sr100_request.rails?service_recid={ticket_id}"


async def verify_webhook_signature(request_body: bytes, signature: str, secret: str) -> bool:
    """
    Verify webhook signature (if ConnectWise supports it)

    Args:
        request_body: Raw request body bytes
        signature: Signature from header
        secret: Shared secret

    Returns:
        True if signature is valid
    """
    import hmac
    import hashlib

    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)
