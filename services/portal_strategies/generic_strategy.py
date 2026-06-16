import logging
from playwright.async_api import Page
from services.portal_strategies.base_strategy import PortalStrategy
from swarm_core.rag_engine import rag_engine

logger = logging.getLogger("GenericStrategy")

class GenericStrategy(PortalStrategy):
    async def create_account(self, page: Page, user_data: dict) -> bool:
        logger.info("[GenericStrategy] Navigating OTR register form...")
        if self.is_mock_page(page):
            # Fill inputs dynamically
            if await page.locator("input[name='name']").count() > 0:
                await self.human_type(page, "input[name='name']", user_data.get("full_name", ""))
            return True

        # Fallback dynamic selector resolution
        # Try to locate inputs by common placeholders or ids
        inputs = {
            "name": user_data.get("full_name", ""),
            "email": user_data.get("email", ""),
            "phone": user_data.get("phone", "")
        }
        for field, value in inputs.items():
            selector = f"input[name*='{field}']"
            try:
                if await page.locator(selector).count() > 0:
                    await self.human_type(page, selector, value)
            except Exception:
                continue
        return True

    async def fill_profile(self, page: Page, user_data: dict) -> bool:
        logger.info("[GenericStrategy] Filling profile form...")
        if self.is_mock_page(page):
            return True

        # Try to type educational and category values
        try:
            if await page.locator("select[id*='category']").count() > 0:
                await page.select_option("select[id*='category']", user_data.get("category", "GEN"))
            if await page.locator("select[id*='state']").count() > 0:
                await page.select_option("select[id*='state']", user_data.get("state", "Bihar"))
        except Exception as e:
            logger.warning(f"[GenericStrategy] Failed to fill some fields: {e}")
        return True

    async def upload_documents(self, page: Page, docs: dict) -> bool:
        logger.info("[GenericStrategy] Uploading files dynamically...")
        if self.is_mock_page(page):
            return True

        # Scan for file inputs
        for doc_type, file_path in docs.items():
            selector = f"input[type='file'][id*='{doc_type}']"
            try:
                if await page.locator(selector).count() > 0:
                    await self.upload_file(page, selector, file_path)
            except Exception:
                # Fallback to general file inputs
                continue
        return True

    async def handle_payment(self, page: Page, fee_info: dict) -> dict:
        logger.info("[GenericStrategy] Directing payment transaction...")
        if self.is_mock_page(page):
            return {"status": "SUCCESS"}
            
        if fee_info.get("fee_waiver"):
            return {"status": "EXEMPTED"}
        else:
            return {"status": "PENDING", "gateway": "PhonePe"}
