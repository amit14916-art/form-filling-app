import logging
from playwright.async_api import Page
from services.portal_strategies.base_strategy import PortalStrategy

logger = logging.getLogger("UPSCStrategy")

class UPSCStrategy(PortalStrategy):
    async def create_account(self, page: Page, user_data: dict) -> bool:
        logger.info("[UPSCStrategy] Starting account creation...")
        if self.is_mock_page(page):
            # Simulation/Mock Form
            if await page.locator("input[name='name']").count() > 0:
                await self.human_type(page, "input[name='name']", user_data.get("full_name", ""))
            return True

        # Real UPSC Portal flow
        await page.goto("https://upsconline.nic.in/otr/registration.php", wait_until="networkidle")
        await self.human_type(page, "#name", user_data.get("full_name", ""))
        await self.human_type(page, "#email", user_data.get("email", ""))
        await self.human_type(page, "#phone", user_data.get("phone", ""))
        await self.human_type(page, "#dob", user_data.get("dob", ""))
        
        # Click submit and trigger OTP sync
        await self.safe_click(page, "#submit-otr-btn")
        logger.info("[UPSCStrategy] OTR Form submitted, waiting for OTP validation...")
        return True

    async def fill_profile(self, page: Page, user_data: dict) -> bool:
        logger.info("[UPSCStrategy] Filling profile details...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://upsconline.nic.in/profile/edit", wait_until="networkidle")
        await self.human_type(page, "#father-name", user_data.get("father_name", "Father Name"))
        await self.human_type(page, "#mother-name", user_data.get("mother_name", "Mother Name"))
        await page.select_option("#category", user_data.get("category", "GEN"))
        await page.select_option("#qualification", user_data.get("qualification", "Graduate"))
        await self.safe_click(page, "#save-profile-btn")
        return True

    async def upload_documents(self, page: Page, docs: dict) -> bool:
        logger.info("[UPSCStrategy] Uploading documents...")
        if self.is_mock_page(page):
            return True

        await page.goto("https://upsconline.nic.in/documents/upload", wait_until="networkidle")
        
        # Photo upload (JPG 20-300KB)
        if "photo" in docs:
            await self.upload_file(page, "#photo-upload-input", docs["photo"])
            
        # Signature upload (JPG 20-300KB)
        if "signature" in docs:
            await self.upload_file(page, "#signature-upload-input", docs["signature"])
            
        # Photo ID card upload (PDF)
        if "aadhaar" in docs:
            await self.upload_file(page, "#id-card-upload-input", docs["aadhaar"])
            
        await self.safe_click(page, "#confirm-upload-btn")
        return True

    async def handle_payment(self, page: Page, fee_info: dict) -> dict:
        logger.info("[UPSCStrategy] Handling payment page parsing...")
        if self.is_mock_page(page):
            return {"status": "SUCCESS", "method": "exemption" if fee_info.get("fee_waiver") else "simulated_phonepe"}

        await page.goto("https://upsconline.nic.in/payment/gateway", wait_until="networkidle")
        
        if fee_info.get("fee_waiver"):
            # Select exemption checkbox/radio
            await self.safe_click(page, "#exemption-sc-st-women")
            await self.safe_click(page, "#submit-payment-exemption")
            return {"status": "EXEMPTED", "transaction_id": "EXEMPT-UPSC"}
        else:
            # Select SBI Collect / UPI / Redirect options
            await self.safe_click(page, "#sbi-collect-payment")
            await self.safe_click(page, "#pay-via-upi")
            # Return redirection info
            return {"status": "PENDING", "gateway": "PhonePe"}
