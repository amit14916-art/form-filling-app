import logging
from playwright.async_api import Page
from services.portal_strategies.base_strategy import PortalStrategy

logger = logging.getLogger("SSCStrategy")

class SSCStrategy(PortalStrategy):
    async def create_account(self, page: Page, user_data: dict) -> bool:
        logger.info("[SSCStrategy] Starting One-Time Registration...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://ssc.gov.in/otr/register", wait_until="networkidle")
        await self.human_type(page, "#candidate-name", user_data.get("full_name", ""))
        await self.human_type(page, "#candidate-mobile", user_data.get("phone", ""))
        await self.human_type(page, "#candidate-email", user_data.get("email", ""))
        await self.safe_click(page, "#generate-otr-otp")
        # Halts for OTP filling and submits OTR
        return True

    async def fill_profile(self, page: Page, user_data: dict) -> bool:
        logger.info("[SSCStrategy] Filling SSC-specific fields...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://ssc.gov.in/profile/details", wait_until="networkidle")
        await page.select_option("#gender-select", user_data.get("gender", "Female"))
        await page.select_option("#category-select", user_data.get("category", "GEN"))
        await page.select_option("#state-select", user_data.get("state", "Uttar Pradesh"))
        await self.safe_click(page, "#submit-details-btn")
        return True

    async def upload_documents(self, page: Page, docs: dict) -> bool:
        logger.info("[SSCStrategy] Uploading photo and signature...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://ssc.gov.in/documents/upload", wait_until="networkidle")
        
        # SSC requires signature size 10-20KB
        if "signature" in docs:
            await self.upload_file(page, "#signature-upload", docs["signature"])
            
        # Support live photo or upload photo
        if "photo" in docs:
            await self.upload_file(page, "#photo-upload", docs["photo"])
            
        await self.safe_click(page, "#confirm-upload-btn")
        return True

    async def handle_payment(self, page: Page, fee_info: dict) -> dict:
        logger.info("[SSCStrategy] Processing payment gate...")
        if self.is_mock_page(page):
            return {"status": "SUCCESS"}

        await page.goto("https://ssc.gov.in/payment", wait_until="networkidle")
        if fee_info.get("fee_waiver"):
            await self.safe_click(page, "#fee-exempted-checkbox")
            await self.safe_click(page, "#confirm-exemption")
            return {"status": "EXEMPTED"}
        else:
            await self.safe_click(page, "#pay-online-gateway")
            return {"status": "PENDING", "gateway": "PhonePe"}
