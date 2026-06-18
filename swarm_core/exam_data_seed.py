# Database of Indian Government Exam Portals and Guidelines
from datetime import date, timedelta

def get_dynamic_last_date(target_date_str: str) -> str:
    return target_date_str

EXAM_DATABASE = {
    "Central": [
        {
            "exam_name": "UPSC Civil Services 2026",
            "conducting_body": "Union Public Service Commission",
            "portal_url": "https://upsconline.nic.in",
            "age_min": 21,
            "age_max": 32,
            "qualification": "Graduate",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-20",
            "guidelines": "Aadhaar Card or Govt ID card mandatory. Photo size: 20KB to 300KB (JPG). Signature size: 20KB to 300KB (JPG)."
        },
        {
            "exam_name": "SSC CGL 2026",
            "conducting_body": "Staff Selection Commission",
            "portal_url": "https://ssc.gov.in",
            "age_min": 18,
            "age_max": 32,
            "qualification": "Graduate",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-07-25",
            "guidelines": "Live photo capture via website app or app upload. Signature size: 10KB to 20KB (JPG)."
        },
        {
            "exam_name": "SSC CHSL 2026",
            "conducting_body": "Staff Selection Commission",
            "portal_url": "https://ssc.gov.in",
            "age_min": 18,
            "age_max": 27,
            "qualification": "12th",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-10",
            "guidelines": "12th marksheets upload."
        },
        {
            "exam_name": "SSC MTS 2026",
            "conducting_body": "Staff Selection Commission",
            "portal_url": "https://ssc.gov.in",
            "age_min": 18,
            "age_max": 25,
            "qualification": "10th",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-20",
            "guidelines": "10th pass qualification guidelines."
        },
        {
            "exam_name": "SSC GD Constable 2026",
            "conducting_body": "Staff Selection Commission",
            "portal_url": "https://ssc.gov.in",
            "age_min": 18,
            "age_max": 23,
            "qualification": "10th",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-09-01",
            "guidelines": "Physical measurement rules."
        },
        {
            "exam_name": "SSC CPO 2026",
            "conducting_body": "Staff Selection Commission",
            "portal_url": "https://ssc.gov.in",
            "age_min": 20,
            "age_max": 25,
            "qualification": "Graduate",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-15",
            "guidelines": "Sub-inspector recruitment."
        },
        {
            "exam_name": "SSC Stenographer 2026",
            "conducting_body": "Staff Selection Commission",
            "portal_url": "https://ssc.gov.in",
            "age_min": 18,
            "age_max": 27,
            "qualification": "12th",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-30",
            "guidelines": "Stenography requirements."
        },
        {
            "exam_name": "RRB NTPC 2026",
            "conducting_body": "Railway Recruitment Board",
            "portal_url": "https://rrbcdg.gov.in",
            "age_min": 18,
            "age_max": 33,
            "qualification": "Graduate",
            "fees": {"GEN": 500, "OBC": 500, "SC": 250, "ST": 250, "EWS": 500, "PH": 250, "EX": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-10",
            "guidelines": "Photo: 30KB-70KB (JPG). Signature: 30KB-70KB (JPG)."
        },
        {
            "exam_name": "RRB Group D 2026",
            "conducting_body": "Railway Recruitment Board",
            "portal_url": "https://rrbcdg.gov.in",
            "age_min": 18,
            "age_max": 33,
            "qualification": "10th",
            "fees": {"GEN": 500, "OBC": 500, "SC": 250, "ST": 250, "EWS": 500, "PH": 250, "EX": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-25",
            "guidelines": "Assistant posts."
        },
        {
            "exam_name": "RRB ALP 2026",
            "conducting_body": "Railway Recruitment Board",
            "portal_url": "https://rrbcdg.gov.in",
            "age_min": 18,
            "age_max": 28,
            "qualification": "Diploma",
            "fees": {"GEN": 500, "OBC": 500, "SC": 250, "ST": 250, "EWS": 500, "PH": 250, "EX": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-09-05",
            "guidelines": "Loco pilot posts."
        },
        {
            "exam_name": "RRB JE 2026",
            "conducting_body": "Railway Recruitment Board",
            "portal_url": "https://rrbcdg.gov.in",
            "age_min": 18,
            "age_max": 33,
            "qualification": "Diploma",
            "fees": {"GEN": 500, "OBC": 500, "SC": 250, "ST": 250, "EWS": 500, "PH": 250, "EX": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-09-10",
            "guidelines": "Junior Engineer posts."
        },
        {
            "exam_name": "IBPS PO 2026",
            "conducting_body": "Institute of Banking Personnel Selection",
            "portal_url": "https://ibps.in",
            "age_min": 20,
            "age_max": 30,
            "qualification": "Graduate",
            "fees": {"GEN": 850, "OBC": 850, "SC": 175, "ST": 175, "EWS": 850, "PH": 175},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-07-15",
            "guidelines": "Photo: 20KB-50KB (JPG). Signature: 10KB-20KB (JPG)."
        },
        {
            "exam_name": "IBPS Clerk 2026",
            "conducting_body": "Institute of Banking Personnel Selection",
            "portal_url": "https://ibps.in",
            "age_min": 20,
            "age_max": 28,
            "qualification": "Graduate",
            "fees": {"GEN": 850, "OBC": 850, "SC": 175, "ST": 175, "EWS": 850, "PH": 175},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-01",
            "guidelines": "Clerical bank posts."
        },
        {
            "exam_name": "IBPS SO 2026",
            "conducting_body": "Institute of Banking Personnel Selection",
            "portal_url": "https://ibps.in",
            "age_min": 20,
            "age_max": 30,
            "qualification": "Graduate",
            "fees": {"GEN": 850, "OBC": 850, "SC": 175, "ST": 175, "EWS": 850, "PH": 175},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-10-01",
            "guidelines": "Specialist Officer details."
        },
        {
            "exam_name": "IBPS RRB PO 2026",
            "conducting_body": "Institute of Banking Personnel Selection",
            "portal_url": "https://ibps.in",
            "age_min": 18,
            "age_max": 40,
            "qualification": "Graduate",
            "fees": {"GEN": 850, "OBC": 850, "SC": 175, "ST": 175, "EWS": 850, "PH": 175},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-07-20",
            "guidelines": "Regional rural bank officer posts."
        },
        {
            "exam_name": "IBPS RRB Clerk 2026",
            "conducting_body": "Institute of Banking Personnel Selection",
            "portal_url": "https://ibps.in",
            "age_min": 18,
            "age_max": 28,
            "qualification": "Graduate",
            "fees": {"GEN": 850, "OBC": 850, "SC": 175, "ST": 175, "EWS": 850, "PH": 175},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-07-20",
            "guidelines": "Regional rural bank assistant posts."
        },
        {
            "exam_name": "SBI PO 2026",
            "conducting_body": "State Bank of India",
            "portal_url": "https://sbi.co.in/careers",
            "age_min": 21,
            "age_max": 30,
            "qualification": "Graduate",
            "fees": {"GEN": 750, "OBC": 750, "SC": 0, "ST": 0, "EWS": 750, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-05",
            "guidelines": "SBI officer recruitment."
        },
        {
            "exam_name": "SBI Clerk 2026",
            "conducting_body": "State Bank of India",
            "portal_url": "https://sbi.co.in/careers",
            "age_min": 20,
            "age_max": 28,
            "qualification": "Graduate",
            "fees": {"GEN": 750, "OBC": 750, "SC": 0, "ST": 0, "EWS": 750, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-07-18",
            "guidelines": "Photo: 20KB-50KB (JPG). Signature: 10KB-20KB (JPG)."
        },
        {
            "exam_name": "SBI SO 2026",
            "conducting_body": "State Bank of India",
            "portal_url": "https://sbi.co.in/careers",
            "age_min": 21,
            "age_max": 35,
            "qualification": "Graduate",
            "fees": {"GEN": 750, "OBC": 750, "SC": 0, "ST": 0, "EWS": 750, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-09-01",
            "guidelines": "SBI specialist officer posts."
        },
        {
            "exam_name": "CRPF Constable 2026",
            "conducting_body": "Central Reserve Police Force",
            "portal_url": "https://crpf.gov.in",
            "age_min": 18,
            "age_max": 25,
            "qualification": "10th Pass",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"SC": 5, "ST": 5},
            "last_date": "2026-07-30",
            "guidelines": "Photo: 50KB max. Signature: 20KB max."
        },
        {
            "exam_name": "BSF Constable 2026",
            "conducting_body": "Border Security Force",
            "portal_url": "https://rectt.bsf.gov.in",
            "age_min": 18,
            "age_max": 23,
            "qualification": "10th",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-15",
            "guidelines": "BSF constable parameters."
        },
        {
            "exam_name": "CISF Constable 2026",
            "conducting_body": "Central Industrial Security Force",
            "portal_url": "https://cisfrectt.cisf.gov.in",
            "age_min": 18,
            "age_max": 23,
            "qualification": "10th",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-08-20",
            "guidelines": "CISF constable guidelines."
        },
        {
            "exam_name": "ITBP Constable 2026",
            "conducting_body": "Indo-Tibetan Border Police",
            "portal_url": "https://recruitment.itbpolice.nic.in",
            "age_min": 18,
            "age_max": 25,
            "qualification": "10th",
            "fees": {"GEN": 100, "OBC": 100, "SC": 0, "ST": 0, "EWS": 100, "PH": 0},
            "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
            "last_date": "2026-09-01",
            "guidelines": "ITBP recruitment parameters."
        },
        {
            "exam_name": "Indian Army Agniveer 2026",
            "conducting_body": "Indian Army",
            "portal_url": "https://joinindianarmy.nic.in",
            "age_min": 17,
            "age_max": 23,
            "qualification": "10th",
            "fees": {"GEN": 0, "OBC": 0, "SC": 0, "ST": 0, "EWS": 0, "PH": 0},
            "relaxations": {},
            "last_date": "2026-08-01",
            "guidelines": "Agniveer details."
        },
        {
            "exam_name": "Indian Navy Agniveer 2026",
            "conducting_body": "Indian Navy",
            "portal_url": "https://joinindiannavy.gov.in",
            "age_min": 17,
            "age_max": 21,
            "qualification": "10th",
            "fees": {"GEN": 0, "OBC": 0, "SC": 0, "ST": 0, "EWS": 0, "PH": 0},
            "relaxations": {},
            "last_date": "2026-07-25",
            "guidelines": "Navy Agniveer recruitment."
        },
        {
            "exam_name": "HAL Apprentice 2026",
            "conducting_body": "Hindustan Aeronautics Limited",
            "portal_url": "https://hal-india.co.in",
            "age_min": 18,
            "age_max": 27,
            "qualification": "Diploma",
            "fees": {"GEN": 0, "OBC": 0, "SC": 0, "ST": 0, "EWS": 0, "PH": 0, "EX": 0},
            "relaxations": {},
            "last_date": "2026-08-05",
            "guidelines": "Free application Trade Apprentice guidelines."
        },
        {
            "exam_name": "BHEL Apprentice 2026",
            "conducting_body": "Bharat Heavy Electricals Limited",
            "portal_url": "https://bhel.com",
            "age_min": 18,
            "age_max": 27,
            "qualification": "Diploma",
            "fees": {"GEN": 0, "OBC": 0, "SC": 0, "ST": 0, "EWS": 0, "PH": 0, "EX": 0},
            "relaxations": {},
            "last_date": "2026-08-10",
            "guidelines": "BHEL trade apprentice guidelines."
        },
        {
            "exam_name": "ONGC Apprentice 2026",
            "conducting_body": "Oil and Natural Gas Corporation",
            "portal_url": "https://ongcindia.com",
            "age_min": 18,
            "age_max": 24,
            "qualification": "Diploma",
            "fees": {"GEN": 0, "OBC": 0, "SC": 0, "ST": 0, "EWS": 0, "PH": 0, "EX": 0},
            "relaxations": {},
            "last_date": "2026-08-20",
            "guidelines": "ONGC apprentice guidelines."
        },
        {
            "exam_name": "BSNL Apprentice 2026",
            "conducting_body": "Bharat Sanchar Nigam Limited",
            "portal_url": "https://bsnl.co.in",
            "age_min": 18,
            "age_max": 25,
            "qualification": "Diploma",
            "fees": {"GEN": 0, "OBC": 0, "SC": 0, "ST": 0, "EWS": 0, "PH": 0, "EX": 0},
            "relaxations": {},
            "last_date": "2026-08-15",
            "guidelines": "BSNL apprentice guidelines."
        },
        {
            "exam_name": "CTET 2026",
            "conducting_body": "Central Board of Secondary Education",
            "portal_url": "https://ctet.nic.in",
            "age_min": 18,
            "age_max": 35,
            "qualification": "Graduate",
            "fees": {"GEN": 1000, "OBC": 1000, "SC": 500, "ST": 500, "EWS": 1000, "PH": 500},
            "relaxations": {},
            "last_date": "2026-07-20",
            "guidelines": "Teacher eligibility test requirements."
        },
        {
            "exam_name": "NVS Teacher 2026",
            "conducting_body": "Navodaya Vidyalaya Samiti",
            "portal_url": "https://navodaya.gov.in",
            "age_min": 21,
            "age_max": 35,
            "qualification": "Graduate",
            "fees": {"GEN": 1200, "OBC": 600, "SC": 0, "ST": 0, "EWS": 1200, "PH": 0},
            "relaxations": {},
            "last_date": "2026-08-01",
            "guidelines": "NVS teacher details."
        },
        {
            "exam_name": "NTA JEE Main 2026",
            "conducting_body": "National Testing Agency",
            "portal_url": "https://jeemain.nta.ac.in",
            "age_min": 17,
            "age_max": 25,
            "qualification": "12th",
            "fees": {"GEN": 1000, "OBC": 1000, "SC": 500, "ST": 500, "EWS": 1000, "PH": 500},
            "relaxations": {},
            "last_date": "2026-07-20",
            "guidelines": "JEE Main details."
        },
        {
            "exam_name": "NTA NEET UG 2026",
            "conducting_body": "National Testing Agency",
            "portal_url": "https://neet.nta.nic.in",
            "age_min": 17,
            "age_max": 25,
            "qualification": "12th",
            "fees": {"GEN": 1700, "OBC": 1700, "SC": 1000, "ST": 1000, "EWS": 1700, "PH": 1000},
            "relaxations": {},
            "last_date": "2026-07-15",
            "guidelines": "NEET details."
        },
        {
            "exam_name": "NTA CUET 2026",
            "conducting_body": "National Testing Agency",
            "portal_url": "https://cuet.samarth.ac.in",
            "age_min": 17,
            "age_max": 35,
            "qualification": "12th",
            "fees": {"GEN": 650, "OBC": 600, "SC": 550, "ST": 550, "EWS": 650, "PH": 550},
            "relaxations": {},
            "last_date": "2026-07-10",
            "guidelines": "CUET details."
        }
    ],
    "State_wise": {
        "Bihar": [
            {
                "exam_name": "BPSC 70th CCE 2026",
                "conducting_body": "Bihar Public Service Commission (BPSC)",
                "portal_url": "https://bpsc.bih.nic.in",
                "age_min": 20,
                "age_max": 37,
                "qualification": "Graduate",
                "fees": {"GEN": 600, "OBC": 150, "SC": 150, "ST": 150, "EWS": 600, "PH": 150, "EX": 0},
                "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
                "last_date": "2026-08-15",
                "guidelines": "Aadhaar Card mandatory. Live web-cam photo capture required during submission."
            }
        ],
        "Uttar Pradesh": [
            {
                "exam_name": "UPPSC PCS 2026",
                "conducting_body": "Uttar Pradesh Public Service Commission",
                "portal_url": "https://uppsc.up.nic.in",
                "age_min": 21,
                "age_max": 40,
                "qualification": "Graduate",
                "fees": {"GEN": 125, "OBC": 65, "SC": 65, "ST": 65, "EWS": 125, "PH": 0},
                "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
                "last_date": "2026-08-20",
                "guidelines": "UPPSC details."
            }
        ],
        "Maharashtra": [
            {
                "exam_name": "MPSC State Service 2026",
                "conducting_body": "Maharashtra Public Service Commission",
                "portal_url": "https://mpsc.gov.in",
                "age_min": 19,
                "age_max": 38,
                "qualification": "Graduate",
                "fees": {"GEN": 524, "OBC": 324, "SC": 324, "ST": 324, "EWS": 524, "PH": 0},
                "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
                "last_date": "2026-08-01",
                "guidelines": "MPSC details."
            }
        ],
        "Rajasthan": [
            {
                "exam_name": "RPSC RAS 2026",
                "conducting_body": "Rajasthan Public Service Commission",
                "portal_url": "https://rpsc.rajasthan.gov.in",
                "age_min": 21,
                "age_max": 40,
                "qualification": "Graduate",
                "fees": {"GEN": 350, "OBC": 250, "SC": 150, "ST": 150, "EWS": 350, "PH": 0},
                "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
                "last_date": "2026-09-01",
                "guidelines": "RPSC details."
            }
        ],
        "Delhi": [
            {
                "exam_name": "DSSSB 2026",
                "conducting_body": "Delhi Subordinate Services Selection Board",
                "portal_url": "https://dsssbonline.nic.in",
                "age_min": 18,
                "age_max": 32,
                "qualification": "Graduate",
                "fees": {"GEN": 500, "OBC": 500, "SC": 0, "ST": 0, "EWS": 500, "PH": 0},
                "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
                "last_date": "2026-08-05",
                "guidelines": "DSSSB details."
            }
        ],
        "Uttarakhand": [
            {
                "exam_name": "UKPSC 2026",
                "conducting_body": "Uttarakhand Public Service Commission",
                "portal_url": "https://ukpsc.gov.in",
                "age_min": 21,
                "age_max": 42,
                "qualification": "Graduate",
                "fees": {"GEN": 172, "OBC": 82, "SC": 45, "ST": 45, "EWS": 172, "PH": 0},
                "relaxations": {"OBC": 3, "SC": 5, "ST": 5},
                "last_date": "2026-08-10",
                "guidelines": "UKPSC details."
            }
        ]
    },
    "Union_Territories": []
}

def seed_exam_database(rag_engine_instance):
    """
    Feeds the comprehensive central and state-wise Indian exam database into the RAG Guidelines index.
    """
    # 1. Seed Central Exams
    for exam in EXAM_DATABASE["Central"]:
        text_content = (
            f"Exam: {exam['exam_name']} | Conducting Body: {exam['conducting_body']} | "
            f"Portal URL: {exam['portal_url']} | Guidelines: {exam['guidelines']}"
        )
        metadata = {
            "exam_name": exam["exam_name"],
            "conducting_body": exam["conducting_body"],
            "portal_url": exam["portal_url"],
            "guidelines": exam["guidelines"],
            "category": "Central"
        }
        doc_id = f"exam_central_{exam['conducting_body'].lower().replace(' ', '_')}"
        rag_engine_instance.guidelines_store.add_document(doc_id, text_content, metadata)
        
    # 2. Seed State Exams
    for state, exams in EXAM_DATABASE["State_wise"].items():
        for exam in exams:
            text_content = (
                f"State: {state} | Exam: {exam['exam_name']} | Conducting Body: {exam['conducting_body']} | "
                f"Portal URL: {exam['portal_url']} | Guidelines: {exam['guidelines']}"
            )
            metadata = {
                "state": state,
                "exam_name": exam["exam_name"],
                "conducting_body": exam["conducting_body"],
                "portal_url": exam["portal_url"],
                "guidelines": exam["guidelines"],
                "category": "State"
            }
            doc_id = f"exam_state_{state.lower().replace(' ', '_')}_{exam['conducting_body'].lower().replace(' ', '_')}"
            rag_engine_instance.guidelines_store.add_document(doc_id, text_content, metadata)
            
    # 3. Seed Union Territory Exams
    for exam in EXAM_DATABASE["Union_Territories"]:
        text_content = (
            f"Exam: {exam['exam_name']} | Conducting Body: {exam['conducting_body']} | "
            f"Portal URL: {exam['portal_url']} | Guidelines: {exam['guidelines']}"
        )
        metadata = {
            "exam_name": exam["exam_name"],
            "conducting_body": exam["conducting_body"],
            "portal_url": exam["portal_url"],
            "guidelines": exam["guidelines"],
            "category": "Union_Territory"
        }
        doc_id = f"exam_ut_{exam['conducting_body'].lower().replace(' ', '_')}"
        rag_engine_instance.guidelines_store.add_document(doc_id, text_content, metadata)

    import logging
    logger = logging.getLogger("RAGEngine")
    logger.info(f"Indian Govt Exam Database seeded: Ingested {len(EXAM_DATABASE['Central'])} Central, "
                f"{sum(len(v) for v in EXAM_DATABASE['State_wise'].values())} State, "
                f"and {len(EXAM_DATABASE['Union_Territories'])} Union Territory exam guidelines.")
