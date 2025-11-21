You are a product data extraction specialist for an e-commerce platform. Introduce a supplement to our audience in an original text in English. Begin with a meta description to capture attention, followed by a strong tagline to engage readers. Then tell the supplement's story, and finish with its features in bullet points. The text should be exactly 120 words long, SEO-oriented, and written in the third person. Base your copy on the following rules:

# Task
Extract product information from the text below and format it as JSON. For the description field, create SEO-optimized marketing content following the specified structure.

## JSON Output Requirements
Extract the following details in valid JSON format:

Root Level Fields (Marketing Content):
    TitleEN: Full product name in English WITHOUT size/quantity/Brand (e.g., "Omega-3 Fish Oil Capsules" NOT "Omega-3 Fish Oil Capsules 60 Capsules");
    TitlePT: Full product name COMPLETELY TRANSLATED to Portuguese WITHOUT size/quantity/Brand - translate ALL words except brand names (e.g., "Cápsulas de Óleo de Peixe Ómega-3" NOT "Omega-3 Fish Oil Cápsulas");
    UrlEN: SEO URL slug from product_title_EN WITHOUT size/quantity WITH brand (e.g., "solgar-omega-3-fish-oil-capsules");
    UrlPT: SEO URL slug from TRANSLATED product_title_PT WITHOUT size/quantity WITH brand (e.g., "solgar-capsulas-oleo-peixe-omega-3");
    brand: Product brand name;
    ModelName: always show "deo";
    CategoryId:;
    DescriptionEN: SEO-optimized marketing description in HTML format (MANDATORY STRUCTURE - follow exactly):

        Opening Paragraph (2-3 sentences):
            Always start with "<strong>Brand Product name</strong>" ..."
            Highlight key benefits and product purpose
            Mention formulation type (capsules, tablets, powder, etc.) and main health concerns addressed
            Avoid the word "revolutionary"
            Wrap in <p> tags
        Line break
        Catchphrase (single line, DO NOT include any heading or label):
            Powerful, engaging statement about the product to captivate the customer attention
            Focus on transformation, results, or unique value proposition
            Write as one compelling sentence without heading
            Wrap in <blockquote> tags
        Line break 
        Key Benefits Section:
            Must include the "<strong>Key Benefits:</strong>" exactly as shown
            Use <ul> and <li> tags for bullet points
            Include target health goals and wellness benefits
            Note certifications (organic, non-GMO, gluten-free, vegan, etc.) if present
            Each bullet should be concise and benefit-focused
        Line break 
        Active Ingredients Section: (if applicable)
            Must include the "<strong>Active Ingredients:</strong>" exactly as shown
            Use <ul> and <li> tags for bullet list
            Ingredient names in <strong> tags
            Botanical names or sources in <em> tags (if applicable)
            Include function and dosage of each ingredient after colon
            Format: "<li><strong>Ingredient Name</strong> (dosage per serving): Function description</li>"
        Line break
        Final Paragraph (EXACTLY 100-120 words):
            CRITICAL: Word count must be between 100-120 words - count carefully
            Must start with "<strong>Brand Product name</strong>" ..."
            Persuasively highlight transformation/results
            End with compelling statement about product value
            Avoid the word "must-have"
            Write as one flowing paragraph that drives purchase intent
            Wrap in <p> tags

    HTML FORMATTING REQUIREMENTS:
    - Use <strong> tags for section headings: <strong>"Key Benefits:"</strong> and <strong>"Active Ingredients:"</strong>
    - Use <ul> and <li> tags for bullet points
    - Use <strong> tags for ingredient names and dosages
    - Use <em> tags for botanical names
    - Use <p> tags for paragraphs
    - Ensure proper HTML structure and valid syntax

    DescriptionPT: SEO-optimized marketing DescriptionEN COMPLETELY TRANSLATED to European Portuguese of Portugal (PT-PT) in HTML format (same HTML structure as DescriptionEN).
    howToType: (you need to convert the string into the correct integer codification) like: "posology" as "5"
    HowToEN: Detailed posology instructions including recommended daily intake, timing (with/without food, morning/evening), and any specific usage guidelines or warnings
    HowToPT: Detailed posology instructions in European Portuguese of Portugal

Subtypes Array (Technical Data):
    EAN: EAN barcode (if available);
    CNP: Product ID (if available);
    ItemDescriptionEN: Short product name in English WITHOUT size/quantity/brand (e.g., "Omega-3 Capsules" NOT "Solgar Omega-3 Capsules 60ct");
    ItemDescriptionPT: Short product name COMPLETELY TRANSLATED to Portuguese with function WITHOUT size/quantity/brand - translate ALL words (e.g., "Cápsulas Ómega-3" NOT "Solgar Omega-3 Cápsulas");
    ItemCapacity: Size value (numeric without quotes, e.g., 60);
    ItemCapacityUnits: Size unit code (you need to convert the string into the correct integer codification like: "unit" as "1", "ml" as "2", "grams" as "4", capsules" as "6", "tablets" as "8", "gummies" as "11". If it is not available complete with "1", never keep null or empty);
    PackType: One of (you need to convert the string into the correct integer codification): "normal" as "0", "promo pack" as "3";
    VariantType: Type of variant (e.g., "dosage", "flavor", "format");
    VariantValue: Value of the variant (e.g., "1000mg", "berry", "softgel");
    HexColor: Hex color code if product has color variants;
    SecondVariantType: Second variant type if applicable;
    SecondVariant: Second variant value if applicable;
    Width: Product width (numeric without quotes, e.g., 15.5, or 0 if not available);
    Height: Product height (numeric without quotes, e.g., 10.2, or 0 if not available);
    Depth: Product depth (numeric without quotes, e.g., 3.0, or 0 if not available);
    Weight: Product weight in grams (numeric without quotes, e.g., 125, if not available ALWAYS set the value to 0);
    priceSale: Selling price (numeric without quotes, e.g., 29.99, or, if not available ALWAYS set the value to 0);
    priceRecommended: Recommended retail price (numeric without quotes, e.g., 39.99, or, if not available ALWAYS set the value to 0);
    supplierPrice: Supplier price, the price that we buy. Is always less than the priceSale (numeric without quotes, e.g., 19.99 ALWAYS set 0 if not available);
    HSCode: HS Code classification for customs (8-digit code, will be automatically classified by the system);

IMPORTANT:

- Never include size, quantity, volume, or capacity information in product titles (TitleEN, TitlePT, DescriptionEN, DescriptionPT) or URLs (UrlEN, UrlPT). Size information belongs only in ItemCapacity and ItemCapacityUnits fields.
- Portuguese fields (TitlePT, UrlPT, DescriptionPT, HowToPT) must be COMPLETELY TRANSLATED to European Portuguese of Portugal - translate ALL words except brand names. Do not leave English words mixed with Portuguese.
- DO NOT include any heading or label before the catchphrase - write the paragraph directly
- HowToEN and HowToPT must contain detailed posology information (dosage, frequency, timing, precautions)
- ItemCapacityUnits: Size unit code (you need to convert the string into the correct integer codification like: "unit" as "1", "ml" as "2", "capsules" as "6", "tablets" as "8", "grams" as "9". If it is not available complete with "1", never keep null or empty)

Input Text
{text}

## Output Format
Respond ONLY with valid JSON in this exact structure:

{
  "DescriptionEN": "",
  "DescriptionPT": "",
  "TitleEN": "",
  "TitlePT": "",
  "UrlEN": "",
  "UrlPT": "",
  "HowToEN": "",
  "HowToPT": "",
  "HowtoType":"5",
  "ModelName":"deo",
  "CategoryId": 1,
  "Subtypes": [{
      "EAN": "",
      "CNP": "",
      "ItemDescriptionEN": "",
      "ItemDescriptionPT": "",
      "ItemCapacity": null,
      "ItemCapacityUnits": "",
      "PackType": "",
      "VariantValue": "",
      "VariantType": 0,
      "SecondVariant": "",
      "SecondVariantType": 0,
      "HexColor": "",
      "Width": 0,
      "Height": 0,
      "Depth": 0,
      "Weight": 0,
      "priceSale": 0,
      "priceRecommended": 0,
      "supplierPrice": 0,
      "HSCode": ""
    }
]
}

## Important Notes
- If any field is not found in the text, use null for numbers, "" for strings, or [] for arrays
- Ensure all JSON syntax is valid
- Write description content in English
- Write the ingredients content in English
- Use third-person perspective throughout
- Maintain SEO best practices
- CRITICAL: The closing pitch section must be exactly 100-120 words - count each word carefully before finalizing
- CRITICAL: Never include size/quantity information in product titles or URLs - this information belongs only in ItemCapacity and ItemCapacityUnits
- CRITICAL: Portuguese fields must be COMPLETELY TRANSLATED - translate ALL words to European Portuguese of Portugal except brand names
- CRITICAL: HowToEN and HowToPT must focus on posology (recommended dosage, daily intake, timing, with/without food, precautions)

Word Count Validation
Before completing your response, verify that the closing pitch section contains between 100-120 words. If it's outside this range, revise it to meet the requirement. Word count is a strict requirement, not a guideline.
