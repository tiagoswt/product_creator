#!/usr/bin/env python3
"""
Enhanced Beauty Product Classifier - Production Deployment Script
Generated on: 2025-08-08T10:56:06.775682
"""

import os
import sys
from pathlib import Path

# Add the classifier directory to Python path
CLASSIFIER_DIR = Path(__file__).parent / "enhanced_classifier_state"
sys.path.insert(0, str(CLASSIFIER_DIR.parent))

def load_classifier():
    """Load the trained classifier for production use"""
    try:
        from enhanced_classifier import load_classifier_state
        classifier = load_classifier_state(str(CLASSIFIER_DIR))

        if classifier is None:
            raise RuntimeError("Failed to load classifier")

        print("SUCCESS: Classifier loaded successfully")
        return classifier

    except Exception as e:
        print(f"ERROR: Failed to load classifier: {e}")
        return None

def classify_product(product_description: str):
    """Classify a single product"""
    classifier = load_classifier()
    if classifier is None:
        return None

    try:
        result = classifier.classify(product_description)
        return {
            'category': result.predicted_category,
            'confidence': result.confidence,
            'method': result.method_used,
            'processing_time': result.processing_time,
            'cost': result.cost_estimate
        }
    except Exception as e:
        print(f"ERROR: Classification failed: {e}")
        return None

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Beauty Product Classifier")
    parser.add_argument("product_description", help="Product description to classify")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    result = classify_product(args.product_description)

    if result:
        if args.verbose:
            print(f"Product: {args.product_description}")
            print(f"Category: {result['category']}")
            print(f"Confidence: {result['confidence']:.3f}")
            print(f"Method: {result['method']}")
            print(f"Processing Time: {result['processing_time']:.3f}s")
            print(f"Cost: ${result['cost']:.6f}")
        else:
            print(result['category'])
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
