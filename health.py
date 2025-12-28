# bot/health.py
"""
Health check endpoint for Docker/Kubernetes
"""

from fastapi import FastAPI, Response
import redis
import psycopg2
from datetime import datetime

app = FastAPI(title="ShortSync Health Check")

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/Kubernetes"""
    
    checks = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check Redis
    try:
        r = redis.Redis(host="redis", port=6379, decode_responses=True)
        r.ping()
        checks["checks"]["redis"] = "healthy"
    except Exception as e:
        checks["checks"]["redis"] = f"unhealthy: {str(e)}"
        checks["status"] = "unhealthy"
    
    # Check Database
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="shortsync",
            user="shortsync",
            password=os.getenv("DB_PASSWORD")
        )
        conn.close()
        checks["checks"]["database"] = "healthy"
    except Exception as e:
        checks["checks"]["database"] = f"unhealthy: {str(e)}"
        checks["status"] = "unhealthy"
    
    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        checks["checks"]["disk_space"] = {
            "total_gb": total // (2**30),
            "used_gb": used // (2**30),
            "free_gb": free // (2**30),
            "free_percent": (free / total) * 100
        }
    except Exception as e:
        checks["checks"]["disk_space"] = f"error: {str(e)}"
    
    return checks

@app.get("/ready")
async def ready_check():
    """Readiness check"""
    return {"status": "ready", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ShortSync Pro",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
