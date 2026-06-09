import uuid
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, status, APIRouter
from pydantic import BaseModel, Field

from swarm_core.orchestrator import CEOOrchestrator
from swarm_core.crypto_utils import derive_key, decrypt_pii_fields

# Global Orchestrator Instance
orchestrator = CEOOrchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    import logging
    logger = logging.getLogger("CEOOrchestrator")

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
    
    # Publish verification ping
    await orchestrator.broker.publish("system:verify", {"status": "HEALTHY", "broker": "UP"})
    yield
    # Shutdown: Clean connection resources
    if hasattr(app.state, "verification_task"):
        app.state.verification_task.cancel()
    await orchestrator.shutdown()

app = FastAPI(
    title="Multi-Agent Swarm Framework API",
    description="Production-Grade Swarm coordination engine with Zero-Knowledge Local Cryptography and Self-Healing layout pipelines.",
    version="1.0.0",
    lifespan=lifespan
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

# Include the router in the app
app.include_router(router)
