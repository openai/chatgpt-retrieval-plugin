# ConnectWise Manage Integration

Import historical tickets from ConnectWise Manage into the retrieval plugin for searchable knowledge base.

## Setup

### 1. Get ConnectWise API Credentials

1. Log into ConnectWise Manage
2. Go to **System > Members > API Members**
3. Create a new API member or use existing
4. Note your:
   - Company ID
   - Public Key
   - Private Key
5. Register for a Client ID at: https://developer.connectwise.com/ClientID

### 2. Set Environment Variables

```bash
export CW_COMPANY_ID="your_company_id"
export CW_PUBLIC_KEY="your_public_key"
export CW_PRIVATE_KEY="your_private_key"
export CW_CLIENT_ID="your_client_id"
export CW_API_URL="https://api-na.myconnectwise.net"  # or your region
export CW_DAYS_BACK="365"  # How many days of history to import (default: 365)

# Also set your retrieval plugin environment variables
export DATASTORE="your_datastore"
export BEARER_TOKEN="your_bearer_token"
export OPENAI_API_KEY="your_openai_api_key"
```

### 3. Install Dependencies

The script uses only standard libraries plus `requests`:

```bash
poetry add requests
```

## Usage

### Option A: One-Time Historical Import

1. **Export tickets to JSON:**

```bash
cd scripts/connectwise_import
python connectwise_importer.py
```

This creates `connectwise_tickets.json` with all closed tickets.

2. **Upload to vector database:**

```bash
python ../process_json/process_json.py connectwise_tickets.json
```

### Option B: Direct Import (Custom Script)

Create a custom script that directly calls the retrieval plugin's upsert endpoint:

```python
from connectwise_importer import ConnectWiseImporter
import requests
import os

# Initialize importer
importer = ConnectWiseImporter(
    company_id=os.getenv('CW_COMPANY_ID'),
    public_key=os.getenv('CW_PUBLIC_KEY'),
    private_key=os.getenv('CW_PRIVATE_KEY'),
    api_url=os.getenv('CW_API_URL'),
    client_id=os.getenv('CW_CLIENT_ID')
)

# Get tickets
tickets = importer.get_closed_tickets(days_back=365)

# Convert to documents
documents = [importer.convert_ticket_to_document(t) for t in tickets]

# Upload to retrieval plugin
api_url = "http://localhost:8000/upsert"
bearer_token = os.getenv('BEARER_TOKEN')

response = requests.post(
    api_url,
    headers={'Authorization': f'Bearer {bearer_token}'},
    json={'documents': [doc.dict() for doc in documents]}
)

print(f"Uploaded {len(documents)} tickets. Response: {response.json()}")
```

## Filtering Options

### Import Specific Ticket Types

Modify the `conditions` in `get_closed_tickets()`:

```python
# Only tickets from specific board
conditions = f"closedFlag=true AND board/name='IT Support'"

# Only tickets from specific company
conditions = f"closedFlag=true AND company/name='Acme Corp'"

# Only high priority tickets
conditions = f"closedFlag=true AND priority/name='High'"

# Tickets with resolution notes
conditions = f"closedFlag=true AND resolution!=null"
```

### Import Specific Time Range

```python
# Last 30 days
tickets = importer.get_closed_tickets(days_back=30)

# Last 2 years
tickets = importer.get_closed_tickets(days_back=730)
```

## Real-Time Sync with Webhooks

To automatically index new tickets as they're closed, set up a webhook in ConnectWise:

### 1. Create Webhook in ConnectWise

1. Go to **System > API Reports > Workflow Rules**
2. Create new rule:
   - **Trigger**: Ticket Status Changed
   - **Condition**: Status = "Closed"
   - **Action**: Call URL
   - **URL**: `https://your-retrieval-plugin.com/connectwise-webhook`
   - **Method**: POST

### 2. Add Webhook Endpoint

Add this to `server/main.py`:

```python
from fastapi import Request

@app.post("/connectwise-webhook")
async def connectwise_webhook(request: Request):
    """Receive webhook from ConnectWise when ticket is closed"""
    try:
        data = await request.json()
        ticket_id = data.get('id')

        # Fetch full ticket details from ConnectWise
        # (You'll need to implement this or use the importer class)

        # Convert to document and upsert
        # document = convert_ticket_to_document(ticket_data)
        # await datastore.upsert([document])

        return {"status": "success", "ticket_id": ticket_id}
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
```

## Advanced: Custom Metadata

To add MSP-specific metadata, modify the script:

```python
# In models/models.py, create custom metadata class
class ConnectWiseMetadata(DocumentMetadata):
    ticket_id: Optional[str]
    client_name: Optional[str]
    board_name: Optional[str]
    priority: Optional[str]
    ticket_type: Optional[str]
    resolved_by: Optional[str]
    resolution_time_hours: Optional[float]

# Then in connectwise_importer.py
metadata = ConnectWiseMetadata(
    source=Source.file,
    source_id=str(ticket.get('id')),
    ticket_id=str(ticket.get('id')),
    client_name=ticket.get('company', {}).get('name'),
    board_name=ticket.get('board', {}).get('name'),
    priority=ticket.get('priority', {}).get('name'),
    ticket_type=ticket.get('type', {}).get('name'),
    resolved_by=ticket.get('closedBy'),
    created_at=ticket.get('dateEntered'),
    author=ticket.get('contactName'),
    url=self._build_ticket_url(ticket.get('id'))
)
```

## Querying Tickets in Chat UI

Once imported, you can query tickets like:

```
"Find tickets about email migration issues"
"How did we resolve printer problems for Acme Corp?"
"Show me tickets closed by John last month"
"What's the solution for error code 0x80070005?"
```

## Cost Estimation

- OpenAI embedding cost: ~$0.0001 per 1000 tokens
- Average ticket: ~500 tokens
- 10,000 tickets: ~$0.50 in embedding costs
- Ongoing: Cost per new ticket closed (~$0.00005)

## Scheduling Automated Imports

### Using Cron (Linux/Mac)

```bash
# Daily import of yesterday's closed tickets
0 2 * * * cd /path/to/chatgpt-retrieval-plugin/scripts/connectwise_import && /usr/bin/python connectwise_importer.py
```

### Using Windows Task Scheduler

Create a batch file `import_tickets.bat`:

```batch
@echo off
cd C:\path\to\chatgpt-retrieval-plugin\scripts\connectwise_import
python connectwise_importer.py
```

Schedule it to run daily at 2 AM.

## Troubleshooting

### Authentication Errors

- Verify Company ID format (usually lowercase)
- Check public/private key validity
- Ensure Client ID is registered
- Verify API member has correct permissions

### API Rate Limits

ConnectWise has rate limits (typically 1000 calls per 5 minutes):
- Reduce `page_size` if hitting limits
- Add delays between requests if needed

### Missing Ticket Data

- Check API member permissions (needs read access to tickets, notes, companies)
- Verify board access restrictions
- Some fields may be null for older tickets

## Security Best Practices

- **Never commit credentials** to version control
- Use environment variables or secrets manager
- Rotate API keys regularly
- Restrict API member permissions (read-only)
- Use HTTPS for webhook endpoints
- Validate webhook signatures (if ConnectWise supports it)

## Next Steps

1. Test with small batch first (days_back=7)
2. Review exported JSON for data quality
3. Adjust text formatting as needed
4. Set up automated daily imports
5. Create webhook for real-time updates
6. Build chat UI for technicians
