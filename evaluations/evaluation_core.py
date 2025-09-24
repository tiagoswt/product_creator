"""
Core evaluation logic with PHASE 3 USER TRACKING
ADDED: User context capture and attribution for product creation tracking
"""

import json
import re
import time
from typing import Dict, List, Optional, Tuple
import streamlit as st
from langsmith import traceable

from models.model_factory import get_llm
from .simple_db import get_db
import config as eval_config

# PHASE 3: Import OpenEvals evaluator
try:
    from .metric_evaluator import create_fixed_evaluator

    OPENEVALS_AVAILABLE = True
except ImportError:
    OPENEVALS_AVAILABLE = False


class OpenEvalsProductEvaluator:
    """OpenEvals-powered evaluator with PHASE 3 USER TRACKING."""

    def __init__(self):
        """Initialize with OpenEvals 3-metric evaluator."""
        self.db = get_db()

        # Try to use OpenEvals evaluator first (silently)
        if OPENEVALS_AVAILABLE and getattr(eval_config, "USE_OPENEVALS", True):
            try:
                self.openevals_evaluator = create_fixed_evaluator()
                self.use_openevals = True
            except Exception:
                self.use_openevals = False
                self._init_fallback_evaluator()
        else:
            self.use_openevals = False
            self._init_fallback_evaluator()

    def _init_fallback_evaluator(self):
        """Initialize fallback evaluator if OpenEvals fails."""
        self.evaluation_model = getattr(eval_config, "EVALUATION_MODEL", "gpt-4o-mini")
        self.evaluation_provider = getattr(eval_config, "EVALUATION_PROVIDER", "openai")

        # Simple fallback prompt
        self.fallback_prompt = """You are an expert evaluator assessing product information extraction quality.

INPUT DATA: {input_text}
EXTRACTED OUTPUT: {extracted_json}
PRODUCT TYPE: {product_type}

Rate the extraction on these dimensions (1-5 each):
1. Structure (JSON format and schema compliance)
2. Content (accuracy vs input, no hallucinations)  
3. Translation (Portuguese translation quality)
4. Overall quality

Respond with ONLY valid JSON:
{{
  "structure_score": <1-5>,
  "accuracy_score": <1-5>, 
  "translation_score": <1-5>,
  "overall_score": <1-5>,
  "reasoning": "Brief explanation"
}}"""

    def evaluate_single_product(
        self,
        product_config_id: str,
        input_text: str,
        extracted_result: Dict,
        product_type: str,
        user_id: str = None,
        username: str = None,
        user_name: str = None,
        # NEW: Add production model parameters
        production_model_provider: str = None,
        production_model_name: str = None,
        production_temperature: float = None,
    ) -> Optional[int]:
        """
        PHASE 3: Evaluate a single product extraction with user attribution and production model tracking.

        Args:
            product_config_id: Unique ID for the product configuration
            input_text: Consolidated input text from all sources
            extracted_result: The extracted product JSON data
            product_type: Type of product (cosmetics, fragrance, subtype)
            user_id: UUID of the user who created this product
            username: Username of the creator
            user_name: Full name of the creator
            production_model_provider: Provider used to create the product (groq/openai)
            production_model_name: Model used to create the product
            production_temperature: Temperature used to create the product

        Returns:
            evaluation_id if successful, None if failed.
        """
        try:
            # PHASE 3: Get user context from session state if not provided
            if not user_id and "current_user" in st.session_state:
                current_user = st.session_state["current_user"]
                user_id = current_user.get("id")
                username = current_user.get("username", "unknown")
                user_name = current_user.get("name", "Unknown User")

            if self.use_openevals:
                # Use OpenEvals 3-metric evaluator
                results = self.openevals_evaluator.evaluate_extraction(
                    input_text=input_text[:100000],  # Truncate for efficiency
                    extracted_json=extracted_result,
                    product_type=product_type,
                )

                # UPDATED: Pass production model info to database
                evaluation_id = self.db.store_openevals_evaluation(
                    product_config_id=product_config_id,
                    openevals_results=results,
                    product_type=product_type,
                    input_text=input_text,
                    extracted_json=extracted_result,
                    user_id=user_id,  # PHASE 3: User attribution
                    username=username,  # PHASE 3: User attribution
                    user_name=user_name,  # PHASE 3: User attribution
                    # NEW: Pass production model info
                    production_model_provider=production_model_provider,
                    production_model_name=production_model_name,
                    production_temperature=production_temperature,
                )

                return evaluation_id
            else:
                # Fallback evaluation
                return self._evaluate_with_fallback(
                    product_config_id=product_config_id,
                    input_text=input_text,
                    extracted_result=extracted_result,
                    product_type=product_type,
                    user_id=user_id,  # PHASE 3: User attribution
                    username=username,  # PHASE 3: User attribution
                    user_name=user_name,  # PHASE 3: User attribution
                    # NEW: Pass production model info to fallback too
                    production_model_provider=production_model_provider,
                    production_model_name=production_model_name,
                    production_temperature=production_temperature,
                )

        except Exception:
            # Silent failure - don't clutter UI with evaluation errors
            return None

    def _evaluate_with_fallback(
        self,
        product_config_id: str,
        input_text: str,
        extracted_result: Dict,
        product_type: str,
        user_id: str = None,
        username: str = None,
        user_name: str = None,
        # NEW: Add production model parameters
        production_model_provider: str = None,
        production_model_name: str = None,
        production_temperature: float = None,
    ) -> Optional[int]:
        """PHASE 3: Fallback evaluation using basic LLM with user attribution and production model tracking."""

        try:
            # Get LLM for evaluation
            llm = get_llm(
                model_name=self.evaluation_model,
                temperature=0.1,
                provider=self.evaluation_provider,
            )

            if not llm:
                return None

            # Format the prompt
            prompt = self.fallback_prompt.format(
                input_text=input_text[:5000],  # Truncate for fallback
                extracted_json=json.dumps(extracted_result, indent=2)[:5000],
                product_type=product_type,
            )

            # Get evaluation from LLM
            response = llm.invoke(prompt)

            # Parse JSON response
            try:
                if hasattr(response, "content"):
                    response_text = response.content
                else:
                    response_text = str(response)

                scores = json.loads(response_text)
            except:
                # Default scores if parsing fails
                scores = {
                    "structure_score": 3,
                    "accuracy_score": 3,
                    "translation_score": 3,
                    "overall_score": 3.0,
                    "reasoning": "Fallback evaluation - could not parse LLM response",
                }

            # Store evaluation using the fallback store_evaluation method
            evaluation_id = self.db.store_evaluation(
                product_config_id=product_config_id,
                input_text=input_text,
                extracted_json=extracted_result,
                scores=scores,
                llm_reasoning=scores.get("reasoning", "Fallback evaluation completed"),
                evaluation_model=f"fallback/{self.evaluation_model}",
                product_type=product_type,
                user_id=user_id,
                username=username,
                user_name=user_name,
                # NEW: Add production model parameters
                production_model_provider=production_model_provider,
                production_model_name=production_model_name,
                production_temperature=production_temperature,
            )

            return evaluation_id

        except Exception:
            return None

    def _parse_fallback_response(self, response_text: str) -> Optional[Dict]:
        """Parse fallback LLM response."""
        try:
            # First, try to find JSON in code blocks
            json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object in the response
                json_match = re.search(
                    r'\{[^}]*"score"[^}]*\}', response_text, re.DOTALL
                )
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # Try to extract the whole response as JSON
                    json_str = response_text.strip()

            # Parse the JSON
            parsed = json.loads(json_str)

            score = int(parsed.get("score", 3))
            feedback = parsed.get("feedback", "No feedback provided")

            # Validate score is in range
            score = max(1, min(5, score))

            return {"score": score, "feedback": feedback}

        except:
            return None


@traceable(name="batch_evaluation", tags=["evaluation", "batch", "multi-product"])
def evaluate_batch(completed_configs: List, current_user: Dict = None) -> Dict:
    """
    PHASE 3: Evaluate a batch of completed product configurations with user attribution and production model tracking.

    Args:
        completed_configs: List of completed product configurations
        current_user: Current user context from session state
    """
    try:
        import config as evaluation_config
    except ImportError:
        return {"status": "config_not_found", "evaluated": 0}

    if (
        not hasattr(evaluation_config, "EVALUATION_ENABLED")
        or not evaluation_config.EVALUATION_ENABLED
    ):
        return {"status": "disabled", "evaluated": 0}

    # PHASE 3: Get user context from session state if not provided
    if not current_user and "current_user" in st.session_state:
        current_user = st.session_state["current_user"]

    # Extract user info for attribution
    user_id = current_user.get("id") if current_user else None
    username = current_user.get("username", "unknown") if current_user else "system"
    user_name = current_user.get("name", "Unknown User") if current_user else "System"

    # Use OpenEvals evaluator (silent initialization)
    evaluator = OpenEvalsProductEvaluator()
    results = {"status": "completed", "evaluated": 0, "failed": 0, "evaluation_ids": []}

    # No progress tracking or verbose messages - just process silently
    try:
        for product_config in completed_configs:
            try:
                # Get the latest successful extraction
                latest_attempt = product_config.get_latest_attempt()
                if not latest_attempt or latest_attempt.status != "completed":
                    results["failed"] += 1
                    continue

                # FIXED: Reconstruct input text from config sources (more robust)
                input_text = _reconstruct_input_text_robust(product_config)
                if not input_text:
                    results["failed"] += 1
                    continue

                # UPDATED: PHASE 3: Evaluate with user attribution AND production model tracking
                evaluation_id = evaluator.evaluate_single_product(
                    product_config_id=product_config.id,
                    input_text=input_text,
                    extracted_result=latest_attempt.result,
                    product_type=product_config.product_type,
                    user_id=user_id,  # PHASE 3: User attribution
                    username=username,  # PHASE 3: User attribution
                    user_name=user_name,  # PHASE 3: User attribution
                    # NEW: Add production model info from ProductConfig
                    production_model_provider=product_config.model_provider,
                    production_model_name=product_config.model_name,
                    production_temperature=product_config.temperature,
                )

                if evaluation_id:
                    results["evaluated"] += 1
                    results["evaluation_ids"].append(evaluation_id)
                else:
                    results["failed"] += 1

            except Exception:
                results["failed"] += 1

    except Exception:
        # Silent failure
        pass

    return results


def _reconstruct_input_text_robust(product_config) -> str:
    """
    IMPROVED: More robust reconstruction of input text with better error handling.
    """
    try:
        consolidated_text = ""

        # Add PDF content if available
        if product_config.pdf_file and product_config.pdf_pages:
            try:
                from processors.pdf_processor import extract_pdf_data

                pdf_text = extract_pdf_data(
                    product_config.pdf_file, product_config.pdf_pages
                )
                if pdf_text:
                    consolidated_text += f"=== PDF CONTENT ({product_config.pdf_file.name}) ===\n{pdf_text}\n\n"
            except Exception:
                consolidated_text += f"=== PDF CONTENT (Failed to extract from {product_config.pdf_file.name}) ===\n\n"

        # Add Excel content if available
        if product_config.excel_file and product_config.excel_rows:
            try:
                from processors.excel_processor import extract_excel_data

                excel_header_row = getattr(product_config, 'excel_header_row', 0)
                excel_text = extract_excel_data(
                    product_config.excel_file,
                    product_config.excel_rows,
                    excel_header_row,
                )
                if excel_text:
                    consolidated_text += f"=== EXCEL CONTENT ({product_config.excel_file.name}) ===\n{excel_text}\n\n"
            except Exception:
                consolidated_text += f"=== EXCEL CONTENT (Failed to extract from {product_config.excel_file.name}) ===\n\n"

        # Add website content if available
        if product_config.website_url:
            try:
                from processors.web_processor import extract_website_data

                website_text = extract_website_data(product_config.website_url)
                if website_text:
                    consolidated_text += f"=== WEBSITE CONTENT ({product_config.website_url}) ===\n{website_text}\n\n"
            except Exception:
                consolidated_text += f"=== WEBSITE CONTENT (Failed to extract from {product_config.website_url}) ===\n\n"

        # Add custom instructions if available
        if (
            hasattr(product_config, "custom_instructions")
            and product_config.custom_instructions
        ):
            consolidated_text = f"=== CUSTOM INSTRUCTIONS ===\n{product_config.custom_instructions}\n\n{consolidated_text}"

        # Ensure we return something even if all extractions failed
        if not consolidated_text.strip():
            consolidated_text = f"=== PRODUCT CONFIGURATION ===\nProduct Type: {product_config.product_type}\nSources: {product_config.source_summary()}\n"

        return consolidated_text.strip()

    except Exception:
        # Ultimate fallback
        return f"Product Type: {getattr(product_config, 'product_type', 'unknown')}"


def get_evaluation_for_config(product_config_id: str) -> Optional[Dict]:
    """Get the latest evaluation for a product configuration."""
    try:
        db = get_db()
        evaluations = db.get_evaluations_for_config(product_config_id)
        return evaluations[0] if evaluations else None
    except Exception:
        return None


def store_human_feedback(evaluation_id: int, rating: int, notes: str = "") -> bool:
    """Store human feedback for an evaluation."""
    try:
        db = get_db()
        feedback_id = db.store_human_feedback(evaluation_id, rating, notes)
        return feedback_id is not None
    except Exception:
        return False


# PHASE 3: New helper functions for user attribution


def get_evaluations_by_user(user_id: str = None, username: str = None) -> List[Dict]:
    """
    PHASE 3: Get evaluations created by a specific user.

    Args:
        user_id: User UUID to filter by
        username: Username to filter by (alternative to user_id)

    Returns:
        List of evaluations created by the user
    """
    try:
        db = get_db()
        return db.get_evaluations_by_user(user_id=user_id, username=username)
    except Exception:
        return []


def get_user_statistics() -> List[Dict]:
    """
    PHASE 3: Get statistics for all users who have created products.

    Returns:
        List of user statistics with product creation data
    """
    try:
        db = get_db()
        return db.get_user_statistics_detailed()
    except Exception:
        return []


def get_creators_list() -> List[Dict]:
    """
    PHASE 3: Get list of all product creators.

    Returns:
        List of creators with their product counts
    """
    try:
        db = get_db()
        return db.get_creators_list()
    except Exception:
        return []

