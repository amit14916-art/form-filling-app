import asyncio
import logging
import random
from typing import Dict, Any, List, Optional, Tuple
from playwright.async_api import async_playwright, Page

from swarm_core.agent_registry import AgentResult, ConsensusEngine

logger = logging.getLogger("BrowserWorker")

class StealthBrowserWorker:
    """
    Asynchronous Playwright Browser Worker that initializes unban-optimized Chromium sessions,
    performs human-like typing actions, and supports QA consensus checks before form submission.
    """
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        self.proxy_config = proxy_config
        self.playwright = None
        self.browser = None
        self.context = None
        self.page: Optional[Page] = None

    async def init_session(self) -> Page:
        """
        Initializes async_playwright(), launches a stealth Chromium instance,
        sets randomized modern user-agents, disables automation flags, and configures viewports.
        """
        self.playwright = await async_playwright().start()

        # Random modern User-Agent selection to bypass browser detection
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]
        user_agent = random.choice(user_agents)

        headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "sec-ch-ua": '"Chromium";v="123", "Not(A:Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

        # Randomized resolution to bypass simple canvas/screen size fingerprint checks
        resolutions = [
            {"width": 1920, "height": 1080},
            {"width": 1440, "height": 900},
            {"width": 1366, "height": 768},
            {"width": 1280, "height": 800}
        ]
        viewport = random.choice(resolutions)

        launch_args = {
            "headless": False,
            "slow_mo": 500,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions"
            ]
        }
        if self.proxy_config:
            launch_args["proxy"] = self.proxy_config

        logger.info(f"[StealthBrowserWorker] Launching Chromium with user-agent: {user_agent} and viewport: {viewport}")
        self.browser = await self.playwright.chromium.launch(**launch_args)
        
        self.context = await self.browser.new_context(
            user_agent=user_agent,
            extra_http_headers=headers,
            viewport=viewport
        )

        # High-Performance Injection script to mask runtime fingerprints, spoof plugins, languages and webdriver object
        stealth_script = """
            // Delete webdriver flag
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Spoof plugins
            const mockPlugins = [
                { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }
            ];
            Object.defineProperty(navigator, 'plugins', {
                get: () => mockPlugins
            });

            // Spoof languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Spoof device properties
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            // Spoof WebGL vendor and renderer
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                    return 'Intel Inc.';
                }
                if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                    return 'Intel(R) Iris(TM) Plus Graphics 640';
                }
                return getParameter.apply(this, arguments);
            };

            // Override permissions query
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """
        await self.context.add_init_script(stealth_script)

        self.page = await self.context.new_page()
        return self.page

    async def solve_page_captcha(self, page_instance: Page, captcha_selector: str) -> str:
        """
        Locates the captcha element block, extracts its image source or captures a screenshot of the block,
        and provides a clean production placeholder to route the token/image to an external solver API.
        """
        logger.info(f"[StealthBrowserWorker] Locating captcha element using selector: '{captcha_selector}'")
        try:
            element = page_instance.locator(captcha_selector).first
            if await element.count() == 0:
                logger.warning(f"[StealthBrowserWorker] Captcha element '{captcha_selector}' not found.")
                return ""

            # Extract image source or attribute
            img_src = await element.get_attribute("src") or ""
            logger.info(f"[StealthBrowserWorker] Extracted captcha source attribute: {img_src[:100]}...")

            # Capture visual screenshot of the captcha element to solve
            screenshot_bytes = None
            if await element.is_visible():
                screenshot_bytes = await element.screenshot(type="png")
                logger.info("[StealthBrowserWorker] Captured captcha element screenshot bytes successfully.")

            # Production Placeholder Solver API Hook
            # In production, route to 2Captcha / Anti-Captcha / Custom API:
            # solver_token = await call_external_solver(img_src, screenshot_bytes)
            # return solver_token

            mock_solved_token = "SOLVED_CAPTCHA_MOCK_TOKEN_" + str(random.randint(1000, 9999))
            logger.info(f"[StealthBrowserWorker] Captcha solved via production placeholder. Returned Token: {mock_solved_token}")
            return mock_solved_token

        except Exception as e:
            logger.error(f"[StealthBrowserWorker] Error solving captcha element: {str(e)}")
            return ""

    async def execute_form_fill(
        self,
        url: str,
        form_data: Dict[str, Any],
        qa_agents: List[Any],
        current_step: Dict[str, Any],
        task_id: Optional[str] = None,
        broker: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Navigates to URL, waits for DOM ready states, maps and types form fields
        character-by-character using human-like delays (150ms-300ms), resolves captcha
        if detected, halts for OTP input up to 60 seconds if OTP fields are detected,
        and runs a live QA consensus hook BEFORE submit action execution.
        """
        if not self.page:
            await self.init_session()

        if url and url != "about:blank" and not url.startswith("data:"):
            logger.info(f"[StealthBrowserWorker] Navigating to target form URL: {url}")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Wait until DOM state is fully loaded dynamically
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_timeout(1000)
        else:
            logger.info(f"[StealthBrowserWorker] Skipping navigation for URL: {url}")

        # Proactive Captcha Detection and Handling
        captcha_selectors = ["#captcha", ".captcha", "img[src*='captcha']", "iframe[src*='recaptcha']"]
        custom_captcha_sel = current_step.get("captcha_selector")
        if custom_captcha_sel:
            captcha_selectors.insert(0, custom_captcha_sel)

        for sel in captcha_selectors:
            try:
                if await self.page.locator(sel).count() > 0:
                    logger.info(f"[StealthBrowserWorker] Captcha element '{sel}' detected on page load.")
                    captcha_val = await self.solve_page_captcha(self.page, sel)
                    if captcha_val:
                        # Inject captcha solution into form data so we can fill it if requested
                        form_data["captcha_solution"] = captcha_val
                        form_data["captcha"] = captcha_val
                        break
            except Exception:
                continue

        # Step 1: Map fields and inject data with human-like delays
        for field, value in form_data.items():
            # Translate snake_case keys to camelCase (e.g., first_name -> firstName)
            parts = field.split('_')
            camel_field = parts[0] + ''.join(x.title() for x in parts[1:]) if len(parts) > 1 else field
            
            selectors = [
                f"input[name='{field}']",
                f"input[name='{camel_field}']",
                f"#{field}",
                f"#{camel_field}",
                f"input[placeholder*='{field.replace('_', ' ').title()}']",
                f"input[placeholder*='{camel_field.title()}']"
            ]

            # OTP Sync State Detection
            is_otp_field = any(keyword in field.lower() or keyword in camel_field.lower() 
                               for keyword in ["otp", "passcode", "verification_code", "seccode", "sec_code"])
            
            if is_otp_field:
                logger.info(f"[StealthBrowserWorker] OTP input field detected: '{field}' / '{camel_field}'")
                otp_code = None
                
                if broker and task_id:
                    channel = f"task_otp:{task_id}"
                    logger.info(f"[StealthBrowserWorker] OTP sync state active. Halting execution pipeline for task {task_id}. Waiting up to 60s for OTP signal on '{channel}'...")
                    
                    async def wait_for_otp_signal():
                        nonlocal otp_code
                        try:
                            async for event in broker.listen(channel):
                                if "otp" in event:
                                    otp_code = event["otp"]
                                    logger.info(f"[StealthBrowserWorker] Received OTP event signal: {otp_code}")
                                    break
                        except Exception as e:
                            logger.error(f"[StealthBrowserWorker] Error listening to OTP channel: {e}")
                    
                    listener_task = asyncio.create_task(wait_for_otp_signal())
                    
                    # Polling retry/wait loop up to 60 seconds
                    for sec in range(60):
                        if otp_code is not None:
                            break
                        await asyncio.sleep(1)
                    
                    listener_task.cancel()
                else:
                    logger.warning("[StealthBrowserWorker] EventBroker or task_id missing in context. Skipping OTP wait loop.")

                if otp_code:
                    value = otp_code
                    logger.info(f"[StealthBrowserWorker] Continuing execution. Injecting OTP: {value}")
                else:
                    logger.warning("[StealthBrowserWorker] OTP wait loop timed out after 60s or no OTP was received. Proceeding with default value.")

            # Special support for gender selection
            if field == "gender":
                try:
                    locator = self.page.locator(f"label:has-text('{value}')")
                    if await locator.count() > 0:
                        logger.info(f"[StealthBrowserWorker] Clicking gender label match: '{value}'")
                        await locator.first.click()
                        await self.page.wait_for_timeout(random.randint(150, 300))
                        continue
                except Exception as e:
                    logger.warning(f"Failed to click gender radio: {e}")

            # Locate input elements using various selector patterns
            found = False
            for selector in selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        logger.info(f"[StealthBrowserWorker] Typing field '{field}' using selector '{selector}'")
                        await self.page.focus(selector)
                        await self.page.wait_for_timeout(random.randint(150, 300))
                        await self.page.fill(selector, "") # Clear input

                        # Character-by-character human-like typing simulation
                        for char in str(value):
                            await self.page.type(selector, char)
                            await self.page.wait_for_timeout(random.randint(50, 150))

                        await self.page.wait_for_timeout(random.randint(200, 400))
                        found = True
                        break
                except Exception:
                    continue

            if not found:
                logger.warning(f"[StealthBrowserWorker] Selector target for field '{field}' was not found.")

        # Step 2: Live Verification Hook
        # Save screenshot buffer and DOM state at the end of the form filling loop (right before submit action)
        logger.info("[StealthBrowserWorker] Running Live Verification Hook before final submission...")
        screenshot_bytes = await self.page.screenshot(type="png")
        dom_snapshot = await self.page.content()

        # Construct transient execution result for QA auditing
        mock_exec_result = AgentResult(
            agent_id="browser_worker_form_fill",
            success=True,
            metadata={
                "screenshot_bytes": screenshot_bytes,
                "dom_snapshot": dom_snapshot
            }
        )

        # Evaluate consensus across the QA Agent pipeline
        qa_passed, confidence, qa_logs = await ConsensusEngine.evaluate(
            qa_agents,
            current_step,
            mock_exec_result
        )

        logger.info(f"[StealthBrowserWorker] QA Consensus Result: Passed={qa_passed}, Confidence={confidence:.2f}")

        return {
            "success": qa_passed,
            "confidence": confidence,
            "qa_logs": qa_logs,
            "final_dom": dom_snapshot,
            "screenshot_bytes": screenshot_bytes
        }

    async def close_session(self):
        """
        Safely disposes all playwright and browser assets after a verification sleep.
        """
        logger.info("[StealthBrowserWorker] Keeping browser open for 5 seconds for visual verification...")
        await asyncio.sleep(5)
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("[StealthBrowserWorker] Browser session closed successfully.")
