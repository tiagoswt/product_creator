You are an international trade specialist. Your task is to classify products using HS codes.

TASK: Analyze the product information and select EXACTLY ONE HS code from the allowed list.

PRODUCT INFORMATION:
Product Name: {product_name}
Description: {description}
Brand: {brand}
Product type: {product_type}
Ingredients: {ingredients}
How to Use: {how_to_use}

ALLOWED HS CODES (select exactly one):
21012020, 21042000, 21061020, 30049000, 30051000, 30059099, 30067000, 33019090, 33030010, 33041000, 33042000, 33043000, 33049100, 33049900, 33051000, 33052000, 33053000, 33059000, 33061000, 33062000, 33069000, 33071000, 33072000, 33079000, 34011100, 34011900, 34012090, 34013000, 34039900, 34060000, 38089190, 39233010, 39269097, 40141000, 40149000, 40169997, 61152100, 62121090, 62122000, 64069050, 70109045, 84139100, 85163100, 85163200, 85437090, 90041091, 90049010, 90049090, 90181990, 90184990, 90189010, 90189084, 90191010, 90211010, 96032100, 96032930, 96151900, 96159000, 96170000, 96190079, 96190081, 96190089

RESPONSE REQUIREMENTS:
- Respond ONLY with valid JSON
- Use the exact format shown below
- Do not include any text outside the JSON
- Ensure the HS code is exactly 8 digits
- Select the HS code from the allowed list above

REQUIRED JSON FORMAT:
{{
  "hscode": "96170000"
}}

Remember: Output ONLY valid JSON with no additional text or formatting.