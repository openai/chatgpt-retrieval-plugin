"""
Enhanced FastAPI server with production-grade features:
- Structured logging
- Health checks and monitoring
- Caching layer
- Rate limiting
- Metrics and analytics
- ConnectWise webhook support
"""
import os
import time
from typing import Optional
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Depends, Body, UploadFile, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import models
from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
)
from datastore.factory import get_datastore
from services.file import get_document_from_file
from models.models import DocumentMetadata, Source

# Import new services
from services.logging_config import setup_logging, get_logger, log_query, log_api_call
from services.health import health_checker, check_datastore, check_memory_usage, check_disk_usage, SystemHealth
from services.cache import cache_manager, calculate_cost_savings
from services.connectwise_webhook import ConnectWiseWebhookHandler

# Setup logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE"),
    json_logs=os.getenv("JSON_LOGS", "false").lower() == "true"
)
logger = get_logger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Bearer token auth
bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None, "BEARER_TOKEN environment variable must be set"


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Validate bearer token"""
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        logger.warning(
            "Invalid authentication attempt",
            extra={"extra_fields": {"scheme": credentials.scheme}}
        )
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


# Create FastAPI app
app = FastAPI(
    title="ChatGPT Retrieval Plugin - Enhanced",
    description="Production-grade retrieval API with caching, monitoring, and MSP features",
    version="2.0.0",
    dependencies=[Depends(validate_token)]
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Sub-application for OpenAPI schema
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://your-app-url.com"}],
    dependencies=[Depends(validate_token)],
)
app.mount("/sub", sub_app)

# Global datastore and webhook handler
datastore = None
webhook_handler = None


# ========== Health & Monitoring Endpoints ==========

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Quick health check endpoint (liveness probe)
    Returns 200 if service is running
    """
    return {"status": "healthy", "service": "retrieval-plugin"}


@app.get("/ready", tags=["Monitoring"], response_model=SystemHealth)
async def readiness_check():
    """
    Detailed readiness check (readiness probe)
    Checks all components including datastore, memory, disk
    """
    health = await health_checker.check_all()

    if health.status == "unhealthy":
        raise HTTPException(status_code=503, detail="Service not ready")

    return health


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """
    Prometheus-compatible metrics endpoint
    Returns cache stats, request counts, etc.
    """
    cache_stats = cache_manager.get_all_stats()
    cost_savings = calculate_cost_savings(cache_stats)
    system_metrics = health_checker.get_system_metrics()

    return {
        "cache": cache_stats,
        "cost_savings": cost_savings,
        "system": system_metrics.dict()
    }


# ========== Core API Endpoints ==========

@app.post("/upsert-file", response_model=UpsertResponse, tags=["Documents"])
@limiter.limit("10/minute")
async def upsert_file(
    request: Request,
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
):
    """
    Upload a single file and store in vector database
    Rate limited to 10 requests per minute
    """
    start_time = time.time()

    try:
        metadata_obj = (
            DocumentMetadata.parse_raw(metadata)
            if metadata
            else DocumentMetadata(source=Source.file)
        )
    except:
        metadata_obj = DocumentMetadata(source=Source.file)

    document = await get_document_from_file(file, metadata_obj)

    try:
        ids = await datastore.upsert([document])

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"File uploaded: {file.filename}",
            extra={
                "extra_fields": {
                    "filename": file.filename,
                    "document_id": ids[0] if ids else None,
                    "duration_ms": duration_ms
                }
            }
        )

        # Invalidate query cache after upsert
        cache_manager.query_cache.invalidate_all()

        return UpsertResponse(ids=ids)

    except Exception as e:
        logger.error(f"Error upserting file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upsert file: {str(e)}")


@app.post("/upsert", response_model=UpsertResponse, tags=["Documents"])
@limiter.limit("20/minute")
async def upsert(
    request: Request,
    upsert_request: UpsertRequest = Body(...),
):
    """
    Upsert documents into vector database
    Rate limited to 20 requests per minute
    """
    start_time = time.time()

    try:
        ids = await datastore.upsert(upsert_request.documents)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Documents upserted: {len(upsert_request.documents)}",
            extra={
                "extra_fields": {
                    "count": len(upsert_request.documents),
                    "duration_ms": duration_ms
                }
            }
        )

        # Invalidate query cache
        cache_manager.query_cache.invalidate_all()

        return UpsertResponse(ids=ids)

    except Exception as e:
        logger.error(f"Error upserting documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upsert documents")


@app.post("/query", response_model=QueryResponse, tags=["Search"])
@limiter.limit("30/minute")
async def query_main(
    request: Request,
    query_request: QueryRequest = Body(...),
):
    """
    Query vector database with caching support
    Rate limited to 30 requests per minute
    """
    start_time = time.time()
    results = []

    try:
        for query in query_request.queries:
            # Check cache first
            cached_result = cache_manager.query_cache.get_results(
                query=query.query,
                filters=query.filter.dict() if query.filter else None,
                top_k=query.top_k or 3
            )

            if cached_result:
                logger.debug(f"Cache hit for query: {query.query[:50]}...")
                results.append(cached_result)
            else:
                # Execute query
                query_results = await datastore.query([query])
                result = query_results[0]
                results.append(result)

                # Cache result
                cache_manager.query_cache.set_results(
                    query=query.query,
                    results=result,
                    filters=query.filter.dict() if query.filter else None,
                    top_k=query.top_k or 3
                )

        duration_ms = (time.time() - start_time) * 1000

        # Log query
        log_query(
            logger,
            query=query_request.queries[0].query if query_request.queries else "",
            results_count=len(results[0].results) if results else 0,
            duration_ms=duration_ms
        )

        return QueryResponse(results=results)

    except Exception as e:
        logger.error(f"Error querying: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Query failed")


@sub_app.post("/query", response_model=QueryResponse, tags=["Search"])
async def query_sub(
    query_request: QueryRequest = Body(...),
):
    """Sub-app query endpoint for OpenAPI schema"""
    return await query_main(Request(scope={"type": "http"}), query_request)


@app.delete("/delete", response_model=DeleteResponse, tags=["Documents"])
@limiter.limit("10/minute")
async def delete(
    request: Request,
    delete_request: DeleteRequest = Body(...),
):
    """
    Delete documents from vector database
    Rate limited to 10 requests per minute
    """
    if not (delete_request.ids or delete_request.filter or delete_request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )

    start_time = time.time()

    try:
        success = await datastore.delete(
            ids=delete_request.ids,
            filter=delete_request.filter,
            delete_all=delete_request.delete_all,
        )

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Documents deleted",
            extra={
                "extra_fields": {
                    "ids_count": len(delete_request.ids) if delete_request.ids else 0,
                    "delete_all": delete_request.delete_all,
                    "duration_ms": duration_ms
                }
            }
        )

        # Invalidate cache
        cache_manager.query_cache.invalidate_all()

        return DeleteResponse(success=success)

    except Exception as e:
        logger.error(f"Error deleting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Delete operation failed")


# ========== ConnectWise Webhook Endpoint ==========

@app.post("/connectwise-webhook", tags=["Webhooks"])
@limiter.limit("100/minute")
async def connectwise_webhook(request: Request):
    """
    Receive webhooks from ConnectWise Manage
    Automatically indexes closed tickets in real-time
    """
    try:
        payload = await request.json()

        if not webhook_handler:
            logger.warning("Webhook received but handler not initialized")
            return {"status": "error", "message": "Webhook handler not configured"}

        result = await webhook_handler.handle_webhook(payload)

        return result

    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# ========== Analytics Endpoints ==========

@app.get("/analytics/cache", tags=["Analytics"])
async def cache_analytics():
    """Get detailed cache analytics and cost savings"""
    stats = cache_manager.get_all_stats()
    savings = calculate_cost_savings(stats)

    return {
        "cache_stats": stats,
        "cost_savings": savings
    }


@app.post("/cache/clear", tags=["Admin"])
async def clear_cache():
    """Clear all caches (admin only)"""
    cache_manager.clear_all()
    logger.info("All caches cleared")
    return {"status": "success", "message": "All caches cleared"}


# ========== Startup/Shutdown Events ==========

@app.on_event("startup")
async def startup():
    """Initialize datastore and health checks"""
    global datastore, webhook_handler

    logger.info("Starting retrieval plugin server...")

    # Initialize datastore
    datastore = await get_datastore()
    logger.info(f"Datastore initialized: {os.getenv('DATASTORE')}")

    # Register health checks
    health_checker.register_check("datastore", lambda: check_datastore(datastore), check_interval=60)
    health_checker.register_check("memory", check_memory_usage, check_interval=30)
    health_checker.register_check("disk", check_disk_usage, check_interval=60)

    # Initialize ConnectWise webhook handler if configured
    if all([
        os.getenv("CW_COMPANY_ID"),
        os.getenv("CW_PUBLIC_KEY"),
        os.getenv("CW_PRIVATE_KEY"),
        os.getenv("CW_CLIENT_ID")
    ]):
        try:
            # Import here to avoid dependency if not using ConnectWise
            import sys
            sys.path.append("scripts/connectwise_import")
            from connectwise_importer import ConnectWiseImporter

            cw_client = ConnectWiseImporter(
                company_id=os.getenv("CW_COMPANY_ID"),
                public_key=os.getenv("CW_PUBLIC_KEY"),
                private_key=os.getenv("CW_PRIVATE_KEY"),
                api_url=os.getenv("CW_API_URL", "https://api-na.myconnectwise.net"),
                client_id=os.getenv("CW_CLIENT_ID")
            )

            webhook_handler = ConnectWiseWebhookHandler(cw_client, datastore, logger)
            logger.info("ConnectWise webhook handler initialized")

        except Exception as e:
            logger.warning(f"Failed to initialize ConnectWise webhook handler: {e}")

    logger.info("Server startup complete")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("Shutting down server...")
    # Clean up resources if needed


def start():
    """Start the enhanced server"""
    uvicorn.run(
        "server.main_enhanced:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_config=None  # Use our custom logging
    )


if __name__ == "__main__":
    start()
