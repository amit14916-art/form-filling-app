import logging
import asyncio
import requests
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.models import UserProfile, Document
from swarm_core.exam_data_seed import EXAM_DATABASE

logger = logging.getLogger("EligibilityEngine")

class EligibilityEngine:
    @staticmethod
    async def check_user_eligibility(user_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Calculates and evaluates a user's eligibility for all exams in EXAM_DATABASE.
        Checks age limit rules, residency/state matching, qualification matching, and documents.
        """
        # Fetch user profile
        result = await db.execute(select(UserProfile).filter(UserProfile.user_id == user_id))
        profile = result.scalars().first()
        if not profile:
            return []

        # Fetch user documents
        result_docs = await db.execute(select(Document).filter(Document.user_id == user_id))
        docs = result_docs.scalars().all()
        uploaded_doc_types = {d.doc_type for d in docs}

        # Calculate user age
        today = date.today()
        age = today.year - profile.dob.year - ((today.month, today.day) < (profile.dob.month, profile.dob.day))

        eligible_exams = []

        def evaluate_exam(exam: Dict[str, Any], exam_category: str, state_name: Optional[str] = None) -> Dict[str, Any]:
            exam_name = exam["exam_name"]
            guidelines_lower = exam.get("guidelines", "").lower()
            exam_name_lower = exam_name.lower()

            reasons = []

            # 1. State / Domicile Check
            if exam_category == "State":
                if not state_name or profile.state.strip().lower() != state_name.strip().lower():
                    reasons.append(f"Requires residency in {state_name}. User is registered in {profile.state}.")
            elif exam_category == "Union_Territory":
                if "jkpsc" in exam_name_lower or "jammu" in exam_name_lower:
                    if profile.state.strip().lower() not in ("jammu & kashmir", "jammu and kashmir", "j&k", "jk"):
                        reasons.append("Requires residency in Jammu & Kashmir UT.")

            # 2. Age limit Check
            min_age = exam.get("age_min", 18)
            max_age = exam.get("age_max", 32)
            user_category = profile.category.upper()
            
            # Apply category relaxation if defined in exam's relaxations
            relaxation = exam.get("relaxations", {}).get(user_category, 0)
            max_age += relaxation

            if age < min_age:
                reasons.append(f"Age restriction: User age is {age}, minimum required is {min_age}.")
            elif age > max_age:
                reasons.append(f"Age restriction: User age is {age}, maximum allowed for {user_category} is {max_age}.")

            # 3. Qualification Match
            def get_qualification_rank(qual_str: str) -> int:
                q = qual_str.strip().lower()
                if "post" in q:
                    return 4
                elif "grad" in q or "btech" in q or "b.tech" in q or "degree" in q:
                    return 3
                elif "12th" in q or "diploma" in q or "iti" in q or "inter" in q:
                    return 2
                elif "10th" in q or "matric" in q or "secondary" in q or "pass" in q:
                    return 1
                return 1

            user_qual_level = get_qualification_rank(profile.qualification)
            exam_qual_level = get_qualification_rank(exam.get("qualification", "Graduate"))

            if user_qual_level < exam_qual_level:
                reasons.append(f"Qualification mismatch: User is '{profile.qualification}', requires '{exam.get('qualification')}'.")

            # 4. Required Documents Match
            missing_docs = []
            if "photo" in guidelines_lower and "photo" not in uploaded_doc_types:
                missing_docs.append("photo")
            if "signature" in guidelines_lower and "signature" not in uploaded_doc_types:
                missing_docs.append("signature")
            if ("aadhaar" in guidelines_lower or "identity card" in guidelines_lower or "id card" in guidelines_lower or "govt id" in guidelines_lower) and "aadhaar" not in uploaded_doc_types:
                missing_docs.append("aadhaar")
            if ("caste" in guidelines_lower or "sc/st certificate" in guidelines_lower or "category certificate" in guidelines_lower or "non-creamy layer" in guidelines_lower) and user_category != "GEN" and "caste_cert" not in uploaded_doc_types:
                missing_docs.append("caste_cert")
            if "marksheet" in guidelines_lower and "marksheet" not in uploaded_doc_types:
                missing_docs.append("marksheet")

            # Fee lookup
            fees_dict = exam.get("fees", {})
            fee = fees_dict.get(user_category)
            if fee is None:
                fee = fees_dict.get("GEN", 0)

            # Category fee waiver logic
            is_woman = profile.gender.strip().lower() in ("female", "woman", "women")
            is_sc_st = user_category in ("SC", "ST")
            category_fee_waiver = (fee == 0) or is_woman or is_sc_st

            eligible = (len(reasons) == 0)

            return {
                "exam_name": exam_name,
                "conducting_body": exam.get("conducting_body", "Govt Board"),
                "portal_url": exam["portal_url"],
                "eligible": eligible,
                "reasons": reasons,
                "fee": fee,
                "category_fee_waiver": category_fee_waiver,
                "missing_documents": missing_docs,
                "last_date": exam.get("last_date")
            }

        # Central exams
        for exam in EXAM_DATABASE.get("Central", []):
            eligible_exams.append(evaluate_exam(exam, "Central"))

        # State exams (matching user state only)
        user_state = profile.state.strip()
        state_exams = EXAM_DATABASE.get("State_wise", {}).get(user_state, [])
        for exam in state_exams:
            eligible_exams.append(evaluate_exam(exam, "State", user_state))

        # Union Territory exams
        for exam in EXAM_DATABASE.get("Union_Territories", []):
            eligible_exams.append(evaluate_exam(exam, "Union_Territory"))

        # Live Feed exams from FreeJobAlert
        live_exams = await EligibilityEngine.fetch_live_exams_from_feed()
        for exam in live_exams:
            eligible_exams.append(evaluate_exam(exam, "Central"))

        return eligible_exams

    @staticmethod
    async def fetch_live_exams_from_feed() -> List[Dict[str, Any]]:
        """
        Fetches live open job listings from FreeJobAlert RSS feed and compiles them into compatible exam dicts.
        """
        try:
            url = "https://www.freejobalert.com/feed/"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            loop = asyncio.get_event_loop()
            
            def make_request():
                return requests.get(url, headers=headers, timeout=5)
                
            response = await loop.run_in_executor(None, make_request)
            if response.status_code != 200:
                return []
                
            root = ET.fromstring(response.content)
            live_exams = []
            for item in root.findall(".//item")[:15]:
                title = item.find("title").text or ""
                link = item.find("link").text or ""
                
                # Parse qualification from title
                title_lower = title.lower()
                qual = "Graduate"
                if "diploma" in title_lower or "12th" in title_lower or "inter" in title_lower:
                    qual = "12th"
                elif "10th" in title_lower or "matric" in title_lower or "pass" in title_lower:
                    qual = "10th"
                elif "degree" in title_lower or "graduate" in title_lower or "post" in title_lower:
                    qual = "Graduate"
                
                # Parse conducting body
                conducting_body = "Government Board"
                if "upsc" in title_lower:
                    conducting_body = "Union Public Service Commission"
                elif "ssc" in title_lower:
                    conducting_body = "Staff Selection Commission"
                elif "rrb" in title_lower or "railway" in title_lower:
                    conducting_body = "Railway Recruitment Board"
                elif "ibps" in title_lower:
                    conducting_body = "Institute of Banking Personnel Selection"
                elif "bpsc" in title_lower:
                    conducting_body = "Bihar Public Service Commission"
                else:
                    parts = title.split(" - ")
                    if len(parts) > 1:
                        conducting_body = parts[0].strip()
                
                # Parse last date (default to 30 days from now)
                last_date_str = (date.today() + timedelta(days=30)).isoformat()
                
                live_exams.append({
                    "exam_name": title,
                    "conducting_body": conducting_body,
                    "portal_url": link,
                    "age_min": 18,
                    "age_max": 32,
                    "qualification": qual,
                    "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
                    "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
                    "last_date": last_date_str,
                    "guidelines": "Official registration guidelines as per FreeJobAlert portal. Upload photo & signature."
                })
            return live_exams
        except Exception as e:
            logger.error(f"Error fetching live exams from RSS feed: {e}")
            return []
