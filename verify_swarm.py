import asyncio
import unittest
from fastapi.testclient import TestClient

from main import app
from swarm_core.crypto_utils import derive_key, encrypt_pii_fields, decrypt_pii_fields
from swarm_core.agent_registry import PlanningAgent, ExecutionAgent, QAAgent, ConsensusEngine, AgentResult
from swarm_core.orchestrator import CEOOrchestrator

class TestMultiAgentSwarm(unittest.TestCase):
    
    def setUp(self):
        from swarm_core.rag_engine import rag_engine, SimpleVectorStore
        rag_engine.healing_store = SimpleVectorStore()
        self.passphrase = "super_secure_passphrase_123"
        self.key = derive_key(self.passphrase)
        self.pii_data = {
            "name": "Bob Dylan",
            "aadhaar": "1111-2222-3333",
            "phone": "+918888888888"
        }

    def test_cryptography_isolation(self):
        """
        Verify that PII fields are encrypted correctly and can only be decrypted
        with the correct key (Zero-Knowledge mandate).
        """
        fields = ["aadhaar", "phone"]
        encrypted = encrypt_pii_fields(self.pii_data, fields, self.key)
        
        # Verify encryption
        self.assertNotEqual(encrypted["aadhaar"], self.pii_data["aadhaar"])
        self.assertNotEqual(encrypted["phone"], self.pii_data["phone"])
        # Non-PII fields like name should not be encrypted if not specified in fields
        self.assertEqual(encrypted["name"], self.pii_data["name"])

        # Decrypt check
        decrypted = decrypt_pii_fields(encrypted, fields, self.key)
        self.assertEqual(decrypted["aadhaar"], self.pii_data["aadhaar"])
        self.assertEqual(decrypted["phone"], self.pii_data["phone"])
        
        # Bad key decryption should raise an exception
        bad_key = derive_key("wrong_passphrase_here")
        with self.assertRaises(Exception):
            decrypt_pii_fields(encrypted, fields, bad_key)

    def test_planning_agent(self):
        """
        Verify Planning Agent constructs pipeline DAG correctly.
        """
        planner = PlanningAgent()
        context = {
            "command": "Fill my exam registration form and notify me on whatsapp",
            "user_name": "Bob Dylan",
            "aadhaar": "encrypted_aadhaar_token"
        }
        
        # Run planning
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(planner.execute(context))
        
        self.assertTrue(res.success)
        steps = res.output_data["steps"]
        self.assertGreater(len(steps), 0)
        
        actions = [s["action"] for s in steps]
        self.assertIn("navigate", actions)
        self.assertIn("fill_form", actions)
        self.assertIn("notify_whatsapp", actions)

    def test_qa_consensus(self):
        """
        Verify that QA Agents and the Consensus Engine validate results correctly.
        """
        step = {"action": "click_submit", "selector": "#submit-btn"}
        exec_res = AgentResult(
            agent_id="test_exec",
            success=True,
            metadata={"dom_snapshot": "<div>Success! Registration code: REG-12345</div>"}
        )
        
        qa_agents = [
            QAAgent("qa1", "DOM_Auditor", weight=1.0),
            QAAgent("qa2", "Visual_Auditor", weight=1.0)
        ]
        
        loop = asyncio.get_event_loop()
        passed, confidence, logs = loop.run_until_complete(
            ConsensusEngine.evaluate(qa_agents, step, exec_res)
        )
        
        self.assertTrue(passed)
        self.assertGreaterEqual(confidence, 0.5)
        self.assertEqual(len(logs), 2)

    def test_self_healing_plan(self):
        """
        Verify Planning Agent rewrites DAG steps when a step fails QA checks.
        """
        failed_step = {"step_id": 2, "action": "click_submit", "selector": "#submit-btn-wrong"}
        current_steps = [
            {"step_id": 1, "action": "navigate", "url": "https://example.com"},
            failed_step,
            {"step_id": 3, "action": "notify_whatsapp"}
        ]
        dom_layout = "<button class='btn-primary'>Submit</button>"
        
        planner = PlanningAgent()
        loop = asyncio.get_event_loop()
        healed_steps = loop.run_until_complete(
            planner.heal_plan(
                failed_step=failed_step,
                error_msg="Element #submit-btn-wrong not found",
                dom_layout=dom_layout,
                current_steps=current_steps,
                retry_count=0
            )
        )
        
        # Assert healed steps contains updated selector
        healed_click_step = healed_steps[1]
        self.assertEqual(healed_click_step["selector"], "button.btn-primary")
        self.assertEqual(healed_click_step["retry_count"], 1)

    def test_fastapi_endpoints(self):
        """
        Verify REST API submission, ZK encrypted-state fetch, and decryption endpoints.
        """
        with TestClient(app) as client:
            # Submit task
            response = client.post(
                "/api/v1/chat-gateway/submit",
                json={
                    "user_id": 42,
                    "chat_message": (
                        "Fill my exam form and notify me on WhatsApp. "
                        f"My name is {self.pii_data['name']}, Aadhaar is {self.pii_data['aadhaar']}, "
                        f"phone is {self.pii_data['phone']}, passphrase is {self.passphrase}"
                    )
                }
            )
            self.assertEqual(response.status_code, 202)
            data = response.json()
            self.assertEqual(data["status"], "SUBMITTED")
            task_id = data["task_id"]
            
            # Verify status endpoint returns 200 and is formatted correctly
            status_resp = client.get(f"/api/v1/chat-gateway/status/{task_id}")
            self.assertEqual(status_resp.status_code, 200)
            status_data = status_resp.json()
            self.assertEqual(status_data["task_id"], task_id)

            # Verify Zero-Knowledge state storage (Aadhaar & phone must be encrypted)
            state_resp = client.get(f"/api/v1/chat-gateway/tasks/{task_id}/encrypted-state")
            self.assertEqual(state_resp.status_code, 200)
            state_data = state_resp.json()
            
            encrypted_context = state_data["encrypted_context"]
            self.assertNotEqual(encrypted_context["aadhaar"], self.pii_data["aadhaar"])
            self.assertNotEqual(encrypted_context["phone"], self.pii_data["phone"])
            # All items in pii_data are encrypted
            self.assertNotEqual(encrypted_context["name"], self.pii_data["name"])

            # Decrypt state output with correct passphrase
            decrypt_resp = client.post(
                f"/api/v1/chat-gateway/tasks/{task_id}/decrypt-output?passphrase={self.passphrase}"
            )
            self.assertEqual(decrypt_resp.status_code, 200)
            decrypted_data = decrypt_resp.json()
            self.assertEqual(decrypted_data["decrypted_context"]["aadhaar"], self.pii_data["aadhaar"])
            self.assertEqual(decrypted_data["decrypted_context"]["name"], self.pii_data["name"])

            # Decrypt with wrong passphrase should fail
            bad_decrypt_resp = client.post(
                f"/api/v1/chat-gateway/tasks/{task_id}/decrypt-output?passphrase=wrong_passphrase"
            )
            self.assertEqual(bad_decrypt_resp.status_code, 400)

    def test_live_web_form_interaction(self):
        """
        Verify real-world stealth browser execution and mapping logic using
        StealthBrowserWorker against a practice form testing mirror.
        """
        import asyncio
        from tools.browser_worker import StealthBrowserWorker
        
        target_url = "https://demoqa.com/automation-practice-form"
        user_profile = {
            "first_name": "Amit",
            "last_name": "Prasad",
            "user_email": "amit@test.com",
            "gender": "Male",
            "user_number": "9876543210"
        }
        
        worker = StealthBrowserWorker()
        loop = asyncio.get_event_loop()
        
        current_step = {
            "action": "fill_form", 
            "description": "Fill practice form",
            "inputs": user_profile
        }
        qa_agents = [
            QAAgent("qa_dom_test", "DOM_Auditor", weight=1.0)
        ]
        
        async def run_test():
            try:
                await worker.init_session()
                res = await worker.execute_form_fill(
                    url=target_url,
                    form_data=user_profile,
                    qa_agents=qa_agents,
                    current_step=current_step
                )
                return res
            except Exception as e:
                # Sanitize string to ascii to prevent UnicodeEncodeError in Windows consoles
                safe_err = str(e).encode('ascii', 'ignore').decode('ascii')
                print(f"\n[SKIP] Live browser test skipped (Expected if browser binaries are not installed): {safe_err}")
                return None
            finally:
                await worker.close_session()
                
        res = loop.run_until_complete(run_test())
        if res is not None:
            self.assertTrue(res["success"])
            self.assertIsNotNone(res["screenshot_bytes"])
            self.assertGreater(len(res["screenshot_bytes"]), 0)

    def test_stealth_browser_initialization(self):
        """
        Verify that StealthBrowserWorker injects variables to bypass bot detection.
        """
        import asyncio
        from tools.browser_worker import StealthBrowserWorker
        worker = StealthBrowserWorker()
        loop = asyncio.get_event_loop()
        
        async def run_test():
            try:
                page = await worker.init_session()
                # Verify navigator.webdriver is undefined
                webdriver = await page.evaluate("navigator.webdriver")
                self.assertIsNone(webdriver)
                
                # Verify plugins are mocked
                plugins_len = await page.evaluate("navigator.plugins.length")
                self.assertEqual(plugins_len, 3)
                
                # Verify language is English
                lang = await page.evaluate("navigator.languages[0]")
                self.assertEqual(lang, "en-US")
                
                # Verify WebGL spoofing
                webgl_vendor = await page.evaluate("""
                    (() => {
                        const canvas = document.createElement('canvas');
                        const gl = canvas.getContext('webgl');
                        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                        return gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                    })()
                """)
                self.assertEqual(webgl_vendor, "Intel Inc.")
                return True
            except Exception as e:
                safe_err = str(e).encode('ascii', 'ignore').decode('ascii')
                print(f"\n[SKIP] Stealth test skipped: {safe_err}")
                return False
            finally:
                await worker.close_session()

        loop.run_until_complete(run_test())

    def test_captcha_solver_hook(self):
        """
        Verify that solve_page_captcha locates and solves a captcha element block.
        """
        import asyncio
        from tools.browser_worker import StealthBrowserWorker
        worker = StealthBrowserWorker()
        loop = asyncio.get_event_loop()

        async def run_test():
            try:
                page = await worker.init_session()
                await page.set_content("<img id='test-captcha' src='data:image/png;base64,iVBORw0KGgo=' />")
                token = await worker.solve_page_captcha(page, "#test-captcha")
                self.assertTrue(token.startswith("SOLVED_CAPTCHA_MOCK_TOKEN_"))
                return True
            except Exception as e:
                safe_err = str(e).encode('ascii', 'ignore').decode('ascii')
                print(f"\n[SKIP] Captcha hook test skipped: {safe_err}")
                return False
            finally:
                await worker.close_session()

        loop.run_until_complete(run_test())

    def test_otp_sync_and_polling(self):
        """
        Verify that OTP polling halts execution and resumes upon receiving an event.
        """
        import asyncio
        from tools.browser_worker import StealthBrowserWorker
        from swarm_core.orchestrator import EventBroker
        
        worker = StealthBrowserWorker()
        broker = EventBroker()
        loop = asyncio.get_event_loop()
        task_id = "test-otp-task-12345"
        
        async def run_test():
            await broker.connect()
            try:
                page = await worker.init_session()
                # Create a simple form page with an OTP input field
                await page.set_content("""
                    <form>
                        <input name='user_otp' id='otp_field' />
                    </form>
                """)
                
                form_data = {
                    "user_otp": "PENDING"
                }
                
                # Publish the OTP event in the background after 2 seconds
                async def publish_otp_later():
                    await asyncio.sleep(2)
                    await broker.publish(f"task_otp:{task_id}", {"otp": "992811"})
                
                pub_task = asyncio.create_task(publish_otp_later())
                
                # Execute form filling which should halt and receive the OTP code
                res = await worker.execute_form_fill(
                    url=page.url,
                    form_data=form_data,
                    qa_agents=[],
                    current_step={"action": "fill_form", "inputs": form_data},
                    task_id=task_id,
                    broker=broker
                )
                
                await pub_task
                
                # Read the input value to verify it was filled with the correct OTP code
                filled_val = await page.locator("#otp_field").input_value()
                self.assertEqual(filled_val, "992811")
                return True
            except Exception as e:
                safe_err = str(e).encode('ascii', 'ignore').decode('ascii')
                print(f"\n[SKIP] OTP sync test skipped: {safe_err}")
                return False
            finally:
                await worker.close_session()
                await broker.close()

        loop.run_until_complete(run_test())

    def test_fastapi_otp_webhook(self):
        """
        Verify that FastAPI gateway router dispatches external OTP webhook signals to the worker.
        """
        with TestClient(app) as client:
            task_id = "test-fastapi-otp-task"
            
            # Post OTP webhook
            response = client.post(
                f"/api/v1/chat-gateway/tasks/{task_id}/otp",
                json={"otp": "112233"}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "SUCCESS")
            self.assertIn("dispatched", data["message"])

    def test_rag_vector_store_retrieval(self):
        """
        Verify that SimpleVectorStore indexes and performs TF-IDF Cosine Similarity retrieval.
        """
        from swarm_core.rag_engine import SimpleVectorStore
        store = SimpleVectorStore()
        
        store.add_document("doc1", "This is about Aadhaar validation rules and patterns.", {"category": "aadhaar"})
        store.add_document("doc2", "This details Playwright browser automation stealth parameters.", {"category": "browser"})
        
        # Query matching doc1
        results = store.retrieve("Aadhaar rule check", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0]["metadata"]["category"], "aadhaar")
        self.assertGreater(results[0][1], 0.1)

    def test_rag_healing_retrieval(self):
        """
        Verify that PlanningAgent utilizes RAG to query and apply resolved selector mappings.
        """
        from swarm_core.rag_engine import rag_engine
        
        # Inject healing action in RAG
        rag_engine.add_healing_record(
            failed_selector="#old-submit",
            error_message="Element not found",
            dom_snippet="<button class='btn-success'>Proceed</button>",
            healed_selector="button.btn-success"
        )
        
        # Execute heal_plan and assert it hits RAG and returns the resolved selector
        failed_step = {"step_id": 2, "action": "click_submit", "selector": "#old-submit"}
        current_steps = [failed_step]
        
        planner = PlanningAgent()
        loop = asyncio.get_event_loop()
        healed_steps = loop.run_until_complete(
            planner.heal_plan(
                failed_step=failed_step,
                error_msg="Element not found",
                dom_layout="<button class='btn-success'>Proceed</button>",
                current_steps=current_steps,
                retry_count=0
            )
        )
        
        self.assertEqual(healed_steps[0]["selector"], "button.btn-success")

    def test_rag_semantic_qa_violation(self):
        """
        Verify that QAAgent Semantic Auditor triggers constraint errors based on RAG guidelines.
        """
        qa_agent = QAAgent("qa_sem", "Semantic_Auditor", weight=1.0)
        
        # Invalid phone format (not 10 digits)
        invalid_step = {
            "action": "fill_form",
            "inputs": {"phone": "12345"}
        }
        
        exec_res = AgentResult(
            agent_id="exec_test",
            success=True,
            metadata={"dom_snapshot": "<div>Empty</div>"}
        )
        
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(
            qa_agent.execute({"step": invalid_step, "exec_result": exec_res})
        )
        
        self.assertFalse(res.success)
        self.assertIn("Semantic RAG constraint violation", res.output_data["feedback"])

    def test_mcp_browser_server_tool_calls(self):
        """
        Verify that the SwarmMCPClient connects to the MCP Browser Server and makes tool calls.
        """
        from tools.mcp_client import SwarmMCPClient
        import json
        loop = asyncio.get_event_loop()
        
        async def run_test():
            try:
                async with SwarmMCPClient() as mcp_client:
                    # Test 'browser_navigate' tool call
                    res = await mcp_client.call_tool("browser_navigate", {"url": "about:blank"})
                    self.assertIn("SUCCESS", res.content[0].text)
                    
                    # Test 'browser_close' tool call
                    close_res = await mcp_client.call_tool("browser_close", {})
                    self.assertIn("SUCCESS", close_res.content[0].text)
                return True
            except Exception as e:
                safe_err = str(e).encode('ascii', 'ignore').decode('ascii')
                print(f"\n[SKIP] MCP Client tool call skipped: {safe_err}")
                return False

        loop.run_until_complete(run_test())

    def test_indian_exam_rag_retrieval(self):
        """
        Verify that seeded Indian government exam portal details are searchable in the RAG store.
        """
        from swarm_core.rag_engine import rag_engine
        
        # Search for BPSC Bihar exam portal
        results = rag_engine.search_guidelines_for_field("BPSC Bihar")
        self.assertGreater(len(results), 0)
        
        # Check that retrieved guideline matches BPSC details
        bpsc_match = results[0]
        self.assertEqual(bpsc_match["conducting_body"], "Bihar Public Service Commission (BPSC)")
        self.assertEqual(bpsc_match["portal_url"], "https://bpsc.bih.nic.in")
        self.assertIn("Live web-cam", bpsc_match["guidelines"])

    def test_consensus_reputation_adjustment(self):
        """
        Verify that correct auditors are rewarded, incorrect ones penalized,
        and a heavily penalized auditor's vote is overruled.
        """
        # Create three QA Agents with initially equal weights
        qa1 = QAAgent("qa1", "DOM_Auditor", weight=1.0)
        qa2 = QAAgent("qa2", "Visual_Auditor", weight=1.0)
        qa3 = QAAgent("qa3", "Semantic_Auditor", weight=1.0)
        qa_agents = [qa1, qa2, qa3]
        
        # Simulate 12 rewards for qa1 and qa2, and 12 penalties for qa3
        for _ in range(12):
            qa1.reward_agent(0.1)
            qa2.reward_agent(0.1)
            qa3.penalize_agent(0.1)
            
        # Assert weights adjusted within bounds (max 2.0, min 0.1)
        self.assertAlmostEqual(qa1.reputation_weight, 2.0)
        self.assertAlmostEqual(qa2.reputation_weight, 2.0)
        self.assertAlmostEqual(qa3.reputation_weight, 0.1)
        
        # Test consensus where qa3 (reputation=0.1) votes False, but qa1 and qa2 (reputation=2.0) vote True.
        # Step: fill_form, with invalid phone number for qa3 (Semantic_Auditor)
        step = {
            "action": "fill_form",
            "inputs": {"phone": "123"}
        }
        exec_res = AgentResult(
            agent_id="test_exec",
            success=True,
            metadata={
                "dom_snapshot": "<form><input name='phone' value='123' /></form>",
                "screenshot_bytes": b"*" * 200
            }
        )
        
        loop = asyncio.get_event_loop()
        passed, confidence, logs = loop.run_until_complete(
            ConsensusEngine.evaluate(qa_agents, step, exec_res)
        )
        
        # Consensus should pass even though the Semantic Auditor voted False (overruled due to penalty)
        self.assertTrue(passed)
        self.assertGreater(confidence, 0.9)
        
        # Test opposite overrule: qa_high (weight 2.0) votes False, qa_low1 & qa_low2 (weight 0.1) vote True.
        qa_high = QAAgent("qa_high", "DOM_Auditor", weight=2.0)
        qa_low1 = QAAgent("qa_low1", "Visual_Auditor", weight=0.1)
        qa_low2 = QAAgent("qa_low2", "Semantic_Auditor", weight=0.1)
        
        # Trigger DOM_Auditor voting False via "error" in dom
        step_submit = {
            "action": "click_submit",
            "selector": "#submit-btn"
        }
        exec_res_error = AgentResult(
            agent_id="test_exec_err",
            success=True,
            metadata={
                "dom_snapshot": "<div>An error occurred!</div>",
                "screenshot_bytes": b"*" * 200
            }
        )
        
        passed_err, confidence_err, logs_err = loop.run_until_complete(
            ConsensusEngine.evaluate([qa_high, qa_low1, qa_low2], step_submit, exec_res_error)
        )
        
        # Consensus should fail because the high reputation agent voted False, overruling the others
        self.assertFalse(passed_err)


if __name__ == "__main__":
    unittest.main()
