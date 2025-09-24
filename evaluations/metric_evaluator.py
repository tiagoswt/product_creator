"""
metric_evaluator.py - FIXED VERSION
Enhanced Three-Metric Evaluator for Product Extraction Quality

FIXES:
- Removed LangChain evaluator dependency that was causing format conflicts
- Direct LLM calls with proper JSON parsing
- Better error handling and fallback mechanisms
- Maintains the same API for backward compatibility
"""

import json
import re
import time
from typing import Dict, List, Optional, Any
import streamlit as st
from langsmith import traceable

try:
    from langchain_openai import ChatOpenAI

    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"LangChain dependencies not available: {str(e)}")
    LANGCHAIN_AVAILABLE = False

import config


class MetricEvaluator:
    """
    Enhanced Three-Metric Evaluator for Product Extraction Quality

    Evaluates:
    1. Structure Correctness - JSON validation and schema compliance
    2. Content Correctness - Accuracy vs input, hallucination detection
    3. Translation Correctness - Portuguese translation quality

    FIXED: Uses direct LLM calls instead of LangChain evaluators to avoid format conflicts.
    """

    def __init__(self):
        """Initialize with direct LLM calls instead of LangChain evaluators."""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain dependencies not available.")

        # Initialize LLM for evaluation - use direct calls instead of evaluators
        self.llm = ChatOpenAI(
            model=config.OPENEVALS_MODEL,
            temperature=config.OPENEVALS_TEMPERATURE,
        )

        if config.OPENEVALS_DEBUG:
            print("SUCCESS: Fixed Three-Metric Evaluator initialized with direct LLM calls")

    def evaluate_extraction(
        self, input_text: str, extracted_json: Dict, product_type: str
    ) -> Dict[str, Any]:
        """
        Complete evaluation using all 3 enhanced metrics with fixed LLM calls.

        Args:
            input_text: Consolidated text from all data sources (PDF, Excel/CSV, Web)
            extracted_json: Extracted product data
            product_type: cosmetics, fragrance, or subtype

        Returns:
            Dict with evaluation results including detailed reasoning for AI Reasoning UI
        """
        start_time = time.time()
        results = {}

        try:
            if config.OPENEVALS_DEBUG:
                print(f"[EVAL] Evaluating {product_type} with fixed evaluator...")

            # 1. Structure Correctness - JSON validation with input context
            results["structure_correctness"] = self._evaluate_structure_correctness(
                input_text, extracted_json, product_type
            )

            # 2. Content Correctness - Hallucination detection with input context
            results["content_correctness"] = self._evaluate_content_correctness(
                input_text, extracted_json
            )

            # 3. Translation Correctness - Portuguese quality assessment
            results["translation_correctness"] = self._evaluate_translation_correctness(
                input_text, extracted_json
            )

            # Calculate weighted overall score
            results["overall_score"] = self._calculate_overall_score(results)
            results["evaluation_time"] = time.time() - start_time

            if config.OPENEVALS_DEBUG:
                self._debug_results(results)

            return results

        except Exception as e:
            print(f"Evaluation failed: {str(e)}")
            return self._create_fallback_results(time.time() - start_time, str(e))

    @traceable(
        name="structure_evaluation",
        tags=["evaluation", "structure", "json_validation", "schema_compliance"]
    )
    def _evaluate_structure_correctness(
        self, input_text: str, extracted_json: Dict, product_type: str
    ) -> Dict:
        """
        FIXED: Structure correctness evaluation with direct LLM calls.
        Uses consolidated input_text from all data sources for context.
        """

        # Truncate input for efficiency while preserving key information
        truncated_input = input_text[:50000] if len(input_text) > 50000 else input_text
        json_str = json.dumps(extracted_json, indent=2)

        # Product-specific structure prompts with enhanced feedback
        structure_prompts = {
            "cosmetics": f"""You are evaluating the JSON structure quality of a cosmetics product extraction.

SOURCE DATA: {truncated_input}

EXTRACTED JSON: {json_str}

TASK: Rate the JSON structure compliance for cosmetics products (1-5 scale).

REQUIRED STRUCTURE for cosmetics (based on cosmetics_prompt.md):
ROOT LEVEL FIELDS (all required):
- TitleEN (string): Full product name in English without size/quantity
- TitlePT (string): Full product name translated to Portuguese without size/quantity
- DescriptionEN (string): SEO-optimized HTML marketing description in English
- DescriptionPT (string): SEO-optimized HTML marketing description in Portuguese
- UrlEN (string): SEO URL slug from English title
- UrlPT (string): SEO URL slug from Portuguese title
- HowToEN (string): Usage instructions in English
- HowToPT (string): Usage instructions in Portuguese
- HowtoType (string/number): Usage type code (0-4)
- brand (string): Product brand name
- ModelName (string): Should be "deo"
- CategoryId (number): Category identifier
- Subtypes (array): Array of product variants

SUBTYPES ARRAY STRUCTURE (each object must contain):
- EAN (string): EAN barcode
- CNP (string): Product ID
- ItemDescriptionEN (string): Short English name without size
- ItemDescriptionPT (string): Short Portuguese name without size
- ItemCapacity (number): Size value
- ItemCapacityUnits (string/number): Unit code (1=unit, 2=ml, 4=gr, etc.)
- PackType (string/number): Pack type code (0=normal, 1=coffret, etc.)
- VariantType (string): Variant type
- VariantValue (string): Variant value
- HexColor (string): Color code if applicable
- Width, Height, Depth, Weight (numbers): Physical dimensions
- priceSale, priceRecommended, supplierPrice (numbers): Pricing information

SCORING:
5 = Perfect structure compliance - all required root fields and Subtypes array with correct types
4 = Minor structural issues - 1-2 missing optional fields or minor type issues
3 = Some structural problems - missing some required fields or incorrect array structure
2 = Major structural issues - missing critical root fields or malformed Subtypes array
1 = Severely malformed structure - invalid JSON or completely wrong schema

Respond with ONLY this JSON format:
{{"score": <1-5>, "feedback": "<specific feedback about structure compliance with actual field names>"}}""",
            "fragrance": f"""You are evaluating the JSON structure quality of a fragrance product extraction.

SOURCE DATA: {truncated_input}

EXTRACTED JSON: {json_str}

TASK: Rate the JSON structure compliance for fragrance products (1-5 scale).

REQUIRED STRUCTURE for fragrance (based on fragance_prompt.md):
- product_name (string): Main product name
- brand (string): Fragrance brand
- price (number): Product price
- purchase_price (number): Cost price at which company buys (if available)
- currency (string): Price currency (e.g., "EUR")
- meta_description (string): 120-155 character marketing description
- benefits (string): Product benefits and advantages
- conclusion (string): 3-5 lines sales storytelling
- scent_family (string): Fragrance family (e.g., "floral", "woody", "oriental")
- top_notes (array): List of top fragrance notes
- middle_notes (array): List of heart/middle notes
- base_notes (array): List of base notes
- concentration (string): e.g., "Eau de Parfum", "Eau de Toilette"
- size (string): Product size (e.g., "50 ml")
- gender (string): "men", "women", or "unisex"
- EAN (string): Product EAN if available
- CNP (string): Product ID if available
- Valid JSON syntax with proper data types

SCORING:
5 = Perfect structure compliance - all required fields present with correct types
4 = Minor structural issues - 1-2 missing optional fields or minor type issues
3 = Some structural problems - missing some required fields or incorrect types  
2 = Major structural issues - missing critical fields or widespread format problems
1 = Severely malformed structure - invalid JSON or missing essential fragrance data

Respond with ONLY this JSON format:
{{"score": <1-5>, "feedback": "<specific feedback about structure compliance>"}}""",
            "subtype": f"""You are evaluating the JSON structure quality of a subtype product extraction.

SOURCE DATA: {truncated_input}

EXTRACTED JSON: {json_str}

TASK: Rate the JSON structure compliance for subtype products (1-5 scale).

REQUIRED STRUCTURE for subtype (based on subtype_prompt.md):
- Array of objects, each containing:
  - EAN (string): EAN barcode (if available)
  - CNP (string): Product ID (if available)
  - ItemDescriptionEN (string): Short English product name without size/quantity
  - ItemDescriptionPT (string): Short Portuguese product name without size/quantity
  - ItemCapacity (number): Size value (numeric without quotes)
  - ItemCapacityUnits (string/number): Unit code (1=unit, 2=ml, 4=gr, 5=kg, 6=capsules, etc.)
  - PackType (string/number): Pack type code (0=normal, 1=coffret, 3=promo, 6=limited, etc.)
  - VariantType (number): Variant type (should be numeric code)
  - VariantValue (string): Variant value
  - HexColor (string): Hex color code if applicable
  - SecondVariantType (number): Second variant type (should be numeric code)
  - SecondVariant (string): Second variant value
  - Width (number): Product width (numeric or null)
  - Height (number): Product height (numeric or null)
  - Depth (number): Product depth (numeric or null)
  - Weight (number): Product weight in grams (numeric or null)
  - priceSale (number): Selling price (numeric or null)
  - priceRecommended (number): Recommended retail price (numeric or null)
- Valid JSON syntax with proper data types

SCORING:
5 = Perfect structure compliance - array format with all required fields and correct types
4 = Minor structural issues - 1-2 missing optional fields or minor type issues
3 = Some structural problems - missing some required fields or incorrect types
2 = Major structural issues - missing critical array fields or widespread format problems  
1 = Severely malformed structure - invalid JSON or not in proper array format

Respond with ONLY this JSON format:
{{"score": <1-5>, "feedback": "<specific feedback about structure compliance>"}}""",
        }

        prompt = structure_prompts.get(product_type, structure_prompts["cosmetics"])

        try:
            # Use direct LLM call instead of evaluator
            response = self.llm.invoke(prompt)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            parsed_result = self._parse_json_response(response_text, "structure")

            return {
                "score": parsed_result["score"],
                "reasoning": f"Structure Evaluation: {parsed_result['feedback']}",
                "method": "direct_llm_json_validation",
                "evaluator": "fixed_direct_call",
            }

        except Exception as e:
            print(f"Structure evaluation failed: {str(e)}")
            return self._create_metric_fallback("structure", str(e))

    @traceable(
        name="content_evaluation",
        tags=["evaluation", "content", "accuracy", "hallucination_detection", "fidelity"]
    )
    def _evaluate_content_correctness(
        self, input_text: str, extracted_json: Dict
    ) -> Dict:
        """
        FIXED: Content accuracy evaluation with direct LLM calls.
        Uses consolidated input_text to detect hallucinations and verify accuracy.
        """

        # Truncate for efficiency but keep key information
        truncated_input = input_text[:50000] if len(input_text) > 50000 else input_text
        json_output = json.dumps(extracted_json, indent=2)[:25000]

        content_prompt = f"""You are evaluating the content accuracy of product extraction.

SOURCE DATA: {truncated_input}

EXTRACTED RESULT: {json_output}

TASK: Rate the content accuracy (1-5 scale).

Evaluate how accurately the extraction reflects the source data. Check for:
- Hallucinated brands, prices, or product names not in source
- Incorrect values that contradict source data  
- Made-up details, ingredients, or descriptions
- Information missing from source but present in extraction
- Faithful representation of available source information

SCORING:
5 = Perfect accuracy - all extracted data faithfully represents source information
4 = Very accurate - minor inconsistencies that don't affect core product data
3 = Mostly accurate - some inaccuracies but core information is correct
2 = Significant inaccuracies - important details are wrong or hallucinated  
1 = Major hallucinations - mostly incorrect information not supported by source

Respond with ONLY this JSON format:
{{"score": <1-5>, "feedback": "<specific feedback about content accuracy and any hallucinations detected>"}}"""

        try:
            # Use direct LLM call instead of evaluator
            response = self.llm.invoke(content_prompt)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            parsed_result = self._parse_json_response(response_text, "content")

            return {
                "score": parsed_result["score"],
                "reasoning": f"Content Evaluation: {parsed_result['feedback']}",
                "method": "direct_llm_hallucination_detection",
                "evaluator": "fixed_direct_call",
            }

        except Exception as e:
            print(f"Content evaluation failed: {str(e)}")
            return self._create_metric_fallback("content", str(e))

    @traceable(
        name="translation_evaluation",
        tags=["evaluation", "translation", "portuguese", "localization", "fluency"]
    )
    def _evaluate_translation_correctness(
        self, input_text: str, extracted_json: Dict
    ) -> Dict:
        """
        FIXED: Translation quality evaluation with direct LLM calls.
        Assesses Portuguese translation accuracy and fluency.
        """

        # Extract English-Portuguese translation pairs
        translation_pairs = self._extract_translation_pairs(extracted_json)

        if not translation_pairs:
            return {
                "score": 5,
                "reasoning": "Translation Evaluation: No translations required - perfect score",
                "method": "no_translations_required",
                "evaluator": "skip",
                "pairs_found": 0,
            }

        pairs_text = self._format_translation_pairs(translation_pairs)

        translation_prompt = f"""You are evaluating Portuguese (PT-PT) translation quality in product extraction from user data sources (CSV, Web, PDF).

TRANSLATION PAIRS FOUND: {pairs_text}

TASK: Evaluate Portuguese translation quality considering ALL 5 criteria and provide a SINGLE final score (1-5 scale).

EVALUATION CRITERIA (consider all 5 when calculating final score):

1. ACCURACY (Semantic Correctness): Does Portuguese correctly convey English meaning?
2. FLUENCY (Natural Portuguese Grammar): Natural European Portuguese grammar and expression?
3. COMPLETENESS (No Missing Translations): All English content translated except brand names?
4. CONSISTENCY (Terminology Alignment): Consistent terminology across translations?
5. CULTURAL APPROPRIATENESS (PT-PT Specifics): European Portuguese expressions, not Brazilian?

IMPORTANT REQUIREMENTS:
- Brand names should remain untranslated (e.g., "CeraVe", "L'Oréal")
- Use European Portuguese (PT-PT), not Brazilian Portuguese
- Marketing language should sound natural and compelling in Portuguese
- Technical terms should use standard European Portuguese terminology
- Product descriptions should be fully translated except brand names

FINAL SCORING (consider all 5 criteria):
5 = Excellent translations - all criteria met excellently
4 = Very good translations - minor issues in 1-2 criteria
3 = Good translations - acceptable with room for improvement
2 = Poor translations - significant issues in multiple criteria
1 = Very poor translations - major problems across most criteria

Calculate a single final score considering all 5 criteria and respond with ONLY this JSON format:
{{"score": <1-5>, "feedback": "<detailed feedback mentioning accuracy, fluency, completeness, consistency, and cultural appropriateness>"}}"""

        try:
            # Use direct LLM call instead of evaluator
            response = self.llm.invoke(translation_prompt)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            parsed_result = self._parse_json_response(response_text, "translation")

            return {
                "score": parsed_result["score"],
                "reasoning": f"Translation Evaluation: {parsed_result['feedback']}",
                "method": "direct_llm_portuguese_assessment",
                "evaluator": "fixed_direct_call",
                "pairs_found": len(translation_pairs),
            }

        except Exception as e:
            print(f"Translation evaluation failed: {str(e)}")
            return self._create_metric_fallback("translation", str(e))

    def _parse_json_response(self, response_text: str, metric_name: str) -> Dict:
        """
        FIXED: Parse JSON response from direct LLM calls.

        Args:
            response_text: LLM response text
            metric_name: Name of metric for logging

        Returns:
            Dict with 'score' and 'feedback' keys
        """
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
            feedback = parsed.get("feedback", f"No specific feedback for {metric_name}")

            # Validate score is in range
            score = max(1, min(5, score))

            return {"score": score, "feedback": feedback}

        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract score with regex
            score_match = re.search(r'"?score"?\s*:?\s*([1-5])', response_text)
            if score_match:
                score = int(score_match.group(1))
                return {
                    "score": score,
                    "feedback": f"{metric_name} evaluation completed (score: {score}) - JSON parse failed but score extracted",
                }

            if config.OPENEVALS_DEBUG:
                print(f"JSON parsing error for {metric_name}: {str(e)}")
                print(f"Response was: {response_text[:500]}...")

            return {
                "score": 3,
                "feedback": f"{metric_name} evaluation failed - could not parse response",
            }

        except Exception as e:
            if config.OPENEVALS_DEBUG:
                print(f"Response parsing error for {metric_name}: {str(e)}")
            return {
                "score": 3,
                "feedback": f"{metric_name} evaluation parsing failed: {str(e)}",
            }

    def _extract_translation_pairs(self, extracted_json: Dict) -> List[Dict]:
        """Extract English-Portuguese translation pairs from JSON structure based on cosmetics_prompt.md format."""
        pairs = []

        try:
            # Root level translation pairs (from cosmetics_prompt.md structure)
            root_pairs = [
                ('DescriptionEN', 'DescriptionPT'),
                ('TitleEN', 'TitlePT'),
                ('UrlEN', 'UrlPT'),
                ('HowToEN', 'HowToPT')
            ]

            # Check root level fields
            for en_field, pt_field in root_pairs:
                en_value = extracted_json.get(en_field)
                pt_value = extracted_json.get(pt_field)

                if en_value and pt_value and str(en_value).strip() and str(pt_value).strip():
                    pairs.append({
                        "english": str(en_value).strip(),
                        "portuguese": str(pt_value).strip(),
                        "field": en_field.replace('EN', ''),
                        "location": "root"
                    })

            # Check Subtypes array for ItemDescription pairs
            if 'Subtypes' in extracted_json and isinstance(extracted_json['Subtypes'], list):
                for i, subtype in enumerate(extracted_json['Subtypes']):
                    if isinstance(subtype, dict):
                        en_value = subtype.get('ItemDescriptionEN')
                        pt_value = subtype.get('ItemDescriptionPT')

                        if en_value and pt_value and str(en_value).strip() and str(pt_value).strip():
                            pairs.append({
                                "english": str(en_value).strip(),
                                "portuguese": str(pt_value).strip(),
                                "field": "ItemDescription",
                                "location": f"Subtypes[{i}]"
                            })

        except Exception as e:
            print(f"Error extracting translation pairs: {str(e)}")

        return pairs

    def _format_translation_pairs(self, pairs: List[Dict]) -> str:
        """Format translation pairs for evaluation prompt."""
        formatted = []
        for i, pair in enumerate(pairs, 1):
            formatted.append(
                f"{i}. {pair['field']} ({pair['location']}):\n"
                f"   English: \"{pair['english']}\"\n"
                f"   Portuguese: \"{pair['portuguese']}\"\n"
            )
        return "\n".join(formatted)

    def _calculate_overall_score(self, results: Dict) -> float:
        """Calculate weighted overall score with score validation."""
        try:
            # Extract scores with validation
            structure_score = results["structure_correctness"]["score"]
            content_score = results["content_correctness"]["score"]
            translation_score = results["translation_correctness"]["score"]

            # Validate all scores are in 1-5 range (clamp if needed)
            structure_score = max(1, min(5, structure_score))
            content_score = max(1, min(5, content_score))
            translation_score = max(1, min(5, translation_score))

            # Apply configured weights
            weights = config.EVALUATION_WEIGHTS
            overall = (
                structure_score * weights["structure_correctness"]
                + content_score * weights["content_correctness"]
                + translation_score * weights["translation_correctness"]
            )

            # Ensure overall score is also in valid range
            return round(max(1.0, min(5.0, overall)), 2)

        except Exception as e:
            print(f"Error calculating overall score: {str(e)}")
            return 3.0

    def _create_metric_fallback(self, metric_name: str, error: str) -> Dict:
        """Create fallback result for failed metric evaluation."""
        return {
            "score": 3,
            "reasoning": f"{metric_name.title()} Evaluation: Failed due to error - {error}",
            "method": "fallback",
            "evaluator": "error",
        }

    def _create_fallback_results(self, evaluation_time: float, error: str) -> Dict:
        """Create complete fallback results when entire evaluation fails."""
        return {
            "structure_correctness": self._create_metric_fallback("structure", error),
            "content_correctness": self._create_metric_fallback("content", error),
            "translation_correctness": self._create_metric_fallback(
                "translation", error
            ),
            "overall_score": 3.0,
            "evaluation_time": evaluation_time,
            "error": error,
        }

    def _debug_results(self, results: Dict):
        """Debug output showing all metric scores and feedback for validation."""
        print("RESULTS: Fixed Evaluation Results with Feedback:")
        for metric, data in results.items():
            if metric not in ["evaluation_time", "overall_score"] and isinstance(
                data, dict
            ):
                score = data.get("score", "N/A")
                reasoning = data.get("reasoning", "No reasoning")
                method = data.get("method", "unknown")
                print(f"  {metric}: {score}/5")
                print(f"    Reasoning: {reasoning[:100]}...")
                print(f"    Method: {method}")

        overall = results.get("overall_score", "N/A")
        time_taken = results.get("evaluation_time", "N/A")
        print(f"  Overall Score: {overall}/5 (Time: {time_taken:.2f}s)")


# Factory function for easy import
def create_fixed_evaluator() -> MetricEvaluator:
    """Factory function to create the fixed three-metric evaluator."""
    try:
        return MetricEvaluator()
    except Exception as e:
        print(f"Failed to create fixed evaluator: {str(e)}")
        raise


# Backward compatibility
ThreeMetricEvaluator = MetricEvaluator

