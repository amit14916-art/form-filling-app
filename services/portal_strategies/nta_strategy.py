import logging
from playwright.async_api import Page
from services.portal_strategies.base_strategy import PortalStrategy

logger = logging.getLogger("NTAStrategy")

class NTAStrategy(PortalStrategy):
    async def create_account(self, page: Page, user_data: dict) -> bool:
        logger.info("[NTAStrategy] Starting account creation...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://jeemain.nta.ac.in/register", wait_until="networkidle")
        await self.human_type(page, "#candidate-name", user_data.get("full_name", ""))
        await self.human_type(page, "#email-id", user_data.get("email", ""))
        await self.human_type(page, "#phone-no", user_data.get("phone", ""))
        await self.safe_click(page, "#submit-reg")
        return True

    async def fill_profile(self, page: Page, user_data: dict) -> bool:
        logger.info("[NTAStrategy] Filling educational and personal details...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://jeemain.nta.ac.in/profile", wait_until="networkidle")
        await page.select_option("#category-select", user_data.get("category", "GEN"))
        await page.select_option("#state-select", user_data.get("state", "Uttar Pradesh"))
        await self.safe_click(page, "#save-details")
        return True

    async def upload_documents(self, page: Page, docs: dict) -> bool:
        logger.info("[NTAStrategy] Uploading passport/postcard photos, signature, and category cert...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://jeemain.nta.ac.in/upload", wait_until="networkidle")
        
        # Passport photo
        if "photo" in docs:
            await self.upload_file(page, "#passport-photo-input", docs["photo"])
            
        # Postcard photo
        if "postcard_photo" in docs:
            await self.upload_file(page, "#postcard-photo-input", docs["postcard_photo"])
        elif "photo" in docs:  # Fallback
            await self.upload_file(page, "#postcard-photo-input", docs["photo"])
            
        # Signature
        if "signature" in docs:
            await self.upload_file(page, "#signature-input", docs["signature"])
            
        # Category/Caste certificate
        if "caste_cert" in docs:
            await self.upload_file(page, "#category-cert-input", docs["caste_cert"])
            
        await self.safe_click(page, "#confirm-uploads")
        return True

    async def handle_payment(self, page: Page, fee_info: dict) -> dict:
        logger.info("[NTAStrategy] Parsing NTA payment gate...")
        if self.is_mock_page(page):
            return {"status": "SUCCESS"}

        await page.goto("https://jeemain.nta.ac.in/payment", wait_until="networkidle")
        if fee_info.get("fee_waiver"):
            return {"status": "EXEMPTED"}
        else:
            await self.safe_click(page, "#pay-via-upi")
            return {"status": "PENDING", "gateway": "PhonePe"}
