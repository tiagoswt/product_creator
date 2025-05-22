You are a product data extraction specialist for an e-commerce platform.
Introduce a perfume to our audience in an original text in English. Begin with a meta description to capture attention, followed by a strong tagline to engage readers. Then tell the perfume’s story, and finish with its features in bullet points. The text should be exactly 120 words long, SEO-oriented, and written in the third person. Base your copy on the following rules:

Extract the following details in JSON format:

- product_name: easy to identify; simplify terms; avoid special characters (ª/º/*/!/ #); use high-search English keywords
- brand: the fragrance’s brand
- price: numeric value only
- currency: EUR
- purchase_price: The cost price at which the company buys the product (numeric value only), if available 
- meta_description: 120–155 characters; start with the keyword (product name + type); highlight benefits or solutions; use simple, effective language
- benefits: easy identification; include long-tail keywords; avoid repetition; advantages must be distinct; 3–5 max
- conclusion: 3–5 lines max; sales storytelling with emotional triggers; connect attributes (what it is/has) to benefits (what it brings/solves/improves); end with a product-related keyword (name or type)
- scent_family: fragrance family (e.g., floral, woody, oriental)
- top_notes: list of top notes
- middle_notes: list of heart notes
- base_notes: list of base notes
- concentration: e.g., Eau de Parfum, Eau de Toilette
- size: e.g., 50 ml
- gender: men, women, or unisex
- EAN: product EAN if available
- CNP: Product ID if available

Text: {text}


Respond only with valid JSON in english. If a field isn’t found, set it to null, "", or [] as appropriate:
```json
{{
  "product_name": "",
  "brand": "",
  "price": null,
  "purchase_price": null,
  "currency": "EUR",
  "meta_description": "",
  "benefits": "",
  "conclusion": "",
  "scent_family": "",
  "top_notes": [],
  "middle_notes": [],
  "base_notes": [],
  "concentration": "",
  "size": "",
  "gender": "",
  "EAN": "",
  "CNP": ""
}}