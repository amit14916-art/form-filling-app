import re
import math
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger("RAGEngine")

class SimpleVectorStore:
    """
    A lightweight, in-memory TF-IDF + Cosine Similarity semantic search engine.
    Requires no heavy PyTorch/database dependencies, ensuring portability.
    """
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        
    def _tokenize(self, text: str) -> List[str]:
        # Tokenize and normalize terms
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
        
    def add_document(self, doc_id: str, text: str, metadata: Dict[str, Any]):
        tokens = self._tokenize(text)
        tf: Dict[str, float] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0.0) + 1.0
        
        # Term Frequency normalization
        total_terms = sum(tf.values())
        if total_terms > 0:
            for token in tf:
                tf[token] /= total_terms
                
        self.documents.append({
            "doc_id": doc_id,
            "text": text,
            "tf": tf,
            "metadata": metadata
        })
        self._recalculate_idf()
        
    def _recalculate_idf(self):
        n_docs = len(self.documents)
        term_doc_counts: Dict[str, int] = {}
        vocab_set = set()
        for doc in self.documents:
            for token in doc["tf"]:
                term_doc_counts[token] = term_doc_counts.get(token, 0) + 1
                vocab_set.add(token)
                
        self.vocab = {token: idx for idx, token in enumerate(vocab_set)}
        self.idf = {}
        for token, count in term_doc_counts.items():
            self.idf[token] = math.log((1.0 + n_docs) / (1.0 + count)) + 1.0
            
    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        if not self.documents:
            return []
            
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [(doc, 0.0) for doc in self.documents[:top_k]]
            
        query_tf: Dict[str, float] = {}
        for token in query_tokens:
            query_tf[token] = query_tf.get(token, 0.0) + 1.0
        total_q_terms = sum(query_tf.values())
        for token in query_tf:
            query_tf[token] /= total_q_terms
            
        query_vector: Dict[str, float] = {}
        for token, tf_val in query_tf.items():
            if token in self.idf:
                query_vector[token] = tf_val * self.idf[token]
                
        scores = []
        for doc in self.documents:
            doc_vector = {token: tf_val * self.idf.get(token, 0.0) for token, tf_val in doc["tf"].items()}
            
            # Dot product
            dot_product = 0.0
            for token, val in query_vector.items():
                if token in doc_vector:
                    dot_product += val * doc_vector[token]
                    
            # Magnitudes
            mag_q = math.sqrt(sum(v*v for v in query_vector.values()))
            mag_d = math.sqrt(sum(v*v for v in doc_vector.values()))
            
            similarity = 0.0
            if mag_q > 0 and mag_d > 0:
                similarity = dot_product / (mag_q * mag_d)
                
            scores.append((doc, similarity))
            
        # Sort by similarity score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class RAGEngine:
    """
    RAG Engine that coordinates:
    1. Healing Index: Searches for resolved CSS selectors based on previous UI failures.
    2. Guidelines Index: Searches validation specifications (Regex patterns) for input keys.
    """
    def __init__(self):
        self.healing_store = SimpleVectorStore()
        self.guidelines_store = SimpleVectorStore()
        self._seed_default_guidelines()
        
    def _seed_default_guidelines(self):
        # Seed standard fields with validation regexes
        self.add_guideline(
            field_name="aadhaar",
            description="Aadhaar card must contain exactly 12 numeric digits.",
            regex_pattern=r"^\d{12}$"
        )
        self.add_guideline(
            field_name="phone",
            description="Phone number must contain exactly 10 digits.",
            regex_pattern=r"^\d{10}$"
        )
        self.add_guideline(
            field_name="user_number",
            description="User phone number must contain exactly 10 digits.",
            regex_pattern=r"^\d{10}$"
        )
        self.add_guideline(
            field_name="user_email",
            description="User email must represent a valid email format.",
            regex_pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        )
        self.add_guideline(
            field_name="user_name",
            description="Name must contain only alphabetic characters and spaces.",
            regex_pattern=r"^[a-zA-Z\s]+$"
        )
        logger.info("Default validation guidelines successfully seeded into RAG guidelines vector store.")
        
        # Load and seed the complete Indian Exam portal database
        try:
            from swarm_core.exam_data_seed import seed_exam_database
            seed_exam_database(self)
        except Exception as e:
            logger.error(f"Failed to seed Indian Govt Exam database: {e}")
        
    def add_healing_record(self, failed_selector: str, error_message: str, dom_snippet: str, healed_selector: str):
        text_to_index = f"failed: {failed_selector} error: {error_message} dom: {dom_snippet}"
        metadata = {
            "failed_selector": failed_selector,
            "error_message": error_message,
            "healed_selector": healed_selector,
            "dom_snippet": dom_snippet
        }
        doc_id = f"healing_{len(self.healing_store.documents)}"
        self.healing_store.add_document(doc_id, text_to_index, metadata)
        logger.info(f"RAG: Added healing record for '{failed_selector}' -> '{healed_selector}'.")
        
    def search_healing_solution(self, failed_selector: str, error_message: str, current_dom: str) -> Optional[str]:
        query = f"failed: {failed_selector} error: {error_message} dom: {current_dom}"
        results = self.healing_store.retrieve(query, top_k=1)
        if results and results[0][1] > 0.1:  # Similarity score threshold
            healed = results[0][0]["metadata"]["healed_selector"]
            logger.info(f"RAG Match found for healing: similarity={results[0][1]:.2f}. Suggested: '{healed}'")
            return healed
        return None
        
    def add_guideline(self, field_name: str, description: str, regex_pattern: Optional[str] = None):
        text_to_index = f"field: {field_name} description: {description} pattern: {regex_pattern or ''}"
        metadata = {
            "field_name": field_name,
            "description": description,
            "regex_pattern": regex_pattern
        }
        doc_id = f"guidelines_{len(self.guidelines_store.documents)}"
        self.guidelines_store.add_document(doc_id, text_to_index, metadata)
        
    def search_guidelines_for_field(self, field_name: str) -> List[Dict[str, Any]]:
        results = self.guidelines_store.retrieve(field_name, top_k=2)
        # Filter matching results with similarity score greater than 0.1
        return [res[0]["metadata"] for res in results if res[1] > 0.1]

# Global Singleton instance
rag_engine = RAGEngine()
