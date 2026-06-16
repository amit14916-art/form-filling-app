import abc
import random
import asyncio
import logging
from playwright.async_api import Page
from swarm_core.rag_engine import rag_engine

logger = logging.getLogger("BaseStrategy")

class PortalStrategy(abc.ABC):
    @abc.abstractmethod
    async def create_account(self, page: Page, user_data: dict) -> bool:
        """Navigates to the portal's registration page and creates a candidate profile."""
        pass

    @abc.abstractmethod
    async def fill_profile(self, page: Page, user_data: dict) -> bool:
        """Navigates to the application forms and inputs demographic/educational data."""
        pass

    @abc.abstractmethod
    async def upload_documents(self, page: Page, docs: dict) -> bool:
        """Locates document upload slots and uploads photo, signature, marksheet, etc."""
        pass

    @abc.abstractmethod
    async def handle_payment(self, page: Page, fee_info: dict) -> dict:
        """Handles payment page parsing, fee waivers, or triggers external payment gateway links."""
        pass

    def is_mock_page(self, page: Page) -> bool:
        """Helper to identify if we are running in an integration testing or mock environment."""
        url = page.url
        return "example.com" in url or "localhost" in url or "about:blank" in url or "testserver" in url

    async def human_type(self, page: Page, selector: str, text: str):
        """Types text character by character with random delays (10-80ms) to bypass bot detection."""
        await page.focus(selector)
        # Clear field first
        await page.fill(selector, "")
        for char in str(text):
            await page.type(selector, char)
            await asyncio.sleep(random.uniform(0.01, 0.08))

    async def safe_click(self, page: Page, selector: str):
        """Clicks an element, falling back to RAG selector healing if the click fails."""
        try:
            await page.wait_for_selector(selector, state="visible", timeout=5000)
            await page.click(selector, timeout=5000)
        except Exception as e:
            logger.warning(f"Click failed on '{selector}'. Triggering RAG selector healing...")
            dom = await page.content()
            healed = rag_engine.search_healing_solution(
                failed_selector=selector,
                error_message=str(e),
                current_dom=dom
            )
            if healed:
                logger.info(f"RAG suggested healed selector: '{healed}'. Attempting click...")
                await page.wait_for_selector(healed, state="visible", timeout=5000)
                await page.click(healed, timeout=5000)
            else:
                logger.error(f"No RAG healing record found for '{selector}'. Raising original error.")
                raise e

    async def upload_file(self, page: Page, selector: str, file_path: str):
        """Uploads a file using the direct file input or fallback file chooser click."""
        try:
            await page.set_input_files(selector, file_path)
            logger.info(f"Successfully uploaded file '{file_path}' directly to '{selector}'.")
        except Exception:
            logger.info(f"Direct set_input_files failed on '{selector}'. Trying file chooser...")
            async with page.expect_file_chooser() as fc_info:
                await page.click(selector)
            file_chooser = await fc_info.value
            await file_chooser.set_files(file_path)
            logger.info(f"Successfully uploaded file '{file_path}' via file chooser.")
