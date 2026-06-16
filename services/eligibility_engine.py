import logging
from datetime import date
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

        # Qualification levels hierarchy
        QUAL_LEVELS = {
            "10th": 1,
            "12th": 2,
            "Graduate": 3,
            "Post Graduate": 4
        }
        user_qual_level = QUAL_LEVELS.get(profile.qualification, 3)

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
            # Base ranges for govt exams: 18 to 32.
            # Relaxations: OBC +3 years (35), SC/ST +5 years (37).
            min_age = 18
            max_age = 32
            user_category = profile.category.upper()
            if user_category == "OBC":
                max_age = 35
            elif user_category in ("SC", "ST"):
                max_age = 37

            if age < min_age:
                reasons.append(f"Age restriction: User age is {age}, minimum required is {min_age}.")
            elif age > max_age:
                reasons.append(f"Age restriction: User age is {age}, maximum allowed for {user_category} is {max_age}.")

            # 3. Qualification Match
            required_level = 1  # base secondary school / matric
            if "post graduate" in exam_name_lower or "post graduate" in guidelines_lower or "master" in exam_name_lower:
                required_level = 4
            elif "graduate" in exam_name_lower or "graduate" in guidelines_lower or "degree" in exam_name_lower or "bachelor" in exam_name_lower:
                required_level = 3
            elif "inter" in exam_name_lower or "12th" in exam_name_lower or "12th" in guidelines_lower or "higher secondary" in exam_name_lower:
                required_level = 2

            if user_qual_level < required_level:
                req_qual_str = next((k for k, v in QUAL_LEVELS.items() if v == required_level), "Higher qualification")
                reasons.append(f"Qualification mismatch: User is '{profile.qualification}', requires '{req_qual_str}'.")

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

            # Note: We do not add missing documents to reasons list so that the candidate
            # is still marked as eligible to apply (allowing them to upload documents later).
            pass

            # Fee and fee waiver logic
            is_woman = profile.gender.strip().lower() in ("female", "woman", "women")
            is_sc_st = user_category in ("SC", "ST")
            category_fee_waiver = is_woman or is_sc_st

            fee = 500
            if "upsc" in exam_name_lower or "ssc" in exam_name_lower:
                fee = 100
            elif "ibps" in exam_name_lower:
                fee = 850
            elif "jee" in exam_name_lower or "neet" in exam_name_lower:
                fee = 1000

            eligible = (len(reasons) == 0)

            return {
                "exam_name": exam_name,
                "conducting_body": exam.get("conducting_body", "Govt Board"),
                "portal_url": exam["portal_url"],
                "eligible": eligible,
                "reasons": reasons,
                "fee": fee,
                "category_fee_waiver": category_fee_waiver,
                "missing_documents": missing_docs
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

        return eligible_exams
