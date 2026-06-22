import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import httpx
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCPAlertServer")

mcp = FastMCP("AlertCommunicator")

@mcp.tool()
async def alert_send_slack(webhook_url: str, message: str, channel: str = None) -> str:
    """
    Sends a notification message to a Slack channel using an incoming webhook URL.
    """
    try:
        if not webhook_url or not message:
            return "ERROR: Missing webhook_url or message."
            
        if webhook_url == "your-slack-webhook-url-here" or not webhook_url.startswith("https://hooks.slack.com/"):
            logger.info(f"[MCPAlertServer] Slack webhook mock routing: Channel: '{channel}', Message: '{message}'")
            return f"SUCCESS: Mock Slack alert dispatched to '{channel}' channel."
            
        payload = {"text": message}
        if channel:
            payload["channel"] = channel
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            
        logger.info(f"[MCPAlertServer] Slack message sent to channel: '{channel}'")
        return "SUCCESS: Slack message dispatched successfully."
    except Exception as e:
        logger.error(f"[MCPAlertServer] Slack dispatch failed: {e}")
        return f"ERROR: Slack send failed: {str(e)}"

@mcp.tool()
async def alert_send_whatsapp(phone: str, message: str) -> str:
    """
    Dispatches a WhatsApp notification message to the specified phone number.
    Uses mock service or Twilio wrapper logic based on environment vars.
    """
    try:
        if not phone or not message:
            return "ERROR: Missing phone or message."
            
        # Clean/normalize phone
        clean_phone = phone.strip().replace(" ", "").replace("-", "")
        
        # Check for Twilio auth in environment to support live dispatch
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER") # e.g. 'whatsapp:+14155238886'
        
        if account_sid and auth_token and twilio_number:
            logger.info(f"[MCPAlertServer] Twilio credentials found. Attempting live WhatsApp dispatch to {clean_phone}...")
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            auth = (account_sid, auth_token)
            data = {
                "From": twilio_number,
                "To": f"whatsapp:{clean_phone}",
                "Body": message
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, auth=auth, data=data)
                res.raise_for_status()
            logger.info(f"[MCPAlertServer] Live WhatsApp message sent successfully via Twilio to {clean_phone}")
            return f"SUCCESS: WhatsApp message sent via Twilio to {clean_phone}."
        else:
            # Fallback simulator mode
            logger.info(f"[MCPAlertServer] Simulator WhatsApp dispatch: To: {clean_phone}, Msg: '{message}'")
            return f"SUCCESS: Simulated WhatsApp message sent to {clean_phone}."
            
    except Exception as e:
        logger.error(f"[MCPAlertServer] WhatsApp dispatch failed: {e}")
        return f"ERROR: WhatsApp send failed: {str(e)}"

@mcp.tool()
async def alert_send_email(recipient: str, subject: str, body: str) -> str:
    """
    Sends an email alert notification using configured SMTP settings or local server simulator.
    """
    try:
        if not recipient or not subject or not body:
            return "ERROR: Missing recipient, subject, or body."
            
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = os.getenv("SMTP_PORT", "587")
        smtp_user = os.getenv("SMTP_USERNAME")
        smtp_pass = os.getenv("SMTP_PASSWORD")
        
        if smtp_server and smtp_user and smtp_pass:
            import smtplib
            from email.mime.text import MIMEText
            
            logger.info(f"[MCPAlertServer] SMTP server configured. Preparing email alert to {recipient}...")
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = recipient
            
            # Send using SMTP library asynchronously (run in executor since smtplib is blocking)
            import asyncio
            def send_sync():
                with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            
            await asyncio.get_event_loop().run_in_executor(None, send_sync)
            logger.info(f"[MCPAlertServer] Email alert sent successfully to {recipient}")
            return f"SUCCESS: Email sent to {recipient}."
        else:
            # Fallback simulator mode
            logger.info(f"[MCPAlertServer] Simulator Email: To: {recipient}, Subj: '{subject}', Body: '{body}'")
            return f"SUCCESS: Simulated email notification sent to {recipient}."
            
    except Exception as e:
        logger.error(f"[MCPAlertServer] Email send failed: {e}")
        return f"ERROR: Email send failed: {str(e)}"

if __name__ == "__main__":
    mcp.run()
