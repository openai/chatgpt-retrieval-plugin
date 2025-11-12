"""
Example usage of ConnectWise integration with enhanced MSP metadata
"""
import os
import requests
from connectwise_importer import ConnectWiseImporter
from models.msp_models import MSPMetadata
from models.models import Document, Source
from datetime import datetime


def enhanced_ticket_to_document(importer: ConnectWiseImporter, ticket: dict) -> Document:
    """
    Convert ConnectWise ticket to Document with enhanced MSP metadata

    Args:
        importer: ConnectWiseImporter instance
        ticket: ConnectWise ticket dictionary

    Returns:
        Document with MSPMetadata
    """
    # Build comprehensive ticket text
    text_parts = [
        f"Ticket #{ticket.get('id')}: {ticket.get('summary', 'No summary')}",
        f"\nClient: {ticket.get('company', {}).get('name', 'Unknown')}",
        f"Priority: {ticket.get('priority', {}).get('name', 'Unknown')}",
        f"Type: {ticket.get('type', {}).get('name', 'Unknown')}"
    ]

    # Problem description
    if ticket.get('initialDescription'):
        text_parts.append(f"\n\nProblem:\n{ticket['initialDescription']}")

    # Resolution
    if ticket.get('resolution'):
        text_parts.append(f"\n\nResolution:\n{ticket['resolution']}")

    # Get notes
    notes = importer.get_ticket_notes(ticket['id'])
    if notes:
        text_parts.append("\n\nTechnician Notes:")
        for note in notes:
            if note.get('text'):
                creator = note.get('createdBy', 'Unknown')
                text_parts.append(f"- [{creator}] {note['text']}")

    full_text = "\n".join(text_parts)

    # Calculate resolution time if possible
    resolution_time = None
    if ticket.get('dateEntered') and ticket.get('dateClosed'):
        try:
            entered = datetime.fromisoformat(ticket['dateEntered'].replace('Z', '+00:00'))
            closed = datetime.fromisoformat(ticket['dateClosed'].replace('Z', '+00:00'))
            resolution_time = (closed - entered).total_seconds() / 3600  # hours
        except:
            pass

    # Create enhanced metadata
    metadata = MSPMetadata(
        source=Source.file,
        source_id=str(ticket.get('id')),
        created_at=ticket.get('dateEntered'),
        author=ticket.get('contactName') or ticket.get('contactEmailAddress'),
        url=importer._build_ticket_url(ticket.get('id')),

        # Ticket info
        ticket_id=str(ticket.get('id')),
        ticket_number=ticket.get('ticketNumber'),

        # Client info
        client_name=ticket.get('company', {}).get('name'),
        client_id=str(ticket.get('company', {}).get('id')) if ticket.get('company', {}).get('id') else None,
        company_identifier=ticket.get('company', {}).get('identifier'),

        # Categorization
        board_name=ticket.get('board', {}).get('name'),
        ticket_type=ticket.get('type', {}).get('name'),
        sub_type=ticket.get('subType', {}).get('name'),
        priority=ticket.get('priority', {}).get('name'),
        severity=ticket.get('severity'),
        status=ticket.get('status', {}).get('name'),

        # Resolution
        resolved_by=ticket.get('closedBy'),
        resolution_time_hours=resolution_time,
        resolution_summary=ticket.get('resolution'),

        # Products
        product_name=ticket.get('item', {}).get('name') if ticket.get('item') else None,
        service_location=ticket.get('serviceLocation', {}).get('name'),

        # Time tracking
        actual_hours=ticket.get('actualHours'),
        billable_hours=ticket.get('billableHours'),
        budget_hours=ticket.get('budgetHours'),

        # Additional
        impact=ticket.get('impact'),
    )

    return Document(
        id=f"cw_ticket_{ticket['id']}",
        text=full_text,
        metadata=metadata
    )


def import_and_upload_tickets(days_back: int = 30):
    """
    Import tickets from ConnectWise and upload directly to retrieval plugin

    Args:
        days_back: Number of days of history to import
    """
    # Initialize ConnectWise importer
    importer = ConnectWiseImporter(
        company_id=os.getenv('CW_COMPANY_ID'),
        public_key=os.getenv('CW_PUBLIC_KEY'),
        private_key=os.getenv('CW_PRIVATE_KEY'),
        api_url=os.getenv('CW_API_URL', 'https://api-na.myconnectwise.net'),
        client_id=os.getenv('CW_CLIENT_ID')
    )

    print(f"Fetching tickets from last {days_back} days...")
    tickets = importer.get_closed_tickets(days_back=days_back)
    print(f"Found {len(tickets)} closed tickets")

    # Convert to enhanced documents
    print("Converting tickets to documents with enhanced metadata...")
    documents = []
    for i, ticket in enumerate(tickets, 1):
        if i % 10 == 0:
            print(f"Processed {i}/{len(tickets)}...")

        doc = enhanced_ticket_to_document(importer, ticket)
        documents.append(doc)

    # Upload to retrieval plugin
    print(f"\nUploading {len(documents)} documents to retrieval plugin...")

    retrieval_api_url = os.getenv('RETRIEVAL_API_URL', 'http://localhost:8000')
    bearer_token = os.getenv('BEARER_TOKEN')

    if not bearer_token:
        print("Error: BEARER_TOKEN not set")
        return

    # Upload in batches of 50
    batch_size = 50
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]

        try:
            response = requests.post(
                f"{retrieval_api_url}/upsert",
                headers={
                    'Authorization': f'Bearer {bearer_token}',
                    'Content-Type': 'application/json'
                },
                json={
                    'documents': [
                        {
                            'id': doc.id,
                            'text': doc.text,
                            'metadata': doc.metadata.dict() if doc.metadata else {}
                        }
                        for doc in batch
                    ]
                },
                timeout=300  # 5 minute timeout for large batches
            )
            response.raise_for_status()
            print(f"Uploaded batch {i//batch_size + 1}: {len(batch)} documents")
        except requests.exceptions.RequestException as e:
            print(f"Error uploading batch: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")

    print(f"\n✅ Successfully imported {len(documents)} tickets!")


def search_tickets_example():
    """
    Example of searching tickets using the retrieval plugin
    """
    retrieval_api_url = os.getenv('RETRIEVAL_API_URL', 'http://localhost:8000')
    bearer_token = os.getenv('BEARER_TOKEN')

    # Example queries
    queries = [
        {
            "query": "How to fix email sync issues in Outlook?",
            "top_k": 3
        },
        {
            "query": "VPN connection problems",
            "filter": {
                "client_name": "Acme Corp"
            },
            "top_k": 5
        },
        {
            "query": "printer not working",
            "filter": {
                "priority": "High"
            },
            "top_k": 3
        }
    ]

    for query_obj in queries:
        print(f"\n🔍 Query: {query_obj['query']}")

        try:
            response = requests.post(
                f"{retrieval_api_url}/query",
                headers={
                    'Authorization': f'Bearer {bearer_token}',
                    'Content-Type': 'application/json'
                },
                json={'queries': [query_obj]},
                timeout=30
            )
            response.raise_for_status()

            results = response.json()

            print(f"Found {len(results['results'][0]['results'])} similar tickets:\n")

            for i, result in enumerate(results['results'][0]['results'], 1):
                print(f"{i}. Score: {result['score']:.3f}")
                print(f"   Text preview: {result['text'][:200]}...")
                if result.get('metadata'):
                    meta = result['metadata']
                    if meta.get('ticket_id'):
                        print(f"   Ticket ID: {meta['ticket_id']}")
                    if meta.get('client_name'):
                        print(f"   Client: {meta['client_name']}")
                    if meta.get('resolved_by'):
                        print(f"   Resolved by: {meta['resolved_by']}")
                print()

        except requests.exceptions.RequestException as e:
            print(f"Error querying: {e}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'search':
        # Run search examples
        search_tickets_example()
    else:
        # Run import
        days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
        import_and_upload_tickets(days_back=days)
