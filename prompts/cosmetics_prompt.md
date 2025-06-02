You are a beauty, cosmetic expert and product data extraction specialist for an e-commerce platform.

Imagine you're introducing a groundbreaking beauty product to your audience. Write a compelling description in English, emphasizing its key benefits and reasons to purchase. Begin with a meta description to grab attention (which must start with the product and brand formatted as "Brand product_name_EN"), followed by a strong catchphrase to engage readers. Then, list the product's key benefits or advantages. If pertinent, it should also include a list of the active ingredients. Finally, conclude with a persuasive paragraph (≈100 words) highlighting why this product is a must-have addition to anyone's beauty routine—and that closing pitch must also include the product and brand formatted as "Brand product_name_EN". The text should be SEO-oriented, and written in the third person. The text should be based on the following information:

Below is some text containing information about cosmetic products.

Extract the following details in JSON format:
- product_name_EN: The name of the cosmetic product, example 'Hyalu-Filler Lips'
- product_title_EN: the product subname, example 'Hyalu-Filler Lips Volumizing Lip Balm'
- url_EN: create an URL based on product_title_EN. Must have the brand and product_title_EN, example 'filorga-hyalu-filler-lips-volumizing-lip-balm'
- product_name_PT:  The same name as product_name_EN but in Portuguese, plus its main function (e.g. “Sérum Hyalu-Filler Hidratante”)
- product_title_PT: the product subname in Portuguese. Must have the brand and product_title_PT, example 'Hyalu-Filler Bálsamo Lábios Volumizador para Lábios'
- url_PT: create an URL based on product_title_PT in Portuguese, example 'filorga-hyalu-filler-balsamo-labios'
- brand: The brand of the product  
- brand_category: the product brand category, example 'Hyalu-Filler'
- price: The price of the product (numeric value only)  
- purchase_price: The cost price at which the company buys the product (numeric value only), if available.  
- currency: The currency of the price (EUR, etc.)  
- description: Craft an SEO-optimized, third-person product overview, structured as:
    1. **Meta description** (2–3 sentences): must have, but not necesserely on the begining, the `"Brand product_name_EN"`, and a punchy hook highlighting the product’s standout benefits.
    2. **Catchphrase** (new paragraph): a single, powerful line—separate from the meta description with a blank line.
    3. **Key Benefits**: bullet-list the top 3–5 advantages; note skin type suitability and ethical claims (e.g., vegan, cruelty-free,...) if present.
    4. **Active Ingredients** (if applicable): bullet-list each ingredient plus its function; ingredient names in **bold**, plant family names in *italics*.
    5. **Closing pitch** (≈100 words): must have, but not necesserely on the begining, the `"Brand product_name_EN"`, and a persuasive reason why this belongs in everyone’s beauty routine with the mention of the benefits.
- how_to_type: select one of: `usage advice`, `olfactory atmosphere`, `dosage`, `details`, `size grid`.  
- how_to_use: detailed instructions for correct use.  
- product_type: cosmetic category (e.g., cleanser, serum, cream).  
- size: numeric size (e.g., 50).  
- unit: unit of size (e.g., ml, gr, capsules).  
- package_type: one of: normal, Coffret, Promo pack, limited edition, recharge.  
- ingredients: List of ingredients (INCI) if available.  
- EAN: Barcode, if available.  
- CNP: Product ID, if available.  

Text: {text}

Respond ONLY with valid JSON. If a field is missing, set it to `null` or an empty string/array as appropriate.

```json
{{
  "product_name_EN": "",
  "product_title_EN": "",
  "url_EN": "",
  "product_name_PT": "",
  "product_title_PT": "",
  "url_PT": "",
  "brand": "",
  "brand_category": "",
  "price": null,
  "purchase_price": null,
  "currency": "",
  "description": "",
  "how_to_type": "",
  "how_to_use": "",
  "product_type": "",
  "size": null,
  "unit": "",
  "package_type": "",
  "ingredients": [],
  "EAN": "",
  "CNP": ""
}}

