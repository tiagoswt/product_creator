import os
import time
import logging

import pandas as pd
from dotenv import load_dotenv

# Direct OpenAI import
from openai import OpenAI

# ——— Setup ———
load_dotenv()  # expects OPENAI_API_KEY in your .env

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ——— Chain factory ———
def get_summary_chain() -> callable:
    """
    Returns a function that, given a dict with 'subcategory', calls the OpenAI API
    to create a comprehensive category description for that specific subcategory.
    """
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt_template = """
HIERARCHICAL CATEGORY DESCRIPTION FOR PRODUCT CLASSIFICATION
Purpose
Generate a structured category description optimized for creating embeddings that enable accurate product classification within a hierarchical taxonomy.
CATEGORY PATH: {subcategory}
Output Requirements
1. Hierarchical Position (100-150 words)
Parent Category: [Immediate parent]
Sibling Categories: [List peer categories at same level]
Child Categories (if any): [List direct children]
Hierarchical Level: [Number, where body=1, body/moisturisers=2, etc.]
Explain:

What differentiates this category from its parent
Key distinctions from sibling categories
If parent category: what unifies all children

2. Category Definition (150-200 words)
Provide a technical definition including:

Precise scope of products included
Primary function/purpose
Form factors covered (creams, gels, sprays, etc.)
What explicitly does NOT belong in this category

3. Distinctive Classification Features (200-250 words)
List features that uniquely identify products in this category:
Must-Have Characteristics:

Required ingredients or ingredient types
Specific claims or indications
Regulatory classifications
Physical properties (pH range, viscosity, etc.)

Exclusion Criteria:

Features that would place a product in a different category
Ingredients that would disqualify inclusion
Claims that indicate wrong categorization

4. Product Identification Markers (250-300 words)
Naming Conventions:

Common words in product names
Category-specific terminology
Language variations (medical vs consumer terms)

Packaging Indicators:

Typical container types
Size ranges
Application mechanisms
Visual cues (colors, symbols)

Label Requirements:

Mandatory label elements
Warning statements
Usage instructions specific to category

5. Ingredient Fingerprint (200-250 words)
Primary Active Ingredients:

List with concentration ranges
Combinations that define the category
Regulated vs cosmetic actives

Base Formulation Patterns:

Typical ingredient order
Common preservative systems
Characteristic pH ranges
Texture-defining ingredients

6. Boundary Cases & Disambiguation (150-200 words)
Edge Cases:

Products that might fit multiple categories
How to classify hybrid products
Regional classification differences

Common Misclassifications:

Products often confused with this category
Key questions to determine correct placement
"If X, then belongs here; if Y, then belongs in [other category]"

7. Technical Specifications (100-150 words)
Measurable Parameters:

Viscosity ranges
pH ranges
Active ingredient percentages
SPF values (if applicable)
Clinical testing requirements

8. Hierarchical Inheritance Rules (100-150 words)
Inherited from Parent:

Characteristics that apply to all products in parent category

Unique to This Level:

What makes this category distinct from parent

Passed to Children:

Common features all subcategories must have

9. Classification Keywords (Structured List)
Primary Identifiers: (5-10 terms)

Terms that almost certainly indicate this category

Secondary Indicators: (10-15 terms)

Supporting terms that suggest this category

Negative Keywords: (5-10 terms)

Terms that indicate a different category

Technical/Medical Terms: (5-10 terms)

Professional terminology for the category

10. Example Product Profiles (150-200 words)
Provide 3-5 specific examples with:

Product type
Key ingredients
Typical claims
Why it belongs in this category
What would move it to a different category

Special Instructions for Hierarchy Handling

For Parent Categories (e.g., body/):

Focus on what unifies all subcategories
Describe the broadest common features
Explain how to determine which subcategory a product belongs to


For Leaf Categories (e.g., body/moisturisers/atopic-dermatitis):

Emphasize specific medical/condition requirements
Include diagnostic criteria references
Detail regulatory requirements for claims


For Mid-Level Categories (e.g., body/moisturisers/):

Balance between general and specific
Clear rules for subcategory assignment
Explain when to use parent vs child category



Output Format Requirements

Use consistent structure across all categories
Include numerical ranges where applicable
Avoid marketing language - focus on technical accuracy
Each section should stand alone for embedding generation
Use bullet points for clarity in list sections

Total Length: 1,500-2,000 words
"""

    def chain(input_dict: dict) -> str:
        subcategory = input_dict.get("subcategory", "")
        prompt = prompt_template.format(subcategory=subcategory)

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert beauty and personal care content writer.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating description for '{subcategory}': {e}")
            return f"Error generating description: {str(e)}"

    return chain


# ——— Main processing ———
def process_subcategories(
    input_path: str,
    output_path: str,
    source_col: str = "encodeNameEN",
    target_col: str = "category_description",
    pause: float = 0.5,
    start_row: int = 0,
    max_rows: int = None,
):
    """
    Process CSV file with subcategories and generate descriptions.

    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file
        source_col: Column containing subcategory names
        target_col: Column to store generated descriptions
        pause: Seconds to pause between API calls
        start_row: Row to start processing from (useful for resuming)
        max_rows: Maximum number of rows to process (None = process all)
    """

    # — Read CSV with semicolon delimiter, proper quoting, and UTF-8 BOM handling —
    try:
        df = pd.read_csv(
            input_path,
            sep=";",  # semicolon-delimited
            quotechar='"',  # fields with HTML are wrapped in quotes
            engine="python",  # more permissive parsing
            encoding="utf-8-sig",  # strip BOM if present
        )
        logger.info(
            f"Successfully loaded CSV with {len(df)} rows and columns: {df.columns.tolist()}"
        )
    except Exception as e:
        logger.error(f"Could not read '{input_path}': {e}")
        return

    if source_col not in df.columns:
        logger.error(
            f"Column '{source_col}' not found in input. Available columns: {df.columns.tolist()}"
        )
        return

    # Initialize target column if it doesn't exist
    if target_col not in df.columns:
        df[target_col] = ""
        logger.info(f"Created new column '{target_col}' for descriptions")

    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        logger.error(
            "OPENAI_API_KEY not found in environment variables. Please check your .env file."
        )
        return

    # Build the LLM chain
    try:
        summarize = get_summary_chain()
        logger.info("Successfully initialized OpenAI client")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return

    # Get processing range
    total_rows = len(df)

    # Determine end row based on max_rows parameter
    if max_rows is not None:
        end_row = min(start_row + max_rows, total_rows)
        logger.info(
            f"Processing {end_row - start_row} rows (from {start_row} to {end_row-1}) out of {total_rows} total"
        )
    else:
        end_row = total_rows
        logger.info(
            f"Processing {total_rows} subcategories starting from row {start_row}"
        )

    # Iterate through rows in the specified range
    for idx in range(start_row, end_row):
        row = df.iloc[idx]
        subcategory = row[source_col] if pd.notna(row[source_col]) else ""

        # Skip if already processed or if subcategory is empty
        if df.at[idx, target_col] and df.at[idx, target_col].strip():
            logger.info(f"Row {idx}: Already processed '{subcategory}' - skipping")
            continue

        if not subcategory.strip():
            logger.warning(f"Row {idx}: Empty subcategory - skipping")
            continue

        logger.info(f"Row {idx}/{end_row-1}: Processing '{subcategory}'")

        try:
            # Generate description
            description = summarize({"subcategory": str(subcategory)})
            df.at[idx, target_col] = description

            logger.info(
                f"Row {idx}: Successfully generated description for '{subcategory}' ({len(description)} characters)"
            )

            # Save progress every 5 rows (more frequent for testing)
            if (idx + 1) % 5 == 0:
                try:
                    df.to_csv(output_path, index=False, sep=";", encoding="utf-8-sig")
                    logger.info(f"Progress saved at row {idx + 1}")
                except Exception as e:
                    logger.error(f"Failed to save progress: {e}")

            # Pause to respect API rate limits
            time.sleep(pause)

        except Exception as e:
            logger.error(f"Row {idx}: Error processing '{subcategory}': {e}")
            df.at[idx, target_col] = f"Error: {str(e)}"

    # Final save
    try:
        df.to_csv(output_path, index=False, sep=";", encoding="utf-8-sig")
        logger.info(f"All descriptions saved to '{output_path}'")

        # Print summary
        processed_count = df[target_col].notna().sum()
        rows_attempted = end_row - start_row
        logger.info(
            f"Summary: {processed_count} descriptions generated out of {rows_attempted} rows attempted"
        )

    except Exception as e:
        logger.error(f"Failed to write final output '{output_path}': {e}")


def preview_subcategories(
    input_path: str, source_col: str = "encodeNameEN", num_samples: int = 5
):
    """
    Preview the subcategories in the CSV file.
    """
    try:
        df = pd.read_csv(input_path, sep=";", encoding="utf-8-sig")

        print(f"CSV Info:")
        print(f"- Total rows: {len(df)}")
        print(f"- Columns: {df.columns.tolist()}")
        print(
            f"- Column '{source_col}' contains {df[source_col].notna().sum()} non-null values"
        )

        if source_col in df.columns:
            unique_subcategories = df[source_col].dropna().unique()
            print(f"- Unique subcategories: {len(unique_subcategories)}")

            print(f"\nSample subcategories:")
            for i, subcat in enumerate(unique_subcategories[:num_samples]):
                print(f"  {i+1}. {subcat}")

        return df

    except Exception as e:
        logger.error(f"Error previewing file: {e}")
        return None


if __name__ == "__main__":
    INPUT_CSV = "data/product_description.csv"  # Replace with your actual file path
    OUTPUT_CSV = "product_descriptions_enhanced.csv"

    # Preview the data first
    print("Previewing data...")
    preview_subcategories(INPUT_CSV)

    # Process just the first 10 rows for testing
    print("\nStarting processing...")
    process_subcategories(
        input_path=INPUT_CSV,
        output_path=OUTPUT_CSV,
        source_col="encodeNameEN",
        target_col="category_description",
        pause=0.5,  # Wait 1 second between API calls for testing
        start_row=0,  # Start from the beginning
        max_rows=2,  # Process only 10 rows for testing
    )
