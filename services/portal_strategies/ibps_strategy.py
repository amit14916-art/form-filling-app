import logging
from playwright.async_api import Page
from services.portal_strategies.base_strategy import PortalStrategy

logger = logging.getLogger("IBPSStrategy")

class IBPSStrategy(PortalStrategy):
    async def create_account(self, page: Page, user_data: dict) -> bool:
        logger.info("[IBPSStrategy] Directing to IBPS New Registration...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://www.ibps.in/new-registration", wait_until="networkidle")
        await self.human_type(page, "input[name='first_name']", user_data.get("full_name", "").split(" ")[0])
        await self.human_type(page, "input[name='mobile']", user_data.get("phone", ""))
        await self.human_type(page, "input[name='email']", user_data.get("email", ""))
        await self.safe_click(page, "#register-submit")
        return True

    async def fill_profile(self, page: Page, user_data: dict) -> bool:
        logger.info("[IBPSStrategy] Filling basic profile...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://www.ibps.in/profile/edit", wait_until="networkidle")
        await page.select_option("#category", user_data.get("category", "GEN"))
        await page.select_option("#state", user_data.get("state", "Bihar"))
        await self.safe_click(page, "#save-details")
        return True

    async def upload_documents(self, page: Page, docs: dict) -> bool:
        logger.info("[IBPSStrategy] Uploading required thumb impression and handwritten declaration...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://www.ibps.in/documents/upload", wait_until="networkidle")
        
        # Photo (20-50KB)
        if "photo" in docs:
            await self.upload_file(page, "#photo-input", docs["photo"])
            
        # Signature (10-20KB)
        if "signature" in docs:
            await self.upload_file(page, "#signature-input", docs["signature"])
            
        # Left thumb impression (20-50KB)
        if "thumb_impression" in docs:
            await self.upload_file(page, "#thumb-input", docs["thumb_impression"])
        elif "photo" in docs:  # Mock fallback
            await self.upload_file(page, "#thumb-input", docs["photo"])
            
        # Handwritten declaration (50-100KB)
        if "declaration" in docs:
            await self.upload_file(page, "#declaration-input", docs["declaration"])
        elif "photo" in docs:  # Mock fallback
            await self.upload_file(page, "#declaration-input", docs["photo"])
            
        await self.safe_click(page, "#confirm-docs")
        return True

    async def handle_payment(self, page: Page, fee_info: dict) -> dict:
        logger.info("[IBPSStrategy] Checking IBPS payment screen...")
        if self.is_mock_page(page):
            return {"status": "SUCCESS"}

        await page.goto("https://www.ibps.in/payment/gateway", wait_until="networkidle")
        if fee_info.get("fee_waiver"):
            return {"status": "EXEMPTED"}
        else:
            await self.safe_click(page, "#pay-online-btn")
            return {"status": "PENDING", "gateway": "PhonePe"}
