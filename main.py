import uuid
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, status, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
import asyncio

from swarm_core.orchestrator import CEOOrchestrator
from swarm_core.crypto_utils import derive_key, decrypt_pii_fields
from database.db import init_db
from auth.auth import router as auth_router
from routers.profile import router as profile_router
from routers.eligibility import router as eligibility_router
from routers.dashboard import router as dashboard_router
from routers.payment import router as payment_router

import os
logger = logging.getLogger("SarkariSwarm")

# Global Orchestrator Instance
orchestrator = CEOOrchestrator(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    import logging
    logger = logging.getLogger("CEOOrchestrator")

    # Startup: Initialize Database tables
    await init_db()

    # Startup: Initialize Redis broker connection
    await orchestrator.start()
    
    # Startup verification loop to ensure background event broker task is active
    async def global_verification_listener():
        try:
            logger.info("Initializing global verification listener task on event broker...")
            async for event in orchestrator.broker.listen("system:verify"):
                logger.info(f"[Global Verification Listener] Received heartbeat/event: {event}")
        except Exception as err:
            logger.error(f"[Global Verification Listener] Stopped with error: {err}")

    # Launch concurrently in async task loop
    app.state.verification_task = asyncio.create_task(global_verification_listener())
    
    # Launch background job scraper loop
    app.state.scraper_task = asyncio.create_task(job_scraper_background_loop())
    
    # Publish verification ping
    await orchestrator.broker.publish("system:verify", {"status": "HEALTHY", "broker": "UP"})
    yield
    # Shutdown: Clean connection resources
    if hasattr(app.state, "verification_task"):
        app.state.verification_task.cancel()
    if hasattr(app.state, "scraper_task"):
        app.state.scraper_task.cancel()
    await orchestrator.shutdown()

app = FastAPI(
    title="Multi-Agent Swarm Framework API",
    description="Production-Grade Swarm coordination engine with Zero-Knowledge Local Cryptography and Self-Healing layout pipelines.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# APIRouter with prefix /api/v1/chat-gateway
router = APIRouter(prefix="/api/v1/chat-gateway")

# Models
class SubmitTaskRequest(BaseModel):
    user_id: int = Field(..., example=42)
    chat_message: str = Field(..., example="Fill my exam form. My name is Alice, Aadhaar is 9876-5432-1098, phone is +919999999999, passphrase is super_secure_passphrase_123")

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    current_step: int
    total_steps: int
    logs: list[str]
    outputs: Dict[str, Any]

class EncryptedStateResponse(BaseModel):
    task_id: str
    encrypted_context: Dict[str, Any]
    pii_keys: list[str]

# Async event monitor fallback loop
async def event_monitor_loop(task_id: str):
    try:
        channel = f"task_events:{task_id}"
        async for event in orchestrator.broker.listen(channel):
            if task_id in orchestrator.task_states:
                state = orchestrator.task_states[task_id]
                state["logs"].append(
                    f"[Async Monitor] Broker Event on step {event.get('step_id', '?')}: "
                    f"Action '{event.get('action', '?')}' status is {event.get('status', '?')}"
                )
            if event.get("action") == "STOP" or event.get("status") in ("COMPLETED", "FAILED"):
                break
    except Exception:
        pass

# Endpoints under /api/v1/chat-gateway
@router.post("/submit", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_task(payload: SubmitTaskRequest, background_tasks: BackgroundTasks):
    """
    Submits a raw human chat message to the Swarm.
    Instantly extracts and encrypts PII, then schedules background execution.
    """
    try:
        result = await orchestrator.submit_task(payload.user_id, payload.chat_message)
        task_id = result["task_id"]

        # Run background event monitor loop
        background_tasks.add_task(event_monitor_loop, task_id)

        return TaskResponse(
            task_id=task_id,
            status=result["status"],
            message=result["message"]
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task submission failed: {str(err)}"
        )

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Queries execution progress, real-time logging audit, and pipeline outputs.
    """
    try:
        if task_id not in orchestrator.task_states:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Task ID {task_id} not found."
            )
        
        state = orchestrator.task_states[task_id]
        return TaskStatusResponse(
            task_id=task_id,
            status=state["status"],
            current_step=state["current_step"],
            total_steps=len(state["steps"]),
            logs=state["logs"],
            outputs=state["outputs"]
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error querying task status: {str(err)}"
        )

@router.get("/tasks/{task_id}/encrypted-state", response_model=EncryptedStateResponse)
async def get_encrypted_state(task_id: str):
    """
    Zero-Knowledge check: Returns the stored database record context to prove
    that the user's PII is fully encrypted in local storage.
    """
    try:
        if task_id not in orchestrator.task_states:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task ID {task_id} not found."
            )
        
        state = orchestrator.task_states[task_id]
        return EncryptedStateResponse(
            task_id=task_id,
            encrypted_context=state["encrypted_context"],
            pii_keys=state["pii_keys"]
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error retrieving encrypted state: {str(err)}"
        )

@router.post("/tasks/{task_id}/decrypt-output")
async def decrypt_output(task_id: str, passphrase: str):
    """
    Utility endpoint to decrypt encrypted states for display, given the correct passphrase.
    """
    try:
        if task_id not in orchestrator.task_states:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task ID {task_id} not found."
            )
        
        state = orchestrator.task_states[task_id]
        encryption_key = derive_key(passphrase)
        decrypted_pii = decrypt_pii_fields(
            state["encrypted_context"], 
            state["pii_keys"], 
            encryption_key
        )
        return {
            "task_id": task_id,
            "decrypted_context": decrypted_pii
        }
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt state. Invalid passphrase or corrupted data."
        )

class SubmitOtpRequest(BaseModel):
    otp: str = Field(..., example="123456")

@router.post("/tasks/{task_id}/otp")
async def submit_otp(task_id: str, payload: SubmitOtpRequest):
    """
    Webhook channel to receive OTP from external signals and forward to the active execution thread.
    """
    try:
        # Publish event to the task_otp channel
        await orchestrator.broker.publish(f"task_otp:{task_id}", {"otp": payload.otp})
        
        # Log it in task state if task exists
        if task_id in orchestrator.task_states:
            orchestrator.task_states[task_id]["logs"].append(f"[Webhook] Received external OTP signal: {payload.otp}")
            
        return {"status": "SUCCESS", "message": "OTP event dispatched to execution worker."}
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process OTP webhook: {str(err)}"
        )

# Include the routers in the app
app.include_router(router)

# Job Alerts Router with WebSockets support
jobs_router = APIRouter(prefix="/api/v1/jobs")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()
latest_jobs_cache = []

FALLBACK_JOBS = [
    {
        "title": "UPSC Civil Services Examination 2026 - Apply Online for 1056 Posts",
        "link": "https://upsconline.nic.in",
        "date": "2026-06-16T12:00:00Z",
        "category": "Central Jobs"
    },
    {
        "title": "SSC Combined Graduate Level (CGL) 2026 - 15000+ Vacancies Announced",
        "link": "https://ssc.gov.in",
        "date": "2026-06-15T10:30:00Z",
        "category": "Central Jobs"
    },
    {
        "title": "BPSC 71st Civil Services (Pre) Exam 2026 - Notification Out",
        "link": "https://bpsc.bih.nic.in",
        "date": "2026-06-14T08:15:00Z",
        "category": "State Jobs"
    },
    {
        "title": "IBPS Bank PO / MT XIV Recruitment 2026 - Apply Online for 4455 Posts",
        "link": "https://www.ibps.in",
        "date": "2026-06-12T14:20:00Z",
        "category": "Bank Jobs"
    },
    {
        "title": "RRB NTPC Graduate & Under Graduate Posts 2026 - 11558 Openings",
        "link": "https://www.rrbcdg.gov.in",
        "date": "2026-06-10T09:00:00Z",
        "category": "Railway Jobs"
    }
]
   
async def fetch_rss_jobs() -> List[dict]:
    try:
        url = "https://www.freejobalert.com/feed/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return []
            
        root = ET.fromstring(response.content)
        jobs = []
        for item in root.findall(".//item")[:15]:
            title = item.find("title").text
            link = item.find("link").text
            
            # Extract category
            category = "Govt Jobs"
            title_lower = title.lower()
            if "bank" in title_lower or "ibps" in title_lower or "sbi" in title_lower:
                category = "Bank Jobs"
            elif "ssc" in title_lower or "upsc" in title_lower:
                category = "Central Jobs"
            elif "psc" in title_lower or "state" in title_lower:
                category = "State Jobs"
            elif "railway" in title_lower or "rrb" in title_lower:
                category = "Railway Jobs"
                
            # Parse publication date
            pub_date_raw = item.find("pubDate").text
            try:
                pub_date = datetime.strptime(pub_date_raw[:25].strip(), "%a, %d %b %Y %H:%M:%S").isoformat() + "Z"
            except Exception:
                pub_date = datetime.utcnow().isoformat() + "Z"
                
            jobs.append({
                "title": title,
                "link": link,
                "date": pub_date,
                "category": category
            })
        return jobs
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        return []

async def job_scraper_background_loop():
    global latest_jobs_cache
    logger.info("Initializing latest jobs cache from FreeJobAlert...")
    initial_jobs = await fetch_rss_jobs()
    if initial_jobs:
        latest_jobs_cache = initial_jobs
    else:
        latest_jobs_cache = FALLBACK_JOBS.copy()
        
    while True:
        try:
            await asyncio.sleep(120)  # poll every 2 minutes
            logger.info("Polling FreeJobAlert feed for updates...")
            new_fetched = await fetch_rss_jobs()
            if not new_fetched:
                continue
                
            existing_links = {j["link"] for j in latest_jobs_cache}
            new_items_found = []
            
            for item in reversed(new_fetched): # oldest to newest
                if item["link"] not in existing_links:
                    logger.info(f"Detected new job notification: {item['title']}")
                    latest_jobs_cache.insert(0, item)
                    new_items_found.append(item)
                    
            if len(latest_jobs_cache) > 50:
                latest_jobs_cache = latest_jobs_cache[:50]
                
            # Broadcast new items
            for new_job in new_items_found:
                await manager.broadcast({
                    "type": "new_job",
                    "job": new_job
                })
        except Exception as e:
            logger.error(f"Error in job scraper background worker: {e}")

@jobs_router.get("/latest")
async def get_latest_jobs():
    global latest_jobs_cache
    if not latest_jobs_cache:
        return FALLBACK_JOBS
    return latest_jobs_cache

@jobs_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

app.include_router(jobs_router)

@app.websocket("/ws/{task_id}")
async def websocket_task_status(websocket: WebSocket, task_id: str):
    await websocket.accept()
    logger.info(f"[WebSocket] Client connected for task_id: {task_id}")
    try:
        channel = f"task_events:{task_id}"
        # Start listening to events from the EventBroker
        async for event in orchestrator.broker.listen(channel):
            logger.info(f"[WebSocket task_id={task_id}] Sending event: {event}")
            await websocket.send_json(event)
            # Do not close on payment_pending because the payment callback will push the submitted status
            if event.get("status") in ("submitted", "failed"):
                break
    except WebSocketDisconnect:
        logger.info(f"[WebSocket] Client disconnected for task_id: {task_id}")
    except Exception as e:
        logger.error(f"[WebSocket] Error in task status websocket: {e}")

from fastapi.responses import StreamingResponse
from database.db import get_db
from database.models import User
from auth.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
import json

@app.get("/eligibility/check")
async def compatibility_check_eligibility(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from routers.eligibility import get_eligible_exams
    return await get_eligible_exams(current_user, db)

class CompatibilityApplyRequest(BaseModel):
    passphrase: Optional[str] = None

@app.post("/apply/{exam_id}")
async def compatibility_apply_exam(
    exam_id: str,
    payload: CompatibilityApplyRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from routers.eligibility import apply_exam, ApplyRequest
    request_payload = ApplyRequest(passphrase=payload.passphrase)
    return await apply_exam(exam_id, request_payload, background_tasks, current_user, db)

@app.get("/apply/status/{task_id}")
async def compatibility_sse_task_status(task_id: str):
    async def sse_event_generator():
        channel = f"task_events:{task_id}"
        yield f"data: {json.dumps({'status': 'initializing', 'message': 'Connected to progress stream...'})}\n\n"
        try:
            async for event in orchestrator.broker.listen(channel):
                logger.info(f"[SSE task_id={task_id}] Sending event: {event}")
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("status") in ("submitted", "failed"):
                    break
        except Exception as err:
            logger.error(f"[SSE task_id={task_id}] Error: {err}")
            yield f"data: {json.dumps({'status': 'failed', 'message': str(err)})}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")

# Include Phase 1 and Phase 2 routers
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(eligibility_router)
app.include_router(dashboard_router)
app.include_router(payment_router, prefix="/api/v1")
app.include_router(payment_router)

# Serve uploads StaticFiles
import os
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Serve static frontend files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

