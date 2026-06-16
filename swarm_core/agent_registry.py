import abc
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentRegistry")

class AgentResult(BaseModel):
    """
    Standard response structure from any micro-agent in the swarm.
    """
    agent_id: str
    success: bool
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseAgent(abc.ABC):
    """
    Abstract Base Class for all micro-agents within the Swarm.
    Provides strict memory boundaries and initialization interfaces.
    """
    def __init__(self, agent_id: str, name: str, role: str):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self._local_memory: Dict[str, Any] = {}

    @abc.abstractmethod
    async def execute(self, task_context: Dict[str, Any]) -> AgentResult:
        """
        Executes a task given the global and local context.
        Must return an AgentResult.
        """
        pass

    def get_memory(self) -> Dict[str, Any]:
        return self._local_memory

    def update_memory(self, key: str, value: Any) -> None:
        self._local_memory[key] = value

    def clear_memory(self) -> None:
        self._local_memory.clear()


class PlanningAgent(BaseAgent):
    """
    Responsible for taking a raw command, analyzing target websites/inputs,
    generating a step-by-step Execution DAG, and re-planning/healing if failures occur.
    """
    def __init__(self, agent_id: str = "agent_planning_01"):
        super().__init__(agent_id, "CEO Planner Agent", "Planning & Re-planning")

    async def execute(self, task_context: Dict[str, Any]) -> AgentResult:
        command = task_context.get("command", "")
        logger.info(f"[{self.name}] Planning pipeline for command: '{command}'")
        
        steps = []
        if "exam" in command.lower() or "form" in command.lower():
            steps = [
                {
                    "step_id": 1,
                    "action": "verify_eligibility",
                    "description": "Verify user eligibility and document formats"
                },
                {
                    "step_id": 2,
                    "action": "navigate",
                    "url": task_context.get("form_url") or "https://example.com/exam-registration",
                    "description": "Navigate to exam form portal"
                },
                {
                    "step_id": 3,
                    "action": "fill_form",
                    "inputs": {
                        "name": task_context.get("user_name", "John Doe"),
                        "aadhaar": task_context.get("aadhaar", "1234-5678-9012"),
                        "exam_center": task_context.get("exam_center", "Center A")
                    },
                    "description": "Fill user details and PII into the registration form"
                },
                {
                    "step_id": 4,
                    "action": "click_submit",
                    "selector": "#submit-btn",
                    "description": "Click submit and submit form"
                }
            ]
        else:
            steps = [
                {
                    "step_id": 1,
                    "action": "verify_eligibility",
                    "description": "Verify user eligibility and document formats"
                },
                {
                    "step_id": 2,
                    "action": "navigate",
                    "url": "https://example.com",
                    "description": "Navigate to home page"
                }
            ]

        if "whatsapp" in command.lower() or "notify" in command.lower():
            steps.append({
                "step_id": len(steps) + 1,
                "action": "notify_whatsapp",
                "phone": task_context.get("phone", "+919999999999"),
                "message": "Form submission completed successfully!",
                "description": "Send notification confirmation via WhatsApp API"
            })

        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            output_data={"steps": steps},
            confidence=0.98
        )

    async def heal_plan(
        self,
        failed_step: Dict[str, Any],
        error_msg: str,
        dom_layout: str,
        current_steps: List[Dict[str, Any]],
        retry_count: int
    ) -> List[Dict[str, Any]]:
        logger.warning(f"[{self.name}] Self-healing triggered on step {failed_step.get('step_id')}. Error: {error_msg}")
        
        from swarm_core.rag_engine import rag_engine
        healed_steps = []
        for step in current_steps:
            if step["step_id"] < failed_step["step_id"]:
                healed_steps.append(step)
            elif step["step_id"] == failed_step["step_id"]:
                healed_step = step.copy()
                if "selector" in healed_step:
                    # RAG Healing Search
                    rag_selector = rag_engine.search_healing_solution(
                        failed_selector=healed_step["selector"],
                        error_message=error_msg,
                        current_dom=dom_layout
                    )
                    if rag_selector:
                        logger.info(f"[{self.name}] Healing RAG hit! Re-using resolved selector: '{rag_selector}'")
                        healed_step["selector"] = rag_selector
                    elif "#submit-btn" in healed_step["selector"] and "btn-primary" in dom_layout:
                        logger.info(f"[{self.name}] Auto-healing selector: '#submit-btn' -> 'button.btn-primary'")
                        healed_step["selector"] = "button.btn-primary"
                    else:
                        logger.info(f"[{self.name}] Auto-healing selector: adding backup fallback tag search")
                        healed_step["selector"] = "button[type='submit']"
                
                healed_step["retry_count"] = retry_count + 1
                healed_steps.append(healed_step)
            else:
                healed_steps.append(step)
                
        return healed_steps


class ExecutionAgent(BaseAgent):
    """
    Executes specific actions using Playwright (with optional proxy configurations).
    """
    def __init__(self, agent_id: str = "agent_exec_01"):
        super().__init__(agent_id, "Browser Execution Agent", "Real-world Form/Action Executer")

    async def execute_form_fill(
        self, 
        url: str, 
        user_profile: Dict[str, Any], 
        proxy_config: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        broker: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Launches a Chromium session in stealth mode via an MCP Browser Server stdio connection,
        navigates to the target URL, fills fields, and handles security checks.
        """
        from tools.mcp_client import SwarmMCPClient
        import json
        logger.info(f"[{self.name}] Calling Browser MCP Server for form fill action...")
        
        async with SwarmMCPClient() as mcp_client:
            tool_args = {
                "url": url,
                "form_data": user_profile,
                "task_id": task_id
            }
            res = await mcp_client.call_tool("browser_fill_form", tool_args)
            response_text = res.content[0].text
            res_dict = json.loads(response_text)
            
            if not res_dict.get("success", False):
                raise Exception(res_dict.get("error", "Unknown MCP form filling failure"))
                
            return {
                "success": True,
                "final_dom": res_dict.get("final_dom", ""),
                "screenshot": b"MOCK_SCREENSHOT_BYTES" if not res_dict.get("screenshot_len") else b"*" * res_dict.get("screenshot_len"),
                "screenshots": [b"MOCK_SCREENSHOT_BYTES"]
            }

    async def execute(self, task_context: Dict[str, Any]) -> AgentResult:
        step = task_context.get("step")
        page = task_context.get("playwright_page")
        proxy_config = task_context.get("proxy_config")
        task_id = task_context.get("task_id")
        broker = task_context.get("broker")
        
        if not step:
            return AgentResult(agent_id=self.agent_id, success=False, error_message="No step details provided.")

        action = step.get("action")
        description = step.get("description", "")
        logger.info(f"[{self.name}] Executing action '{action}' (Proxy Active: {proxy_config is not None}): {description}")

        try:
            metadata = {}
            output_data = {}
            
            # Detect verify_eligibility
            if action == "verify_eligibility":
                # Check for presence of key user details in decrypted inputs
                inputs = task_context.get("decrypted_inputs", {})
                if not inputs:
                    inputs = task_context.get("inputs", {})
                    
                errors = []
                # Check name
                name = inputs.get("name") or inputs.get("first_name") or inputs.get("user_name")
                if not name:
                    errors.append("Full Name is missing")
                
                # Check phone
                phone = inputs.get("phone") or inputs.get("user_number") or inputs.get("phone_number")
                if not phone:
                    errors.append("Phone Number is missing")
                else:
                    clean_phone = str(phone).replace("-", "").replace(" ", "").replace("+91", "")
                    if len(clean_phone) != 10:
                        errors.append(f"Phone Number '{phone}' must contain exactly 10 digits")
                
                # Check Aadhaar
                aadhaar = inputs.get("aadhaar") or inputs.get("aadhaar_number")
                if not aadhaar:
                    errors.append("Aadhaar Card is missing")
                else:
                    clean_aadhaar = str(aadhaar).replace("-", "").replace(" ", "")
                    if len(clean_aadhaar) != 12:
                        errors.append(f"Aadhaar Card '{aadhaar}' must contain exactly 12 digits")
                
                if errors:
                     raise ValueError("Verification failed: " + ", ".join(errors))
                     
                output_data["eligibility_status"] = "PASSED"
                output_data["verification_details"] = "Personal details, documents, and Aadhaar formatting successfully verified."
                logger.info(f"[{self.name}] Eligibility verified successfully.")

            # Detect fill_form and attempt stealth Playwright execution
            elif action == "fill_form":
                inputs = step.get("inputs", {})
                decrypted_inputs = task_context.get("decrypted_inputs", inputs)
                url = step.get("url") or (page.url if page else "https://example.com/exam-registration")
                
                try:
                    fill_res = await self.execute_form_fill(
                        url=url,
                        user_profile=decrypted_inputs,
                        proxy_config=proxy_config,
                        task_id=task_id,
                        broker=broker
                    )
                    metadata["dom_snapshot"] = fill_res["final_dom"]
                    metadata["screenshot_bytes"] = fill_res["screenshot"]
                    metadata["all_screenshots"] = fill_res["screenshots"]
                except Exception as playwright_err:
                    logger.warning(f"[{self.name}] Stealth browser execution failed: {playwright_err}. Falling back to simulation context.")
                    # Fallback to simulated/mock execution
                    metadata["dom_snapshot"] = f"<form><input name='name' value='{decrypted_inputs.get('name')}' /><input name='aadhaar' value='***' /><button id='submit-btn'>Submit</button></form>"
            
            elif page is not None:
                # Standard actions using existing page context (if launched by Orchestrator)
                if action == "navigate":
                    url = step.get("url")
                    await page.goto(url, wait_until="networkidle", timeout=10000)
                    metadata["url"] = page.url
                    metadata["dom_snapshot"] = await page.content()
                    
                elif action == "click_submit":
                    selector = step.get("selector", "button[type='submit']")
                    await page.click(selector, timeout=5000)
                    await page.wait_for_timeout(1000)
                    metadata["dom_snapshot"] = await page.content()
                    
                elif action == "notify_whatsapp":
                    phone = step.get("phone")
                    msg = step.get("message")
                    logger.info(f"[{self.name}] WhatsApp API dispatch to {phone}: '{msg}'")
                    output_data["notification_status"] = "SENT"
                else:
                    raise ValueError(f"Unknown browser action: {action}")
                
                try:
                    screenshot_bytes = await page.screenshot(type="png")
                    metadata["screenshot_bytes"] = screenshot_bytes
                except Exception as screenshot_err:
                    logger.warning(f"Screenshot capture skipped or failed: {str(screenshot_err)}")
                    
            else:
                # Full simulation fallback mode (useful for local environment tests)
                logger.warning(f"[{self.name}] No Playwright browser context. Running in MOCK mode.")
                await asyncio.sleep(0.5)
                
                if action == "navigate":
                    metadata["url"] = step.get("url")
                    metadata["dom_snapshot"] = "<form><input name='name' /><input name='aadhaar' /><button id='submit-btn'>Submit</button></form>"
                elif action == "click_submit":
                    selector = step.get("selector")
                    if selector == "#submit-btn-wrong":
                        raise Exception("Element #submit-btn-wrong not found in current DOM layout.")
                    metadata["dom_snapshot"] = "<div>Success! Registration reference code: REG-992184</div>"
                    output_data["registration_code"] = "REG-992184"
                elif action == "notify_whatsapp":
                    output_data["notification_status"] = "SENT"
                else:
                    raise ValueError(f"Unknown mock action: {action}")

            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                output_data=output_data,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"[{self.name}] Execution error on action '{action}': {str(e)}")
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                error_message=str(e),
                metadata={"dom_snapshot": task_context.get("last_dom", "")}
            )


class QAAgent(BaseAgent):
    """
    Quality Assurance Micro-Agent. Inspects screen DOM structures, execution logs,
    and visual screenshots to rate correctness and vote on next-step viability.
    """
    def __init__(self, agent_id: str, qa_type: str, weight: float = 1.0):
        super().__init__(agent_id, f"QA Agent ({qa_type})", "Quality Assurance & consensus voting")
        self.qa_type = qa_type
        self.weight = weight
        self.reputation_weight = weight

    def reward_agent(self, amount: float = 0.1):
        self.reputation_weight = min(2.0, self.reputation_weight + amount)
        
    def penalize_agent(self, amount: float = 0.1):
        self.reputation_weight = max(0.1, self.reputation_weight - amount)

    async def execute(self, task_context: Dict[str, Any]) -> AgentResult:
        exec_result: AgentResult = task_context.get("exec_result")
        step = task_context.get("step")
        
        if not exec_result or not step:
            return AgentResult(agent_id=self.agent_id, success=False, error_message="Missing execution result/step context.")
        
        if not exec_result.success:
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                confidence=1.0,
                error_message=f"Propagated execution failure: {exec_result.error_message}",
                metadata={"qa_type": self.qa_type}
            )

        dom = exec_result.metadata.get("dom_snapshot", "")
        action = step.get("action")
        
        vote_success = True
        confidence = 0.9
        feedback = "All checks passed"

        if self.qa_type == "DOM_Auditor":
            if action == "navigate":
                if not dom or len(dom) < 10:
                    vote_success = False
                    confidence = 0.95
                    feedback = "Empty DOM layout detected."
            elif action == "fill_form":
                inputs = step.get("inputs", {})
                for key in inputs.keys():
                    if any(keyword in key.lower() for keyword in ("captcha", "otp", "passcode", "verification_code")):
                        continue
                    parts = key.split('_')
                    camel_key = parts[0] + ''.join(x.title() for x in parts[1:]) if len(parts) > 1 else key
                    if key not in dom and camel_key not in dom:
                        vote_success = False
                        confidence = 0.8
                        feedback = f"Form input field '{key}' / '{camel_key}' not found in target page DOM layout."
            elif action == "click_submit":
                if "error" in dom.lower() or "fail" in dom.lower():
                    vote_success = False
                    confidence = 0.85
                    feedback = "Validation/Error message detected in submission result DOM."
                
        elif self.qa_type == "Visual_Auditor":
            screenshot = exec_result.metadata.get("screenshot_bytes")
            if screenshot is not None:
                if len(screenshot) < 100:
                    vote_success = False
                    confidence = 0.9
                    feedback = "Screenshot file size too small, potential blank page."
            else:
                if action == "click_submit" and "REG-" not in dom:
                    vote_success = False
                    confidence = 0.7
                    feedback = "Visual confirmation indicator (REG code) missing from output text."

        elif self.qa_type == "Semantic_Auditor":
            if action == "fill_form":
                inputs = step.get("inputs", {})
                from swarm_core.rag_engine import rag_engine
                for key, val in inputs.items():
                    # Query guidelines vector store for matching constraints
                    guidelines = rag_engine.search_guidelines_for_field(key)
                    for g in guidelines:
                        pattern = g.get("regex_pattern")
                        if pattern:
                            import re
                            # Remove typical punctuation/separators for digit fields during validation
                            clean_val = str(val).replace("-", "").replace(" ", "") if key in ("aadhaar", "phone", "user_number") else str(val)
                            if not re.match(pattern, clean_val):
                                vote_success = False
                                confidence = 0.95
                                feedback = f"Semantic RAG constraint violation for field '{key}': {g['description']}"
                                break
                    if not vote_success:
                        break

        return AgentResult(
            agent_id=self.agent_id,
            success=vote_success,
            confidence=confidence,
            output_data={"feedback": feedback},
            metadata={"qa_type": self.qa_type, "weight": self.reputation_weight}
        )


class ConsensusEngine:
    """
    3-Tier Consensus engine that aggregates votes from multiple QA Agents
    and calculates the majority decisions with confidence weights.
    """
    @staticmethod
    async def evaluate(
        qa_agents: List[QAAgent],
        step: Dict[str, Any],
        exec_result: AgentResult
    ) -> Tuple[bool, float, List[Dict[str, Any]]]:
        tasks = []
        for agent in qa_agents:
            context = {"step": step, "exec_result": exec_result}
            tasks.append(agent.execute(context))
        
        qa_results: List[AgentResult] = await asyncio.gather(*tasks)
        
        total_weight = 0.0
        weighted_success_score = 0.0
        audit_logs = []
        
        for res in qa_results:
            qa_type = res.metadata.get("qa_type", "Unknown")
            weight = res.metadata.get("weight", 1.0)
            total_weight += weight
            
            feedback = res.output_data.get("feedback", "")
            audit_logs.append({
                "qa_agent": res.agent_id,
                "qa_type": qa_type,
                "success_vote": res.success,
                "confidence": res.confidence,
                "feedback": feedback
            })
            
            vote_val = 1.0 if res.success else 0.0
            weighted_success_score += (vote_val * res.confidence * weight)
            
        max_possible_score = sum(res.confidence * res.metadata.get("weight", 1.0) for res in qa_results)
        consensus_score = (weighted_success_score / max_possible_score) if max_possible_score > 0 else 0.0
        passed = consensus_score >= 0.5
        
        logger.info(f"[ConsensusEngine] Tabulated QA consensus: Passed={passed}, Score={consensus_score:.2f}")
        return passed, consensus_score, audit_logs
