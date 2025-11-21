You are an international trade specialist. Your task is to classify products using HS codes.

TASK:
Analyze the product information and select EXACTLY ONE HS code from the allowed list.

PRODUCT INFORMATION:

Product Name: {product_name}
Description: {description}
Brand: {brand}
Product type: {product_type}
Ingredients: {ingredients}
How to Use: {how_to_use}

ALLOWED HS CODES (select exactly one):
Food, beverages & supplements

21012020

21042000 — Homogenized composite food preparations for retail sale (baby food/dietetic), ≤250 g

21061020 — Food supplements: protein concentrates and textured protein substances

Medicines & medical preparations

30049000 — Medicaments (not containing antibiotics, hormones, vitamins, alkaloids, etc.)

30051000 — Adhesive dressings and other adhesive medical articles

30059099 — Bandages and non-adhesive dressings impregnated/coated with pharmaceutical substances

30067000 — Gel preparations for medical use (surgical/examination lubricants)

Essential oils & fragrances

33019090 — Essential oils, aromatic waters, aqueous solutions of essential oils

33030010 — Perfumes

Cosmetics and skincare

33041000 — Lip make-up products

33042000 — Eye make-up products

33043000 — Manicure/pedicure preparations

33049100 — Face/body powders including compact powders

33049900 — Beauty or skin-care products (excluding lip/eye/makeup powders)

Haircare

33051000 — Shampoos

33052000 — Hair permanent-wave or straightening preparations

33053000 — Hair lacquers

33059000 — Other hair preparations

Oral care

33061000 — Dentifrices (toothpaste/tooth powder)

33062000 — Dental floss (retail)

33069000 — Other oral or dental hygiene preparations (except dentifrice and floss)

Body care & personal hygiene

33071000 — Shaving preparations

33072000 — Deodorants and antiperspirants

33079000 — Other cosmetic/toiletry preparations

Soaps & detergents

34011100 — Toilet soaps (including medicinal)

34011900 — Other solid soaps

34012090 — Soap in liquid form

34013000 — Organic surface-active products for washing the skin

Other chemicals & lubricants

34039900 — Lubricating preparations (non-petroleum-based)

Candles

34060000 — Candles and similar articles

Insect repellents

38089190 — Insecticides for retail sale (excluding certain active substances)

Plastic packaging & goods

39233010 — Plastic bottles, flasks and similar containers ≤2L

39269097 — Other articles of plastic (not otherwise specified)

Rubber products

40141000 — Condoms

40149000 — Hygiene/pharmacy rubber articles (excluding condoms)

40169997 — Other rubber articles (non-hardened)

Textiles & clothing

61152100 — Synthetic fiber pantyhose <67 decitex

62121090 — Brassieres (excluding retail assortments)

62122000 — Girdles and panty-girdles

Footwear accessories

64069050 — Removable insoles and similar accessories

Glass packaging

70109045 — Glass bottles/flasks 0.15–0.33 L

Mechanical & electrical components

84139100 — Parts of pumps for liquids

85163100 — Electric hair dryers

85163200 — Other electric hair-dressing appliances (excluding dryers)

85437090 — Electrical machines/apparatus with an independent function

Eyewear

90041091 — Sunglasses with plastic lenses

90049010 — Spectacles with plastic lenses (excluding sunglasses)

90049090 — Spectacles/eyewear (other, excluding plastic lenses/sun/test types)

Medical devices & instruments

90181990 — Electro-diagnostic apparatus

90184990 — Dental instruments/apparatus

90189010 — Blood pressure monitors

90189084 — Other medical/surgical instruments

90191010 — Electric vibro-massagers

90211010 — Orthopedic appliances

Brushes & accessories

96032100 — Toothbrushes (including denture brushes)

96032930 — Hairbrushes

96151900 — Plastic hair rollers/bobbers

96159000 — Combs, hairpins, clips, curlers, etc. (non-electric)

Insulated containers

96170000 — Thermos bottles and vacuum-insulated containers

Hygiene products

96190079 — Feminine hygiene articles (non-textile)

96190081 — Baby diapers (non-textile)

96190089 — Other hygiene articles (e.g., incontinence pads)

RESPONSE REQUIREMENTS:

Respond ONLY with valid JSON

Use exactly this structure:

REQUIRED JSON FORMAT:
{{
  "hscode": "96170000"
}}

Do NOT include any text outside the JSON

HS code must be 8 digits

Choose only from the allowed list above