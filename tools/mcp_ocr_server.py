import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import json
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCPOCRServer")

mcp = FastMCP("OCRProcessor")

@mcp.tool()
async def ocr_extract_text(file_path: str) -> str:
    """
    Simulates or performs OCR text extraction on the provided image or document file path.
    Recognizes file names like 'aadhaar' or 'pan' to return structured fields.
    """
    try:
        # Resolve to absolute path
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            # If the file does not exist, return a mock response based on filename
            filename = os.path.basename(file_path).lower()
            logger.warning(f"[MCPOCRServer] File not found: '{abs_path}'. Using simulator fallback.")
        else:
            filename = os.path.basename(abs_path).lower()
            
        logger.info(f"[MCPOCRServer] Performing extraction on '{filename}'")
        
        # Simulated extraction based on common document patterns
        if "aadhaar" in filename:
            data = {
                "document_type": "Aadhaar Card",
                "extracted_fields": {
                    "aadhaar_number": "1234-5678-9012",
                    "full_name": "Amit Prasad",
                    "dob": "1995-08-15",
                    "gender": "Male"
                },
                "confidence": 0.98
            }
        elif "pan" in filename:
            data = {
                "document_type": "PAN Card",
                "extracted_fields": {
                    "pan_number": "ABCDE1234F",
                    "full_name": "Amit Prasad",
                    "dob": "1995-08-15"
                },
                "confidence": 0.97
            }
        elif "signature" in filename:
            data = {
                "document_type": "Signature Scan",
                "extracted_fields": {
                    "signature_verified": "TRUE",
                    "background_clean": "TRUE"
                },
                "confidence": 0.92
            }
        else:
            # Fallback text extraction if file exists
            if os.path.exists(abs_path) and abs_path.endswith((".txt", ".json", ".xml")):
                with open(abs_path, "r", encoding="utf-8") as f:
                    content = f.read(1000)
                data = {
                    "document_type": "Text File",
                    "extracted_text": content,
                    "confidence": 1.0
                }
            else:
                data = {
                    "document_type": "Generic Document",
                    "extracted_text": "Sample extracted text block from document.",
                    "confidence": 0.80
                }
                
        return json.dumps(data)
    except Exception as e:
        logger.error(f"[MCPOCRServer] Extraction failed: {e}")
        return json.dumps({"error": f"Extraction failed: {str(e)}"})

@mcp.tool()
async def ocr_verify_document_format(file_path: str, expected_type: str) -> str:
    """
    Verifies if a document file path meets size and extension constraints for the expected_type
    (e.g., 'aadhaar_pdf', 'signature_image', 'passport_photo').
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        # Verify file exists
        if not os.path.exists(abs_path):
            # For demonstration, if we pass a simulated path, treat as valid if extension is right
            ext = os.path.splitext(file_path)[1].lower()
            if ext in (".pdf", ".png", ".jpg", ".jpeg"):
                return json.dumps({
                    "valid": True,
                    "details": f"File does not exist on disk, but extension '{ext}' matches expected format.",
                    "mock": True
                })
            return json.dumps({
                "valid": False,
                "error": f"File '{file_path}' does not exist on disk."
            })
            
        file_size_kb = os.path.getsize(abs_path) / 1024.0
        ext = os.path.splitext(abs_path)[1].lower()
        
        expected_type = expected_type.lower()
        
        if "aadhaar" in expected_type or "pdf" in expected_type:
            # Expect PDF or JPEG under 500KB
            if ext not in (".pdf", ".jpg", ".jpeg"):
                return json.dumps({"valid": False, "error": f"Invalid extension '{ext}'. Aadhaar must be PDF, JPG, or JPEG."})
            if file_size_kb > 500.0:
                return json.dumps({"valid": False, "error": f"File size ({file_size_kb:.1f} KB) exceeds maximum limit of 500 KB."})
                
        elif "signature" in expected_type or "photo" in expected_type:
            # Expect PNG or JPEG under 100KB
            if ext not in (".png", ".jpg", ".jpeg"):
                return json.dumps({"valid": False, "error": f"Invalid extension '{ext}'. Photos/Signatures must be PNG, JPG, or JPEG."})
            if file_size_kb > 100.0:
                return json.dumps({"valid": False, "error": f"File size ({file_size_kb:.1f} KB) exceeds maximum limit of 100 KB."})
                
        return json.dumps({
            "valid": True,
            "details": f"File '{os.path.basename(abs_path)}' meets constraints. Size: {file_size_kb:.1f} KB. Extension: '{ext}'"
        })
    except Exception as e:
        return json.dumps({"valid": False, "error": f"Verification error: {str(e)}"})

if __name__ == "__main__":
    mcp.run()
