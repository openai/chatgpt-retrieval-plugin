"""
Health check and monitoring services
Provides health/readiness endpoints and system metrics
"""
import time
import os
import psutil
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status of a single component"""
    status: HealthStatus
    message: Optional[str] = None
    response_time_ms: Optional[float] = None
    last_check: datetime
    metadata: Dict[str, Any] = {}


class SystemHealth(BaseModel):
    """Overall system health status"""
    status: HealthStatus
    timestamp: datetime
    uptime_seconds: float
    components: Dict[str, ComponentHealth]
    metadata: Dict[str, Any] = {}


class SystemMetrics(BaseModel):
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    process_count: int
    thread_count: int


class HealthChecker:
    """
    Manages health checks for various system components
    """

    def __init__(self):
        self.start_time = time.time()
        self.checks = {}
        self.last_check_results = {}

    def register_check(self, name: str, check_func, check_interval: int = 60):
        """
        Register a health check function

        Args:
            name: Name of the component
            check_func: Async function that returns (status, message, metadata)
            check_interval: How often to run check (seconds)
        """
        self.checks[name] = {
            "func": check_func,
            "interval": check_interval,
            "last_run": 0
        }

    async def check_component(self, name: str) -> ComponentHealth:
        """
        Check health of a specific component

        Args:
            name: Component name

        Returns:
            ComponentHealth object
        """
        if name not in self.checks:
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"Unknown component: {name}",
                last_check=datetime.utcnow()
            )

        check = self.checks[name]
        current_time = time.time()

        # Use cached result if check was recent
        if (current_time - check["last_run"]) < check["interval"]:
            if name in self.last_check_results:
                return self.last_check_results[name]

        # Run the check
        start = time.time()
        try:
            status, message, metadata = await check["func"]()
            response_time = (time.time() - start) * 1000

            result = ComponentHealth(
                status=status,
                message=message,
                response_time_ms=round(response_time, 2),
                last_check=datetime.utcnow(),
                metadata=metadata or {}
            )

        except Exception as e:
            result = ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                last_check=datetime.utcnow()
            )

        # Cache result
        check["last_run"] = current_time
        self.last_check_results[name] = result

        return result

    async def check_all(self) -> SystemHealth:
        """
        Check all registered components

        Returns:
            SystemHealth with status of all components
        """
        component_results = {}

        for name in self.checks.keys():
            component_results[name] = await self.check_component(name)

        # Determine overall status
        statuses = [c.status for c in component_results.values()]

        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        uptime = time.time() - self.start_time

        return SystemHealth(
            status=overall_status,
            timestamp=datetime.utcnow(),
            uptime_seconds=round(uptime, 2),
            components=component_results,
            metadata=self.get_system_metrics().dict()
        )

    def get_system_metrics(self) -> SystemMetrics:
        """Get current system resource metrics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        process = psutil.Process()

        return SystemMetrics(
            cpu_percent=round(cpu_percent, 2),
            memory_percent=round(memory.percent, 2),
            memory_used_mb=round(memory.used / (1024 * 1024), 2),
            memory_available_mb=round(memory.available / (1024 * 1024), 2),
            disk_percent=round(disk.percent, 2),
            disk_used_gb=round(disk.used / (1024 * 1024 * 1024), 2),
            disk_free_gb=round(disk.free / (1024 * 1024 * 1024), 2),
            process_count=len(psutil.pids()),
            thread_count=process.num_threads()
        )


# Health check functions for common components

async def check_openai_api() -> tuple:
    """Check if OpenAI API is accessible"""
    import openai
    import os

    if not os.getenv("OPENAI_API_KEY"):
        return (HealthStatus.UNHEALTHY, "OPENAI_API_KEY not configured", {})

    try:
        # Simple API call to check connectivity
        start = time.time()
        response = await openai.Model.alist()
        duration = (time.time() - start) * 1000

        return (
            HealthStatus.HEALTHY,
            "OpenAI API accessible",
            {"response_time_ms": round(duration, 2), "models_count": len(response.get("data", []))}
        )
    except Exception as e:
        return (HealthStatus.UNHEALTHY, f"OpenAI API error: {str(e)}", {})


async def check_datastore(datastore) -> tuple:
    """Check if datastore is accessible"""
    try:
        # Try a simple query
        from models.models import Query
        start = time.time()

        # Attempt a test query (empty query should be fast)
        await datastore.query([Query(query="test health check", top_k=1)])

        duration = (time.time() - start) * 1000

        return (
            HealthStatus.HEALTHY,
            "Datastore accessible",
            {"response_time_ms": round(duration, 2)}
        )
    except Exception as e:
        return (HealthStatus.UNHEALTHY, f"Datastore error: {str(e)}", {})


async def check_memory_usage() -> tuple:
    """Check if memory usage is acceptable"""
    memory = psutil.virtual_memory()

    if memory.percent > 90:
        status = HealthStatus.UNHEALTHY
        message = "Memory usage critical"
    elif memory.percent > 80:
        status = HealthStatus.DEGRADED
        message = "Memory usage high"
    else:
        status = HealthStatus.HEALTHY
        message = "Memory usage normal"

    return (
        status,
        message,
        {
            "percent": memory.percent,
            "used_gb": round(memory.used / (1024 ** 3), 2),
            "total_gb": round(memory.total / (1024 ** 3), 2)
        }
    )


async def check_disk_usage() -> tuple:
    """Check if disk usage is acceptable"""
    disk = psutil.disk_usage('/')

    if disk.percent > 90:
        status = HealthStatus.UNHEALTHY
        message = "Disk space critical"
    elif disk.percent > 80:
        status = HealthStatus.DEGRADED
        message = "Disk space low"
    else:
        status = HealthStatus.HEALTHY
        message = "Disk space normal"

    return (
        status,
        message,
        {
            "percent": disk.percent,
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "total_gb": round(disk.total / (1024 ** 3), 2)
        }
    )


# Global health checker instance
health_checker = HealthChecker()
