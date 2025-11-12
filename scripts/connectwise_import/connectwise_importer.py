"""
ConnectWise Manage API Integration for Ticket Import
Pulls closed tickets and indexes them into the retrieval plugin
"""
import requests
import base64
import os
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from models.models import Document, DocumentMetadata, Source


class ConnectWiseImporter:
    """Import tickets from ConnectWise Manage into the retrieval plugin"""

    def __init__(
        self,
        company_id: str,
        public_key: str,
        private_key: str,
        api_url: str,
        client_id: str
    ):
        """
        Initialize ConnectWise API client

        Args:
            company_id: Your ConnectWise company identifier
            public_key: API public key
            private_key: API private key
            api_url: Base URL (e.g., https://api-na.myconnectwise.net)
            client_id: Your registered client ID
        """
        self.company_id = company_id
        self.api_url = api_url.rstrip('/')
        self.client_id = client_id

        # Create basic auth header
        auth_string = f"{company_id}+{public_key}:{private_key}"
        auth_bytes = auth_string.encode('ascii')
        base64_auth = base64.b64encode(auth_bytes).decode('ascii')

        self.headers = {
            'Authorization': f'Basic {base64_auth}',
            'clientId': client_id,
            'Content-Type': 'application/json'
        }

    def get_closed_tickets(
        self,
        days_back: int = 365,
        page_size: int = 100,
        status_filter: str = "closed"
    ) -> List[Dict]:
        """
        Retrieve closed tickets from ConnectWise

        Args:
            days_back: How many days of history to retrieve
            page_size: Number of tickets per API call
            status_filter: Filter by status (closed, resolved, etc.)

        Returns:
            List of ticket dictionaries
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        cutoff_str = cutoff_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        # ConnectWise API conditions
        # See: https://developer.connectwise.com/Products/Manage/Developer_Guide#Conditions
        conditions = f"closedFlag=true AND dateClosed>[{cutoff_str}]"

        all_tickets = []
        page = 1

        while True:
            print(f"Fetching page {page}...")

            params = {
                'conditions': conditions,
                'pageSize': page_size,
                'page': page,
                'orderBy': 'id desc'
            }

            try:
                response = requests.get(
                    f"{self.api_url}/v4_6_release/apis/3.0/service/tickets",
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()

                tickets = response.json()

                if not tickets:
                    break

                all_tickets.extend(tickets)
                print(f"Retrieved {len(tickets)} tickets (total: {len(all_tickets)})")

                if len(tickets) < page_size:
                    break

                page += 1

            except requests.exceptions.RequestException as e:
                print(f"Error fetching tickets: {e}")
                break

        return all_tickets

    def get_ticket_notes(self, ticket_id: int) -> List[Dict]:
        """
        Get all notes/comments for a specific ticket

        Args:
            ticket_id: The ticket ID

        Returns:
            List of note dictionaries
        """
        try:
            response = requests.get(
                f"{self.api_url}/v4_6_release/apis/3.0/service/tickets/{ticket_id}/notes",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching notes for ticket {ticket_id}: {e}")
            return []

    def convert_ticket_to_document(
        self,
        ticket: Dict,
        include_notes: bool = True
    ) -> Document:
        """
        Convert a ConnectWise ticket to a Document for the retrieval plugin

        Args:
            ticket: ConnectWise ticket dictionary
            include_notes: Whether to fetch and include ticket notes

        Returns:
            Document object ready for upserting
        """
        # Build the document text
        text_parts = []

        # Title and summary
        text_parts.append(f"Ticket #{ticket.get('id')}: {ticket.get('summary', 'No summary')}")

        # Problem description
        if ticket.get('initialDescription'):
            text_parts.append(f"\nProblem Description:\n{ticket['initialDescription']}")

        # Resolution
        if ticket.get('resolution'):
            text_parts.append(f"\nResolution:\n{ticket['resolution']}")

        # Get additional notes if requested
        if include_notes:
            notes = self.get_ticket_notes(ticket['id'])
            if notes:
                text_parts.append("\nAdditional Notes:")
                for note in notes:
                    if note.get('text'):
                        text_parts.append(f"- {note['text']}")

        full_text = "\n".join(text_parts)

        # Create metadata
        metadata = DocumentMetadata(
            source=Source.file,  # or create a custom 'connectwise' source
            source_id=str(ticket.get('id')),
            created_at=ticket.get('dateEntered'),
            author=ticket.get('contactName') or ticket.get('contactEmailAddress'),
            url=self._build_ticket_url(ticket.get('id'))
        )

        # Create document
        doc = Document(
            id=f"cw_ticket_{ticket['id']}",
            text=full_text,
            metadata=metadata
        )

        return doc

    def _build_ticket_url(self, ticket_id: int) -> str:
        """Build URL to view ticket in ConnectWise"""
        # Adjust this based on your ConnectWise setup
        return f"{self.api_url}/v4_6_release/services/system_io/Service/fv_sr100_request.rails?service_recid={ticket_id}"

    def export_to_json(self, output_file: str, days_back: int = 365):
        """
        Export tickets to JSON format compatible with process_json script

        Args:
            output_file: Path to output JSON file
            days_back: How many days of history to retrieve
        """
        print(f"Fetching tickets from last {days_back} days...")
        tickets = self.get_closed_tickets(days_back=days_back)

        print(f"Converting {len(tickets)} tickets to documents...")
        documents = []

        for i, ticket in enumerate(tickets, 1):
            if i % 10 == 0:
                print(f"Processed {i}/{len(tickets)} tickets...")

            doc = self.convert_ticket_to_document(ticket, include_notes=True)

            # Convert to dict for JSON serialization
            doc_dict = {
                "id": doc.id,
                "text": doc.text,
                "metadata": doc.metadata.dict() if doc.metadata else {}
            }
            documents.append(doc_dict)

        # Write to file
        with open(output_file, 'w') as f:
            json.dump(documents, f, indent=2)

        print(f"Exported {len(documents)} tickets to {output_file}")
        return documents


def main():
    """Main function to run the import"""

    # Load configuration from environment variables
    company_id = os.getenv('CW_COMPANY_ID')
    public_key = os.getenv('CW_PUBLIC_KEY')
    private_key = os.getenv('CW_PRIVATE_KEY')
    api_url = os.getenv('CW_API_URL', 'https://api-na.myconnectwise.net')
    client_id = os.getenv('CW_CLIENT_ID')

    if not all([company_id, public_key, private_key, client_id]):
        print("Error: Missing required environment variables")
        print("Required: CW_COMPANY_ID, CW_PUBLIC_KEY, CW_PRIVATE_KEY, CW_CLIENT_ID")
        return

    # Initialize importer
    importer = ConnectWiseImporter(
        company_id=company_id,
        public_key=public_key,
        private_key=private_key,
        api_url=api_url,
        client_id=client_id
    )

    # Export tickets to JSON
    output_file = 'connectwise_tickets.json'
    days_back = int(os.getenv('CW_DAYS_BACK', 365))

    importer.export_to_json(output_file, days_back=days_back)

    print(f"\nNext steps:")
    print(f"1. Review the exported file: {output_file}")
    print(f"2. Run the process_json script to upload to vector database:")
    print(f"   poetry run python scripts/process_json/process_json.py {output_file}")


if __name__ == '__main__':
    main()
