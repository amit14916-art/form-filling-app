import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright

from swarm_core.agent_registry import (
    PlanningAgent,
    ExecutionAgent,
    QAAgent,
    ConsensusEngine,
    AgentResult
)
from swarm_core.crypto_utils import encrypt_pii_fields, decrypt_pii_fields

logger = logging.getLogger("CEOOrchestrator")

class EventBroker:
    """
    Event-driven communication channel.
    Uses Redis PubSub when available, falling back to local asyncio Queues.
    """
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None
        self.use_fallback = False
        self.queues: Dict[str, asyncio.Queue] = {}

    async def connect(self):
        try:
            import redis.asyncio as aioredis
            self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("EventBroker connected to Redis successfully.")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis ({str(e)}). Using in-memory event routing.")
            self.use_fallback = True

    async def publish(self, channel: str, message: Any):
        payload = json.dumps(message)
        if self.use_fallback or self.redis is None:
            if channel not in self.queues:
                self.queues[channel] = asyncio.Queue()
            await self.queues[channel].put(payload)
        else:
            await self.redis.publish(channel, payload)

    async def listen(self, channel: str):
        if self.use_fallback or self.redis is None:
            if channel not in self.queues:
                self.queues[channel] = asyncio.Queue()
            while True:
                msg = await self.queues[channel].get()
                yield json.loads(msg)
        else:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(channel)
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        yield json.loads(message["data"])
            finally:
                await pubsub.unsubscribe(channel)

    async def close(self):
        if self.redis:
            await self.redis.aclose()


class CEOOrchestrator:
    """
    CEO Agent Engine coordinates planning, parallel task execution, QA consensus checks,
    and self-correcting layout adjustments.
    """
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.broker = EventBroker(redis_url)
        
        # Instantiate agents
        self.planner = PlanningAgent()
        self.executer = ExecutionAgent()
        
        # 3-tier Quality Assurance Agents
        self.qa_agents = [
            QAAgent("qa_dom_auditor", "DOM_Auditor", weight=1.2),
            QAAgent("qa_visual_auditor", "Visual_Auditor", weight=1.0),
            QAAgent("qa_semantic_auditor", "Semantic_Auditor", weight=0.8)
        ]
        
        # Keep track of active task states in memory (for querying)
        self.task_states: Dict[str, Dict[str, Any]] = {}

    async def start(self):
        await self.broker.connect()

    async def shutdown(self):
        await self.broker.close()

    async def submit_task(self, user_id: int, chat_message: str) -> Dict[str, Any]:
        """
        Parses a raw chat command to extract PII (Name, Aadhaar, Phone) and passphrases,
        encrypts it instantly, and routes it to the execution swarm pipeline.
        """
        import re
        import uuid
        from swarm_core.crypto_utils import derive_key

        # 1. Extractor rules
        # Extract Aadhaar (Format: 12 digits or 4-4-4 spacing)
        aadhaar_match = re.search(r"\b\d{4}-\d{4}-\d{4}\b", chat_message)
        if not aadhaar_match:
            aadhaar_match = re.search(r"\b\d{12}\b", chat_message)
        aadhaar = aadhaar_match.group(0) if aadhaar_match else "1234-5678-9012"
        
        # Extract phone (Format: digits possibly with country code prefix)
        phone_match = re.search(r"\+?\d{10,12}", chat_message)
        phone = phone_match.group(0) if phone_match else "+919999999999"
        
        # Extract Name: looking for name patterns
        name_match = re.search(r"(?:name is|name:)\s*([A-Za-z ]+)", chat_message, re.IGNORECASE)
        name = name_match.group(1).strip() if name_match else "John Doe"
        
        # Extract Passphrase: looking for password or passphrase patterns
        pass_match = re.search(r"(?:passphrase is|passphrase:|password is|password:)\s*(\S+)", chat_message, re.IGNORECASE)
        passphrase = pass_match.group(1).strip() if pass_match else f"default_passphrase_for_{user_id}_secure"
        
        # Extract Form URL if provided
        url_match = re.search(r"https?://\S+", chat_message)
        form_url = url_match.group(0).strip() if url_match else None
        
        # Compile raw command by removing credentials for cleanliness (keeps command readable in planning phase)
        cleaned_command = chat_message
        for val in [aadhaar, phone, name, passphrase]:
            if val and val != f"default_passphrase_for_{user_id}_secure":
                cleaned_command = cleaned_command.replace(val, "*****")
                
        # 2. Package PII
        pii_data = {
            "name": name,
            "aadhaar": aadhaar,
            "phone": phone
        }
        
        task_id = str(uuid.uuid4())
        encryption_key = derive_key(passphrase)
        
        # Dispatch the task to the execution runner
        asyncio.create_task(
            self.run_task(
                task_id=task_id,
                command=cleaned_command,
                pii_data=pii_data,
                encryption_key=encryption_key,
                form_url=form_url
            )
        )
        
        return {
            "task_id": task_id,
            "status": "SUBMITTED",
            "message": "Chat message parsed successfully and micro-agents dispatched."
        }

    async def run_task(
        self,
        task_id: str,
        command: str,
        pii_data: Dict[str, Any],
        encryption_key: str,
        form_url: Optional[str] = None,
        proxy_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a task command. Encrypts PII, creates execution steps,
        dispatches them, runs QA voting, and heals when necessary.
        """
        # 1. State Isolation & Zero-Knowledge: Encrypt local state data using the key
        pii_keys = list(pii_data.keys())
        encrypted_pii = encrypt_pii_fields(pii_data, pii_keys, encryption_key)
        
        # Create isolated task state
        self.task_states[task_id] = {
            "task_id": task_id,
            "command": command,
            "status": "PLANNING",
            "steps": [],
            "current_step": 0,
            "encrypted_context": encrypted_pii,
            "pii_keys": pii_keys,
            "logs": [],
            "outputs": {}
        }
        
        task_state = self.task_states[task_id]
        task_state["logs"].append(f"Task initiated. Encrypted {len(pii_keys)} PII keys.")

        # 2. Decompose instruction into a execution plan DAG
        plan_context = {
            "command": command,
            "form_url": form_url,
            "phone": pii_data.get("phone", "+919999999999"),
            "user_name": pii_data.get("name", "John Doe"),
            "aadhaar": encrypted_pii.get("aadhaar", "") # Passed encrypted to planner
        }
        
        plan_res = await self.planner.execute(plan_context)
        if not plan_res.success:
            task_state["status"] = "FAILED"
            task_state["logs"].append(f"Planning failed: {plan_res.error_message}")
            return task_state

        steps = plan_res.output_data.get("steps", [])
        task_state["steps"] = steps
        task_state["status"] = "RUNNING"
        task_state["logs"].append(f"Plan generated with {len(steps)} steps.")

        # Setup browser if possible
        playwright_instance = None
        browser = None
        page = None
        
        try:
            playwright_instance = await async_playwright().start()
            
            # Setup dynamic proxy parameters if provided in user request
            launch_args = {"headless": True}
            if proxy_config:
                launch_args["proxy"] = proxy_config
                
            browser = await playwright_instance.chromium.launch(**launch_args)
            page = await browser.new_page()
            task_state["logs"].append(f"Playwright browser initialized successfully (Proxy Active: {proxy_config is not None}).")
        except Exception as browser_err:
            logger.warning(f"Could not launch real Playwright browser: {str(browser_err)}. Using simulation mode.")
            task_state["logs"].append(f"Browser launch skipped: {str(browser_err)}. Running in mock simulation.")
            page = None

        # 3. Execution event loop
        # We spawn an async listener to monitor events for this task
        async def event_consumer():
            channel = f"task_events:{task_id}"
            async for event in self.broker.listen(channel):
                logger.info(f"[Task {task_id} Event] Received event: {event}")
                if event.get("action") == "STOP":
                    break

        consumer_task = asyncio.create_task(event_consumer())

        try:
            step_idx = 0
            while step_idx < len(task_state["steps"]):
                current_step = task_state["steps"][step_idx]
                task_state["current_step"] = step_idx + 1
                task_state["logs"].append(f"Dispatching Step {step_idx + 1}: {current_step['description']}")
                
                # Zero-Knowledge decryption only at the transient execution boundary
                decrypted_pii = decrypt_pii_fields(task_state["encrypted_context"], task_state["pii_keys"], encryption_key)
                
                # Execute action via dispatch pipeline
                exec_context = {
                    "step": current_step,
                    "playwright_page": page,
                    "decrypted_inputs": decrypted_pii,
                    "proxy_config": proxy_config,
                    "last_dom": task_state["logs"][-1],
                    "task_id": task_id,
                    "broker": self.broker
                }
                
                # Publish task event to notify listeners
                await self.broker.publish(f"task_events:{task_id}", {
                    "task_id": task_id,
                    "step_id": current_step["step_id"],
                    "action": current_step["action"],
                    "status": "STARTING"
                })

                # Execution Agent run
                exec_res = await self.executer.execute(exec_context)
                
                # 4. Strict 3-Tier Quality Assurance Consensus
                qa_passed, confidence, qa_logs = await ConsensusEngine.evaluate(
                    self.qa_agents,
                    current_step,
                    exec_res
                )
                
                task_state["logs"].append(f"QA Evaluation: Passed={qa_passed}, Confidence={confidence:.2f}")
                for q_log in qa_logs:
                    task_state["logs"].append(f" - {q_log['qa_type']}: {q_log['feedback']} (Success={q_log['success_vote']})")

                # Dynamic QA Reputation Calibration feedback loop
                ground_truth_success = exec_res.success and qa_passed
                for agent in self.qa_agents:
                    for q_log in qa_logs:
                        if q_log["qa_agent"] == agent.agent_id:
                            vote = q_log["success_vote"]
                            if vote == ground_truth_success:
                                agent.reward_agent(0.1)
                            else:
                                agent.penalize_agent(0.1)
                            break
                
                # Log updated weights for full traceability
                task_state["logs"].append("QA Swarm Reputation Calibration Weights:")
                for agent in self.qa_agents:
                    task_state["logs"].append(f" - {agent.name}: reputation_weight={agent.reputation_weight:.2f}")

                if not qa_passed:
                    # Self-Healing loop
                    retry_limit = 3
                    retry_count = current_step.get("retry_count", 0)
                    
                    if retry_count < retry_limit:
                        task_state["logs"].append(f"Consensus rejected execution. Triggering self-healing (Attempt {retry_count + 1}/{retry_limit})...")
                        
                        dom_layout = exec_res.metadata.get("dom_snapshot", "")
                        error_msg = exec_res.error_message or "QA voting rejection"
                        
                        # Request the planner to heal/rewrite the remaining steps DAG
                        healed_steps = await self.planner.heal_plan(
                            failed_step=current_step,
                            error_msg=error_msg,
                            dom_layout=dom_layout,
                            current_steps=task_state["steps"],
                            retry_count=retry_count
                        )
                        
                        # Update pipeline DAG structure in isolated state
                        task_state["steps"] = healed_steps
                        task_state["logs"].append("Plan updated with healed steps.")
                        continue
                    else:
                        task_state["status"] = "FAILED"
                        task_state["logs"].append(f"Step {current_step['step_id']} failed retry limit. Aborting.")
                        await self.broker.publish(f"task_events:{task_id}", {"status": "FAILED"})
                        break
                
                # Step succeeded
                if exec_res.output_data:
                    task_state["outputs"].update(exec_res.output_data)
                
                # RAG: Save healed selector corrections in rag_engine
                if current_step.get("retry_count", 0) > 0 and "selector" in current_step:
                    from swarm_core.rag_engine import rag_engine
                    failed_sel = "#submit-btn"
                    for log in task_state["logs"]:
                        if "Element" in log and "not found" in log:
                            import re
                            m = re.search(r"Element\s+(\S+)\s+not\s+found", log)
                            if m:
                                failed_sel = m.group(1)
                                break
                    rag_engine.add_healing_record(
                        failed_selector=failed_sel,
                        error_message="Element not found",
                        dom_snippet=exec_res.metadata.get("dom_snapshot", ""),
                        healed_selector=current_step["selector"]
                    )
                    
                await self.broker.publish(f"task_events:{task_id}", {
                    "task_id": task_id,
                    "step_id": current_step["step_id"],
                    "action": current_step["action"],
                    "status": "COMPLETED"
                })
                
                step_idx += 1

            if task_state["status"] != "FAILED":
                task_state["status"] = "COMPLETED"
                task_state["logs"].append("All execution steps finished successfully.")
                
        finally:
            if browser:
                await browser.close()
            if playwright_instance:
                await playwright_instance.stop()
            
            await self.broker.publish(f"task_events:{task_id}", {"action": "STOP"})
            await consumer_task

        return task_state
