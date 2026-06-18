import base64
import logging
import asyncio
import httpx

logger = logging.getLogger("CaptchaSolver")

async def solve_image_captcha(api_key: str, image_bytes: bytes) -> str:
    """
    Submits image bytes to the 2Captcha API and polls for the result.
    Returns the solved CAPTCHA text or raises an exception.
    """
    if not api_key or api_key == "your-api-key-here":
        logger.warning("No valid CAPTCHA API key provided. CAPTCHA solver will not run.")
        raise ValueError("Invalid CAPTCHA API key.")
        
    logger.info("Submitting CAPTCHA image to 2Captcha solver service...")
    
    # Base64 encode the image
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    # 2Captcha submission endpoint
    in_url = "https://2captcha.com/in.php"
    payload = {
        "key": api_key,
        "method": "base64",
        "body": base64_image,
        "json": 1
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Submit the CAPTCHA
            response = await client.post(in_url, data=payload)
            response.raise_for_status()
            res_json = response.json()
            
            if res_json.get("status") != 1:
                error_msg = res_json.get("request", "Unknown Error")
                logger.error(f"2Captcha submission failed: {error_msg}")
                raise Exception(f"2Captcha submission error: {error_msg}")
                
            task_id = res_json["request"]
            logger.info(f"CAPTCHA submitted successfully. Task ID: {task_id}. Polling for solution...")
            
            # Poll for the solution
            res_url = "https://2captcha.com/res.php"
            poll_params = {
                "key": api_key,
                "action": "get",
                "id": task_id,
                "json": 1
            }
            
            # Max poll duration: 60 seconds
            for attempt in range(30):
                await asyncio.sleep(2)
                poll_resp = await client.get(res_url, params=poll_params)
                poll_resp.raise_for_status()
                poll_json = poll_resp.json()
                
                status_code = poll_json.get("status")
                request_val = poll_json.get("request")
                
                if status_code == 1:
                    logger.info(f"CAPTCHA solved successfully: {request_val}")
                    return request_val
                elif request_val == "CAPCHA_NOT_READY":
                    logger.info(f"CAPTCHA not ready yet (attempt {attempt + 1})...")
                    continue
                else:
                    logger.error(f"2Captcha solving error: {request_val}")
                    raise Exception(f"2Captcha solver returned: {request_val}")
                    
            raise TimeoutError("CAPTCHA solving request timed out.")
            
        except Exception as e:
            logger.error(f"Error communicating with 2Captcha API: {e}")
            raise e
