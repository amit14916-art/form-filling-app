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

        return eligible_exams
