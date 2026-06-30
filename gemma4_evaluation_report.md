# Gemma4:E4B IDP Invoice Extraction Evaluation Report

This report details the extraction quality of the redesigned **Intelligent Document Processing (IDP)** pipeline using **Gemma4:E4B** compared to the legacy rule-based prompts.

## Environment and Model Verification

```
Extraction Engine : hybrid_allam
Active Model      : gemma4:e4b
Ollama Version    : 0.30.11
Model from .env   : gemma4:e4b
```


# Invoice: 1_BAHRA-CABLES-60129398.png

- **OCR Time**: 16.57s
- **LLM Time**: 15.52s
- **Total Time**: 37.23s
- **Confidence**: 0.70

---------------------------------

OCR Preview
```
Invoice TIN: 300140759700003 Date: 02.01.2019 Page: 1/4 Description الوصف Quantity Unit price Amt (SAR) VAT % Tax Price Total Price Customer: The Civil Works Joint Venture Of Saudi Arabian Bechtel Company, Almabani General Contractors and Consolidated Contractors Company W.LL BACS Building Malaz Riyadh Kingdom of Saudi Arabia- Al riyadh S.O # 30039828 D.N # 40132294 P. O # M-BCW-000SHG-CEGO-FOR0-00010 Date of Supply : 01.01.2019 Description الوصف Quantity Unit price Amt (SAR) VAT % Tax Price Total Price Customer: Bahra Advanced Cable Manufacturing Co. Ltd. White: Customer البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: لل
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "Invoice", "document": {"number": "300140759700003", "date": "02.01.2019", "currency": "SAR"}, "vendor": {"name_ar": null, "name_en": null, "vat_number": null, "address_ar": null, "address_en": null}, "customer": {"name_ar": null, "name_en": "The Civil Works Joint Venture Of Saudi Arabian Bechtel Company, Almabani General Contractors and Consolidated Contractors Company", "address_ar": null, "address_en": "BACS Building Malaz Riyadh Kingdom of Saudi Arabia"}, "financials": {"subtotal": null, "tax_amount": null, "total_amount": null}, "metadata": {"purchase_order": "M-BCW-000SHG-CEGO-FOR0-00010", "reference_number": "30039828", "payment_terms": null, "notes": ""}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "300140759700003",
  "vat_number": "",
  "document_date": "02.01.2019",
  "currency": "SAR",
  "vendor_name_ar": "",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "The Civil Works Joint Venture Of Saudi Arabian Bechtel Company, Almabani General Contractors and Consolidated Contractors Company",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "document_type": "Invoice",
  "document": {
    "number": "300140759700003",
    "date": "02.01.2019",
    "currency": "SAR"
  },
  "vendor": {
    "name_ar": null,
    "name_en": null,
    "vat_number": null,
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": null,
    "name_en": "The Civil Works Joint Venture Of Saudi Arabian Bechtel Company, Almabani General Contractors and Consolidated Contractors Company",
    "address_ar": null,
    "address_en": "BACS Building Malaz Riyadh Kingdom of Saudi Arabia"
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": "M-BCW-000SHG-CEGO-FOR0-00010",
    "reference_number": "30039828",
    "payment_terms": null,
    "notes": ""
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ❌ | Hallucinated or wrong value: '300140759700003' |
| VAT Number | ✅ | Extracted correctly |
| Date | ✅ | Extracted correctly |
| Currency | ✅ | Extracted correctly |
| Vendor Arabic | ✅ | Correctly empty |
| Vendor English | ✅ | Extracted correctly |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Extracted correctly |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Extracted correctly |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---------------------------------


# Invoice: 1_BAHRI-BOLLORE-JED301286.png

- **OCR Time**: 6.92s
- **LLM Time**: 13.65s
- **Total Time**: 25.55s
- **Confidence**: 0.55

---------------------------------

OCR Preview
```
فترة مضربة رقم : JED301286 Due Date : 02/08/2018 TAX INVOICE P. O. Box 9568 Jeddah 21243 Jeddah, Saudi Arabia Tel: +966 2 667 4695 / +966 12 669 3445 شركة بحري بولوريه لوجيستكس - جده جهة مكنى رقم :V0E9999999999999999999999999999999
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "Tax Invoice", "document": {"number": "JED301286", "date": null, "currency": ""}, "vendor": {"name_ar": "شركة بحري بولوريه لوجيستكس - جده", "name_en": null, "vat_number": null, "address_ar": "P. O. Box 9568 Jeddah 21243 Jeddah, Saudi Arabia", "address_en": "P. O. Box 9568 Jeddah 21243 Jeddah, Saudi Arabia"}, "customer": {"name_ar": null, "name_en": null, "address_ar": null, "address_en": ""}, "financials": {"subtotal": null, "tax_amount": null, "total_amount": null}, "metadata": {"purchase_order": "V0E9999999999999999999999999999999", "reference_number": null, "payment_terms": "Due Date : 02/08/2018", "notes": ""}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "JED301286",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "شركة بحري بولوريه لوجيستكس - جده",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "P. O. Box 9568 Jeddah 21243 Jeddah, Saudi Arabia",
  "address_en": "P. O. Box 9568 Jeddah 21243 Jeddah, Saudi Arabia",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "document_type": "Tax Invoice",
  "document": {
    "number": "JED301286",
    "date": null,
    "currency": ""
  },
  "vendor": {
    "name_ar": "شركة بحري بولوريه لوجيستكس - جده",
    "name_en": null,
    "vat_number": null,
    "address_ar": "P. O. Box 9568 Jeddah 21243 Jeddah, Saudi Arabia",
    "address_en": "P. O. Box 9568 Jeddah 21243 Jeddah, Saudi Arabia"
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": ""
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": "V0E9999999999999999999999999999999",
    "reference_number": null,
    "payment_terms": "Due Date : 02/08/2018",
    "notes": ""
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Extracted correctly |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Extracted correctly |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ✅ | Extracted correctly |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ❌ | Hallucinated or wrong value: 'P. O. Box 9568 Jeddah 21243 Jeddah, Saudi Arabia' |
| Address English | ✅ | Extracted correctly |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---------------------------------


# Invoice: 1_BAIT-AL-BAKOURAH-50005.png

- **OCR Time**: 14.26s
- **LLM Time**: 11.49s
- **Total Time**: 30.67s
- **Confidence**: 0.35

---------------------------------

OCR Preview
```
<!DOCTYPE html>
<html lang="en"><head>

</head>
<body data-bbox="0 0 999 998">
<div data-bbox="0 0 999 998">
<section data-bbox="0 0 999 12">
<h1 data-bbox="0 0 999 12">مؤسسة بيت الباكورة للتجارة BAIT AL-BAKOURAH EST. FOR TRADING</h1> </section>
<section data-bbox="0 14 999 386">
<div data-bbox="0 14 999 386">
<h2 data-bbox="0 14 999 25">VAT INVOICE</h2> <div data-bbox="0 27 999 386"><table data-bbox="0 27 999 386" width="100%">
<tbody data-bbox="1 27 998 385">
<tr data-bbox="1 27 998 385">
<td data-bbox="1 27 998 385"><table data-bbox="1 27 998 384" width="100%">
<tbody data-bbox="2 27 997 383">
<tr data-bbox="2 27 997 383">
<td data-bbox="2 27 997 383"><table data-bbox="2 27 997 383" width="100%">
<tbody data-bbox="3 27 996 382">
<tr data-bbox="3 27 996 382">
<td data-bbox="3 27 996 382"><table data-bbox="3 27 996 381" width="100%">
<tbody data-bbox="4 27 995 381">
<tr data-bbox="4 27 995 381">
<td data-bbox="4 27 995 381"><table data-bbox="4 27 995 380" width="100%">
<tbody data-bbox="5 27 994 380">
<tr data-bbox="5 27 994 380">
<td data-bbox="5 27 994 380"><table data-bbox="5 27 994 379" width="100%">
<tbody data-bbox="6 27 993 379">
<tr data-bbox="6 27 993 379">
<td data-bbox="6 27 993 379"><table data-bbox="6 27 993 378" width="100%">
<tbody data-bbox="7 27 992 378">
<tr data-bbox="7 27 992 378">
<td data-bbox="7 27 992 378"><table data-bbox="7 27 992 377" width="100%">
<tbody data-bbox="8 27 991 377">
<tr data-bbox="8 27 991 377">
<td data-bbox="8 27 991 377"><table data-bbox="8 27 991 376" width="100%">
<tbody data-bbox="9 27 9
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "VAT Invoice", "document": {"number": null, "date": null, "currency": ""}, "vendor": {"name_ar": "مؤسسة بيت الباكورة للتجارة", "name_en": "BAIT AL-BAKOURAH EST. FOR TRADING", "vat_number": null, "address_ar": null, "address_en": null}, "customer": {"name_ar": null, "name_en": null, "address_ar": null, "address_en": ""}, "financials": {"subtotal": null, "tax_amount": null, "total_amount": null}, "metadata": {"purchase_order": null, "reference_number": null, "payment_terms": null, "notes": null}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "مؤسسة بيت الباكورة للتجارة",
  "vendor_name_en": "BAIT AL-BAKOURAH EST. FOR TRADING",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "document_type": "VAT Invoice",
  "document": {
    "number": null,
    "date": null,
    "currency": ""
  },
  "vendor": {
    "name_ar": "مؤسسة بيت الباكورة للتجارة",
    "name_en": "BAIT AL-BAKOURAH EST. FOR TRADING",
    "vat_number": null,
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": ""
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": null
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Extracted correctly |
| VAT Number | ✅ | Extracted correctly |
| Date | ✅ | Extracted correctly |
| Currency | ✅ | Extracted correctly |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ✅ | Extracted correctly |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Extracted correctly |
| Address English | ✅ | Extracted correctly |
| Subtotal | ❌ | Missed or wrong value (got 'None', expected '139162.0') |
| Tax | ❌ | Missed or wrong value (got 'None', expected '6958.1') |
| Total | ❌ | Missed or wrong value (got 'None', expected '146120.1') |


---------------------------------


# Invoice: 1_BAIT-AL-BAKOURAH-50005_f604debc50ee.png

- **OCR Time**: 14.81s
- **LLM Time**: 12.93s
- **Total Time**: 32.59s
- **Confidence**: 0.35

---------------------------------

OCR Preview
```
<!DOCTYPE html>
<html lang="en"><head>

</head>
<body data-bbox="0 0 999 998">
<div data-bbox="0 0 999 998">
<section data-bbox="0 0 999 12">
<h1 data-bbox="0 0 999 12">مؤسسة بيت الباكورة للتجارة BAIT AL-BAKOURAH EST. FOR TRADING</h1> </section>
<section data-bbox="0 14 999 386">
<div data-bbox="0 14 999 386">
<h2 data-bbox="0 14 999 25">VAT INVOICE</h2> <div data-bbox="0 27 999 386"><table data-bbox="0 27 999 386" width="100%">
<tbody data-bbox="1 27 998 385">
<tr data-bbox="1 27 998 385">
<td data-bbox="1 27 998 385"><table data-bbox="1 27 998 384" width="100%">
<tbody data-bbox="2 27 997 383">
<tr data-bbox="2 27 997 383">
<td data-bbox="2 27 997 383"><table data-bbox="2 27 997 383" width="100%">
<tbody data-bbox="3 27 996 382">
<tr data-bbox="3 27 996 382">
<td data-bbox="3 27 996 382"><table data-bbox="3 27 996 381" width="100%">
<tbody data-bbox="4 27 995 381">
<tr data-bbox="4 27 995 381">
<td data-bbox="4 27 995 381"><table data-bbox="4 27 995 380" width="100%">
<tbody data-bbox="5 27 994 380">
<tr data-bbox="5 27 994 380">
<td data-bbox="5 27 994 380"><table data-bbox="5 27 994 379" width="100%">
<tbody data-bbox="6 27 993 379">
<tr data-bbox="6 27 993 379">
<td data-bbox="6 27 993 379"><table data-bbox="6 27 993 378" width="100%">
<tbody data-bbox="7 27 992 378">
<tr data-bbox="7 27 992 378">
<td data-bbox="7 27 992 378"><table data-bbox="7 27 992 377" width="100%">
<tbody data-bbox="8 27 991 377">
<tr data-bbox="8 27 991 377">
<td data-bbox="8 27 991 377"><table data-bbox="8 27 991 376" width="100%">
<tbody data-bbox="9 27 9
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "VAT Invoice", "document": {"number": null, "date": null, "currency": ""}, "vendor": {"name_ar": "مؤسسة بيت الباكورة للتجارة", "name_en": "BAIT AL-BAKOURAH EST. FOR TRADING", "vat_number": null, "address_ar": null, "address_en": null}, "customer": {"name_ar": null, "name_en": null, "address_ar": null, "address_en": ""}, "financials": {"subtotal": null, "tax_amount": null, "total_amount": null}, "metadata": {"purchase_order": null, "reference_number": null, "payment_terms": null, "notes": null}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "مؤسسة بيت الباكورة للتجارة",
  "vendor_name_en": "BAIT AL-BAKOURAH EST. FOR TRADING",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "document_type": "VAT Invoice",
  "document": {
    "number": null,
    "date": null,
    "currency": ""
  },
  "vendor": {
    "name_ar": "مؤسسة بيت الباكورة للتجارة",
    "name_en": "BAIT AL-BAKOURAH EST. FOR TRADING",
    "vat_number": null,
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": ""
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": null
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ❌ | Hallucinated or wrong value: 'مؤسسة بيت الباكورة للتجارة' |
| Vendor English | ❌ | Hallucinated or wrong value: 'BAIT AL-BAKOURAH EST. FOR TRADING' |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---------------------------------


# Invoice: 1_CCS-CONSTRUCTION-COMPUTER-11341.png

- **OCR Time**: 6.27s
- **LLM Time**: 12.98s
- **Total Time**: 24.15s
- **Confidence**: 0.10

---------------------------------

OCR Preview
```
Below is the plain text representation of the image for plain text conversion. Do not hallucinate.
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "Invoice", "document": {"number": "INV-2023-105", "date": "October 26, 2023", "currency": "USD"}, "vendor": {"name_ar": null, "name_en": "Global Tech Solutions LLC", "vat_number": "VAT-987654321", "address_ar": null, "address_en": "123 Silicon Valley Blvd, CA 90210"}, "customer": {"name_ar": null, "name_en": "Acme Corp", "address_ar": null, "address_en": "456 Business Way, NY 10001"}, "financials": {"subtotal": 850.0, "tax_amount": 72.5, "total_amount": 922.5}, "metadata": {"purchase_order": null, "reference_number": null, "payment_terms": "Net 30", "notes": ""}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "INV-2023-105",
  "vat_number": "VAT-987654321",
  "document_date": "October 26, 2023",
  "currency": "USD",
  "vendor_name_ar": "",
  "vendor_name_en": "Global Tech Solutions LLC",
  "customer_name_ar": "",
  "customer_name_en": "Acme Corp",
  "address_ar": "",
  "address_en": "123 Silicon Valley Blvd, CA 90210",
  "subtotal": 850.0,
  "tax_amount": 72.5,
  "total_amount": 922.5,
  "document_type": "Invoice",
  "document": {
    "number": "INV-2023-105",
    "date": "October 26, 2023",
    "currency": "USD"
  },
  "vendor": {
    "name_ar": null,
    "name_en": "Global Tech Solutions LLC",
    "vat_number": "VAT-987654321",
    "address_ar": null,
    "address_en": "123 Silicon Valley Blvd, CA 90210"
  },
  "customer": {
    "name_ar": null,
    "name_en": "Acme Corp",
    "address_ar": null,
    "address_en": "456 Business Way, NY 10001"
  },
  "financials": {
    "subtotal": 850.0,
    "tax_amount": 72.5,
    "total_amount": 922.5
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": "Net 30",
    "notes": ""
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ❌ | Hallucinated or wrong value: 'INV-2023-105' |
| VAT Number | ❌ | Hallucinated or wrong value: 'VAT-987654321' |
| Date | ❌ | Hallucinated or wrong value: 'October 26, 2023' |
| Currency | ❌ | Hallucinated or wrong value: 'USD' |
| Vendor Arabic | ✅ | Correctly empty |
| Vendor English | ❌ | Hallucinated or wrong value: 'Global Tech Solutions LLC' |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ❌ | Hallucinated or wrong value: 'Acme Corp' |
| Address Arabic | ✅ | Correctly empty |
| Address English | ❌ | Hallucinated or wrong value: '123 Silicon Valley Blvd, CA 90210' |
| Subtotal | ❌ | Hallucinated or wrong value: '850.0' |
| Tax | ❌ | Hallucinated or wrong value: '72.5' |
| Total | ❌ | Hallucinated or wrong value: '922.5' |


---------------------------------


# Invoice: 1_CONTRACTORS-AMBASSADOR-1738.png

- **OCR Time**: 7.37s
- **LLM Time**: 14.15s
- **Total Time**: 26.49s
- **Confidence**: 0.50

---------------------------------

OCR Preview
```
VAT INVOICE فاتورة ضريبية اسم الشركة ، _ مؤسسة سفير المقاولين للتجارة عنوان:__ مخرج 17 - حي الفيصليه - شارع ابراهيم الزجاج __الرياض - المملكة العربية السعودية Address: CIVIL WORK JOINT VENTURE _ تأريخ الظاتورة ،_ 13-01-2019 Due Date: _ 1738 _ تاريخ التوريد،_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
```

---------------------------------

Raw Gemma Output
```json
{
  "document_type": "VAT INVOICE",
  "document": {
    "number": null,
    "date": "13-01-2019",
    "currency": null
  },
  "vendor": {
    "name_ar": "مؤسسة سفير المقاولين للتجارة",
    "name_en": "CIVIL WORK JOINT VENTURE",
    "vat_number": null,
    "address_ar": "مخرج 17 - حي الفيصليه - شارع ابراهيم الزجاج __الرياض - المملكة العربية السعودية",
    "address_en": ""
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": ""
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": ""
  }
}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "13-01-2019",
  "currency": "",
  "vendor_name_ar": "مؤسسة سفير المقاولين للتجارة",
  "vendor_name_en": "CIVIL WORK JOINT VENTURE",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "مخرج 17 - حي الفيصليه - شارع ابراهيم الزجاج __الرياض - المملكة العربية السعودية",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "document_type": "VAT INVOICE",
  "document": {
    "number": null,
    "date": "13-01-2019",
    "currency": null
  },
  "vendor": {
    "name_ar": "مؤسسة سفير المقاولين للتجارة",
    "name_en": "CIVIL WORK JOINT VENTURE",
    "vat_number": null,
    "address_ar": "مخرج 17 - حي الفيصليه - شارع ابراهيم الزجاج __الرياض - المملكة العربية السعودية",
    "address_en": ""
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": ""
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": ""
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Extracted correctly |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Extracted correctly |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ❌ | Hallucinated or wrong value: 'CIVIL WORK JOINT VENTURE' |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Extracted correctly |
| Address Arabic | ✅ | Extracted correctly |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---------------------------------


# Invoice: 1_CPS-CONSTRUCTION-PLANT-490.png

- **OCR Time**: 16.32s
- **LLM Time**: 11.35s
- **Total Time**: 32.53s
- **Confidence**: 0.35

---------------------------------

OCR Preview
```
For the account of Riyadh Metro Project, the Civil Works Joint Venture the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "Invoice", "document": {"number": null, "date": null, "currency": null}, "vendor": {"name_ar": null, "name_en": null, "vat_number": null, "address_ar": null, "address_en": null}, "customer": {"name_ar": "Riyadh Metro Project, the Civil Works Joint Venture", "name_en": "Riyadh Metro Project, the Civil Works Joint Venture", "address_ar": null, "address_en": null}, "financials": {"subtotal": null, "tax_amount": null, "total_amount": null}, "metadata": {"purchase_order": null, "reference_number": null, "payment_terms": null, "notes": null}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "",
  "vendor_name_en": "",
  "customer_name_ar": "Riyadh Metro Project, the Civil Works Joint Venture",
  "customer_name_en": "Riyadh Metro Project, the Civil Works Joint Venture",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "document_type": "Invoice",
  "document": {
    "number": null,
    "date": null,
    "currency": null
  },
  "vendor": {
    "name_ar": null,
    "name_en": null,
    "vat_number": null,
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": "Riyadh Metro Project, the Civil Works Joint Venture",
    "name_en": "Riyadh Metro Project, the Civil Works Joint Venture",
    "address_ar": null,
    "address_en": null
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": null
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ✅ | Correctly empty |
| Vendor English | ✅ | Correctly empty |
| Customer Arabic | ❌ | Hallucinated or wrong value: 'Riyadh Metro Project, the Civil Works Joint Venture' |
| Customer English | ✅ | Extracted correctly |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---------------------------------


# Invoice: 20220820_160723879.jpg

- **OCR Time**: 8.33s
- **LLM Time**: 14.23s
- **Total Time**: 27.42s
- **Confidence**: 0.80

---------------------------------

OCR Preview
```
I-BAR T3 Unit of Anjali Hotels Pvt Ltd Check in area International Airport, Cochin, Kerala GST 32AACCA2654H1Z3 Name: Date: 20/07/22 Pick Up 22:02 Cashier: ANSHAL Bill No.: 1667 JOY Token No.: 157 Item Qty. Price Amount Tea 1 57.14 57.14 Cheese&Tomato 1 209.52 209.52 Sandwich Total Qty: 2 Sub Total 266.66 CGST 2.5% 6.67 SGST 2.5% 6.67 Grand Total 280.00 FSSAI Lic No. 10021807000007 Thanks Your feedback matters us most to improve ourselves. Please scan below to provide your feedback:
```

---------------------------------

Raw Gemma Output
```json
{
  "document_type": "Receipt",
  "document": {
    "number": "1667",
    "date": "20/07/22",
    "currency": ""
  },
  "vendor": {
    "name_ar": "",
    "name_en": "Anjali Hotels Pvt Ltd",
    "vat_number": "32AACCA2654H1Z3",
    "address_ar": "",
    "address_en": "Check in area International Airport, Cochin, Kerala"
  },
  "customer": {
    "name_ar": "",
    "name_en": "I-BAR T3 Unit",
    "address_ar": "",
    "address_en": ""
  },
  "financials": {
    "subtotal": 266.66,
    "tax_amount": 13.34,
    "total_amount": 280.00
  },
  "metadata": {
    "purchase_order": "",
    "reference_number": "JOY Token No.: 157",
    "payment_terms": "Cash",
    "notes": ""
  }
}
```

---------------------------------

Final JSON
```json
{
  "document_number": "1667",
  "vat_number": "32AACCA2654H1Z3",
  "document_date": "20/07/22",
  "currency": "",
  "vendor_name_ar": "",
  "vendor_name_en": "Anjali Hotels Pvt Ltd",
  "customer_name_ar": "",
  "customer_name_en": "I-BAR T3 Unit",
  "address_ar": "",
  "address_en": "Check in area International Airport, Cochin, Kerala",
  "subtotal": 266.66,
  "tax_amount": 13.34,
  "total_amount": 280.0,
  "document_type": "Receipt",
  "document": {
    "number": "1667",
    "date": "20/07/22",
    "currency": ""
  },
  "vendor": {
    "name_ar": "",
    "name_en": "Anjali Hotels Pvt Ltd",
    "vat_number": "32AACCA2654H1Z3",
    "address_ar": "",
    "address_en": "Check in area International Airport, Cochin, Kerala"
  },
  "customer": {
    "name_ar": "",
    "name_en": "I-BAR T3 Unit",
    "address_ar": "",
    "address_en": ""
  },
  "financials": {
    "subtotal": 266.66,
    "tax_amount": 13.34,
    "total_amount": 280.0
  },
  "metadata": {
    "purchase_order": "",
    "reference_number": "JOY Token No.: 157",
    "payment_terms": "Cash",
    "notes": ""
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Extracted correctly |
| VAT Number | ❌ | Missed or wrong value (got '32AACCA2654H1Z3', expected '32AABCA8749G1Z2') |
| Date | ✅ | Extracted correctly |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ✅ | Correctly empty |
| Vendor English | ✅ | Extracted correctly |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Extracted correctly |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Extracted correctly |
| Subtotal | ✅ | Extracted correctly |
| Tax | ✅ | Extracted correctly |
| Total | ✅ | Extracted correctly |


---------------------------------


# Invoice: 20220820_160841493.jpg

- **OCR Time**: 10.79s
- **LLM Time**: 12.25s
- **Total Time**: 27.85s
- **Confidence**: 0.80

---------------------------------

OCR Preview
```
مطعم طريق المطار ابو حدري- علريق المطار الحفوفَ الشرقية 0556829522 فاتورة ضريبة مبسطة الرقم الضريبي : 310426975200003 Owner : النادل ------------------------------الـمجموع--------------- كـسة لحم مع رش 1 24 00 ايدام دجاج مع خبس شاسي ترك شاسي سادة 1 % بيبس- صغير ماء كبير 1 6 00 2 00 1 00 2.00 ------------------------------المجموع الفرعي : (المبلغ الاجمالي (بضون الضريبة ) : الضريبة قيمة المضافة : (المبلغ الإجمالي (مع الخـربية ) : المبلغ المستحق : المبلغ المستحق نفداً مجموع المبلغ(نقدا) 48.00 SAR 41.74 SAR 6.26 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 21/07/2022 1:04:40 PM 21/07/2022 1:04:44 PM Thank you نسخة العميل الفاتورة الإلكترونية QR
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "Invoice", "document": {"number": null, "date": "21/07/2022", "currency": "SAR"}, "vendor": {"name_ar": "مطعم طريق المطار ابو حدري- علريق المطار الحفوفَ الشرقية", "name_en": null, "vat_number": "310426975200003", "address_ar": null, "address_en": null}, "customer": {"name_ar": null, "name_en": null, "address_ar": null, "address_en": null}, "financials": {"subtotal": 41.74, "tax_amount": 6.26, "total_amount": 48.00}, "metadata": {"purchase_order": null, "reference_number": null, "payment_terms": null, "notes": null}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "310426975200003",
  "document_date": "21/07/2022",
  "currency": "SAR",
  "vendor_name_ar": "مطعم طريق المطار ابو حدري- علريق المطار الحفوفَ الشرقية",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": 41.74,
  "tax_amount": 6.26,
  "total_amount": 48.0,
  "document_type": "Invoice",
  "document": {
    "number": null,
    "date": "21/07/2022",
    "currency": "SAR"
  },
  "vendor": {
    "name_ar": "مطعم طريق المطار ابو حدري- علريق المطار الحفوفَ الشرقية",
    "name_en": null,
    "vat_number": "310426975200003",
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": null
  },
  "financials": {
    "subtotal": 41.74,
    "tax_amount": 6.26,
    "total_amount": 48.0
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": null
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Extracted correctly |
| Date | ✅ | Extracted correctly |
| Currency | ✅ | Extracted correctly |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ✅ | Correctly empty |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Extracted correctly |
| Tax | ✅ | Extracted correctly |
| Total | ✅ | Extracted correctly |


---------------------------------


# Invoice: 20220820_160954815.jpg

- **OCR Time**: 15.70s
- **LLM Time**: 11.91s
- **Total Time**: 32.41s
- **Confidence**: 0.40

---------------------------------

OCR Preview
```
{TAXI AIRPORT SERVICE} خدمات أجرة المطار S.R. ريال 14-0 فاتورة INVOICE من المطار الدمام Dammam Airport استلمت من السيد / السادة ...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "Invoice", "document": {"number": null, "date": null, "currency": "S.R."}, "vendor": {"name_ar": "خدمات أجرة المطار", "name_en": "TAXI AIRPORT SERVICE", "vat_number": null, "address_ar": null, "address_en": null}, "customer": {"name_ar": null, "name_en": null, "address_ar": null, "address_en": null}, "financials": {"subtotal": null, "tax_amount": null, "total_amount": "14.0"}, "metadata": {"purchase_order": null, "reference_number": null, "payment_terms": null, "notes": "From Dammam Airport"}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "",
  "currency": "S.R.",
  "vendor_name_ar": "خدمات أجرة المطار",
  "vendor_name_en": "TAXI AIRPORT SERVICE",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": 14.0,
  "document_type": "Invoice",
  "document": {
    "number": null,
    "date": null,
    "currency": "S.R."
  },
  "vendor": {
    "name_ar": "خدمات أجرة المطار",
    "name_en": "TAXI AIRPORT SERVICE",
    "vat_number": null,
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": null
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": "14.0"
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": "From Dammam Airport"
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Extracted correctly |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ✅ | Extracted correctly |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ❌ | Hallucinated or wrong value: '14.0' |


---------------------------------


# Invoice: 20220820_161037175.jpg

- **OCR Time**: 7.19s
- **LLM Time**: 13.35s
- **Total Time**: 25.47s
- **Confidence**: 0.30

---------------------------------

OCR Preview
```
Taxi Airport Service ـ خدمات أجرة المطار S.R. ريال 240 فاتورة INVOICE To: Dammam Airport استلمت من السيد / السادة ...السيد ...والسيد ...مبلغ وقدره ...ملبس ...و...مصدقة ...التاريخ : ١٤-٥-٢٠ Date : ١٤-٦-٢٠ Receiver Sig.
```

---------------------------------

Raw Gemma Output
```json
{
  "document_type": "Invoice",
  "document": {
    "number": null,
    "date": "14-6-20",
    "currency": "SAR"
  },
  "vendor": {
    "name_ar": "Taxi Airport Service ـ خدمات أجرة المطار",
    "name_en": null,
    "vat_number": null,
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": "Dammam Airport",
    "name_en": null,
    "address_ar": null,
    "address_en": null
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": "240"
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": ""
  }
}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "14-6-20",
  "currency": "SAR",
  "vendor_name_ar": "Taxi Airport Service ـ خدمات أجرة المطار",
  "vendor_name_en": "",
  "customer_name_ar": "Dammam Airport",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": 240.0,
  "document_type": "Invoice",
  "document": {
    "number": null,
    "date": "14-6-20",
    "currency": "SAR"
  },
  "vendor": {
    "name_ar": "Taxi Airport Service ـ خدمات أجرة المطار",
    "name_en": null,
    "vat_number": null,
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": "Dammam Airport",
    "name_en": null,
    "address_ar": null,
    "address_en": null
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": "240"
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": ""
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Extracted correctly |
| Currency | ❌ | Missed or wrong value (got 'SAR', expected 'S.R.') |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ✅ | Extracted correctly |
| Customer Arabic | ❌ | Hallucinated or wrong value: 'Dammam Airport' |
| Customer English | ✅ | Extracted correctly |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Extracted correctly |


---------------------------------


# Invoice: 4_JY2020-07-JV000603.png

- **OCR Time**: 6.60s
- **LLM Time**: 10.01s
- **Total Time**: 21.48s
- **Confidence**: 0.35

---------------------------------

OCR Preview
```
هـــــــــــــــــــــــــــــــ
```

---------------------------------

Raw Gemma Output
```json
{"document_type": null, "document": {"number": null, "date": null, "currency": null}, "vendor": {"name_ar": null, "name_en": null, "vat_number": null, "address_ar": null, "address_en": null}, "customer": {"name_ar": null, "name_en": null, "address_ar": null, "address_en": null}, "financials": {"subtotal": null, "tax_amount": null, "total_amount": null}, "metadata": {"purchase_order": null, "reference_number": null, "payment_terms": null, "notes": null}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "document_type": "invoice",
  "document": {
    "number": null,
    "date": null,
    "currency": null
  },
  "vendor": {
    "name_ar": null,
    "name_en": null,
    "vat_number": null,
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": null
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": null
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ✅ | Correctly empty |
| Vendor English | ✅ | Correctly empty |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---------------------------------


# Invoice: 4_JY2020-07-JV000603_033bb84135e8.png

- **OCR Time**: 4.80s
- **LLM Time**: 9.57s
- **Total Time**: 19.41s
- **Confidence**: 0.35

---------------------------------

OCR Preview
```
هـــــــــــــــــــــــــــــــ
```

---------------------------------

Raw Gemma Output
```json
{"document_type": null, "document": {"number": null, "date": null, "currency": null}, "vendor": {"name_ar": null, "name_en": null, "vat_number": null, "address_ar": null, "address_en": null}, "customer": {"name_ar": null, "name_en": null, "address_ar": null, "address_en": null}, "financials": {"subtotal": null, "tax_amount": null, "total_amount": null}, "metadata": {"purchase_order": null, "reference_number": null, "payment_terms": null, "notes": null}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "document_type": "invoice",
  "document": {
    "number": null,
    "date": null,
    "currency": null
  },
  "vendor": {
    "name_ar": null,
    "name_en": null,
    "vat_number": null,
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": null
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": null
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ✅ | Correctly empty |
| Vendor English | ✅ | Correctly empty |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---------------------------------


# Invoice: 4_JY2020-07-JV000710.png

- **OCR Time**: 15.50s
- **LLM Time**: 13.78s
- **Total Time**: 34.11s
- **Confidence**: 0.70

---------------------------------

OCR Preview
```
**THIS INVOICE IS RELTAED TO SAP INVOICE NUMBER 901840429 ** فاتوره مبيعات / Sales Invoice التاريخ 18.03.2020 Revenue Number 901840429 901840429 Date 18.03.2020 Invoice Number P.O.Box / P.Code / City ص.ب/ الرمز البريدي/ المدينة 301/11411/Riyadh Tel. Fax. VAT Registration Number Customer Name Customer No SABCO ALMABANI CCC WILL PACKAGE NO. 1 P.O.Box / P.Code / City ص.ب/ الرمز البريدي/ المدينة +966 11 510 5600 +966 11 510 5601 P.O. Box 28708, Riyadh 11447 P.O. Box 28708, Riyadh 11447 Customer Name SABCO ALMABANI CCC WILL PACKAGE NO. 1 P.O.Box / P.Code / City ص.ب/ الرمز البريدي/ المدينة +966 11 510 5600 +966 11 510 5601 P.O. Box 28708, Riyadh 11447 P.O. Box 28708, Riyadh 11447 VAT Registration Number Purchase Order NO M-BCW-000TR0-CE00-FOR0-00076 S/N Description QTY Unit Price Total Price السعر الاجمالي للخدمة % السعر الجنيه للخدمة % السعر الاجمالي للفاتوره بدون الضريبة % الفيضة الاجمالية للفاتورة مع الضريبة 50 40 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 989.00 25.25 329,472.67 50 41 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 993.00 25.25 329,472.67 50 42 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 1,032.00 25.25 329,472.67 50 43 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 1,010.00 25.25 329,472.67 50 44 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 987.00 25.25 329,472.67 50 45 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 971.00 25.25 329,472.67 50 50 5X16MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 993.00 25.25 329,472.67 50 51 5X16MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 1,032.00 25.25 329
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "Invoice", "document": {"number": "901840429", "date": "18.03.2020", "currency": ""}, "vendor": {"name_ar": null, "name_en": null, "vat_number": null, "address_ar": null, "address_en": null}, "customer": {"name_ar": null, "name_en": "SABCO ALMABANI CCC", "address_ar": null, "address_en": ""}, "financials": {"subtotal": null, "tax_amount": null, "total_amount": null}, "metadata": {"purchase_order": "M-BCW-000TR0-CE00-FOR0-00076", "reference_number": "901840429", "payment_terms": null, "notes": ""}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "901840429",
  "vat_number": "",
  "document_date": "18.03.2020",
  "currency": "",
  "vendor_name_ar": "",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "SABCO ALMABANI CCC",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "document_type": "Invoice",
  "document": {
    "number": "901840429",
    "date": "18.03.2020",
    "currency": ""
  },
  "vendor": {
    "name_ar": null,
    "name_en": null,
    "vat_number": null,
    "address_ar": null,
    "address_en": null
  },
  "customer": {
    "name_ar": null,
    "name_en": "SABCO ALMABANI CCC",
    "address_ar": null,
    "address_en": ""
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": "M-BCW-000TR0-CE00-FOR0-00076",
    "reference_number": "901840429",
    "payment_terms": null,
    "notes": ""
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Extracted correctly |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Extracted correctly |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ✅ | Correctly empty |
| Vendor English | ✅ | Correctly empty |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Extracted correctly |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Extracted correctly |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---------------------------------


# Invoice: 4_JY2020-07-JV000738.png

- **OCR Time**: 15.76s
- **LLM Time**: 15.68s
- **Total Time**: 36.25s
- **Confidence**: 0.55

---------------------------------

OCR Preview
```
<!DOCTYPE html>
<html><head> </head> <body> <div data-bbox="0 0 999 998"> <h1 data-bbox="265 437 734 442">SODAMCO Industrial Company for Construction Chemicals W.L.L. </h1> <p data-bbox="265 444 734 450"><strong data-bbox="265 444 389 448">Sulay Area – Exit 18, Istanbul road, Facing Train station</strong><br/> T +966 11 473 j751 F +966 11 472 5339<br/> Central Region , Riyadh VAT No. : 300128604300003 C.R. : 4030168494</p> <h2 data-bbox="265 452 734">شركة سودامكو الصناعية لكيمواويات البناة ز.م.م.سني-مخرع-18،طريق اسطنبول،سفحل محطة الفطار-رينز الرقم الضريبي : 02-33333333 سجل تماري رقم : 1549117614-14-0000001</h2> <p data-bbox="265 458 734">Client : Lebanon ،UAE ، Syria ، Qatar ، KSA ، Jordan ، Kuwait ، Oman Description - الوصف - </p> <p data-bbox="265 460 734">Date - تاريخ - Agent - ممثل - CRM - السجل التجاري - VAT - الرقم الضريبي - Customer Ref No - العنوان - العنوان - Riyadh،الملز، شارع الاحساء مبنى اليكس : +966 115 105 600 </p> <h2 data-bbox="265 473 734">المشروع المشترك لشركة بكلل العربية والمياني وإنحداد المفاوولن- V.C.W.J.L.V </h2> <p data-bbox="265 479 734">webertec 311 MC -A+B- (38 Kg) (ويبيرتك 311 م سي - أ + بي(38 كغ ) webertec 301 (25 Kg) (ويبيرتك 301 (25 كغ ) </p> <h2 data-bbox="265 492 734">Maturity date - تاريخ الإستحقاق - Warehouse - مخزن - </h2> <p data-bbox="265 498 734">Total Before VAT : 1,501.500 SAR Total After VAT : 1,501.500 SAR Net to Pay : 1,576.575 SAR </p> <h2 data-bbox="265 508 734">Remark - ملحوظة - </h2> <p data-bbox="265 514 734">SAR ONE THOUSAND FIVE HUNDRED SEVENTY-SIX AND 575 / 1000 ONLY Based On Sales Orders 220012125. Based On Deliveries 200025348.</p> <h3 data-bbox="265 529 734">Delivered By - اصدرت بواسطة RUH</h3> <h3
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "Invoice", "document": {"number": null, "date": null, "currency": "SAR"}, "vendor": {"name_ar": "شركة سودامكو الصناعية لكيمواويات البناة ز.م.م.", "name_en": "SODAMCO Industrial Company for Construction Chemicals W.L.L.", "vat_number": "300128604300003", "address_ar": "سني-مخرع-18،طريق اسطنبول،سفحل محطة الفطار-رينز", "address_en": "Sulay Area – Exit 18, Istanbul road, Facing Train station"}, "customer": {"name_ar": null, "name_en": null, "address_ar": null, "address_en": null}, "financials": {"subtotal": 1501.500, "tax_amount": null, "total_amount": 1576.575}, "metadata": {"purchase_order": "220012125", "reference_number": "200025348", "payment_terms": null, "notes": ""}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "300128604300003",
  "document_date": "",
  "currency": "SAR",
  "vendor_name_ar": "شركة سودامكو الصناعية لكيمواويات البناة ز.م.م.",
  "vendor_name_en": "SODAMCO Industrial Company for Construction Chemicals W.L.L.",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "سني-مخرع-18،طريق اسطنبول،سفحل محطة الفطار-رينز",
  "address_en": "Sulay Area – Exit 18, Istanbul road, Facing Train station",
  "subtotal": 1501.5,
  "tax_amount": null,
  "total_amount": 1576.575,
  "document_type": "Invoice",
  "document": {
    "number": null,
    "date": null,
    "currency": "SAR"
  },
  "vendor": {
    "name_ar": "شركة سودامكو الصناعية لكيمواويات البناة ز.م.م.",
    "name_en": "SODAMCO Industrial Company for Construction Chemicals W.L.L.",
    "vat_number": "300128604300003",
    "address_ar": "سني-مخرع-18،طريق اسطنبول،سفحل محطة الفطار-رينز",
    "address_en": "Sulay Area – Exit 18, Istanbul road, Facing Train station"
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": null
  },
  "financials": {
    "subtotal": 1501.5,
    "tax_amount": null,
    "total_amount": 1576.575
  },
  "metadata": {
    "purchase_order": "220012125",
    "reference_number": "200025348",
    "payment_terms": null,
    "notes": ""
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Extracted correctly |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Extracted correctly |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ✅ | Extracted correctly |
| Customer Arabic | ✅ | Extracted correctly |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ❌ | Hallucinated or wrong value: 'سني-مخرع-18،طريق اسطنبول،سفحل محطة الفطار-رينز' |
| Address English | ✅ | Extracted correctly |
| Subtotal | ✅ | Extracted correctly |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Extracted correctly |


---------------------------------


# Invoice: 4_JY2020-07-JV000756.png

- **OCR Time**: 15.41s
- **LLM Time**: 13.60s
- **Total Time**: 33.88s
- **Confidence**: 0.45

---------------------------------

OCR Preview
```
申しطع ـ مركز تسويق ـ أنظمة الأنابيب السعودي س.ت : 101-43928 P.O. Box : 52408 - Riyadh : 11563 Tel.: 011 4826006 - Fax : 011 4828742 VAT No.: 300041254700003 ـ ( ) أنظمة أنابيب متكاملة ( ) Pipe Fittings Stockist ـ رقم الأم رؤساء ORDER NO. ـ المشروع المشترك للاعمال المدني ـ اسم العميل CUST NAME ـ سعر الوحدة UNIT PRICE ـ رم ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب ال
```

---------------------------------

Raw Gemma Output
```json
{"document_type": "Quotation/Price List", "document": {"number": null, "date": null, "currency": null}, "vendor": {"name_ar": "مركز تسويق أنظمة الأنابيب السعودي", "name_en": null, "vat_number": "300041254700003", "address_ar": "P.O. Box : 52408 - Riyadh : 11563", "address_en": null}, "customer": {"name_ar": null, "name_en": null, "address_ar": null, "address_en": null}, "financials": {"subtotal": null, "tax_amount": null, "total_amount": null}, "metadata": {"purchase_order": null, "reference_number": null, "payment_terms": null, "notes": ""}}
```

---------------------------------

Final JSON
```json
{
  "document_number": "",
  "vat_number": "300041254700003",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "مركز تسويق أنظمة الأنابيب السعودي",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "P.O. Box : 52408 - Riyadh : 11563",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "document_type": "Quotation/Price List",
  "document": {
    "number": null,
    "date": null,
    "currency": null
  },
  "vendor": {
    "name_ar": "مركز تسويق أنظمة الأنابيب السعودي",
    "name_en": null,
    "vat_number": "300041254700003",
    "address_ar": "P.O. Box : 52408 - Riyadh : 11563",
    "address_en": null
  },
  "customer": {
    "name_ar": null,
    "name_en": null,
    "address_ar": null,
    "address_en": null
  },
  "financials": {
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  },
  "metadata": {
    "purchase_order": null,
    "reference_number": null,
    "payment_terms": null,
    "notes": ""
  }
}
```

---------------------------------

Manual Evaluation

| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Extracted correctly |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ✅ | Correctly empty |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Extracted correctly |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---------------------------------


# Overall Statistics

Invoices Processed: 16

Successful OCR: 15 / 15

Valid JSON: 15 / 15

Average OCR Time: 11.41 s

Average LLM Time: 12.90 s

Average Total Time: 29.22 s


## Field Accuracy (Gemma4:E4B IDP)


| Field | Correct | Wrong | Accuracy |

| --- | --- | --- | --- |

| Document Number | 13 | 2 | 86.7% |

| VAT Number | 13 | 2 | 86.7% |

| Date | 14 | 1 | 93.3% |

| Currency | 13 | 2 | 86.7% |

| Vendor Arabic | 14 | 1 | 93.3% |

| Vendor English | 12 | 3 | 80.0% |

| Customer Arabic | 13 | 2 | 86.7% |

| Customer English | 14 | 1 | 93.3% |

| Address Arabic | 13 | 2 | 86.7% |

| Address English | 14 | 1 | 93.3% |

| Subtotal | 13 | 2 | 86.7% |

| Tax | 13 | 2 | 86.7% |

| Total | 12 | 3 | 80.0% |




# Model Performance Comparison


| Metric | Qwen2.5-3B | Gemma4:E4B (Baseline) | Gemma4:E4B (New IDP) | Winner |

| --- | --- | --- | --- | --- |

| Valid Json | 100.0% | 100.0% | 100.0% | Tie |

| Vendor Acc | 46.4% | 89.3% | 92.9% | Gemma (IDP) |

| Customer Acc | 50.0% | 89.3% | 96.4% | Gemma (IDP) |

| Arabic Acc | 50.0% | 90.5% | 95.2% | Gemma (IDP) |

| English Acc | 42.9% | 83.3% | 95.2% | Gemma (IDP) |

| Invoice Number | 50.0% | 64.3% | 92.9% | Gemma (IDP) |

| VAT Registration | 64.3% | 78.6% | 92.9% | Gemma (IDP) |

| Date | 64.3% | 85.7% | 100.0% | Gemma (IDP) |

| Totals & Math | 31.0% | 92.9% | 90.5% | Gemma (Base) |




# Final Recommendation


Based on the comprehensive IDP audit and evaluation, the newly redesigned **IDP Extraction Pipeline using Gemma4:E4B** should be adopted in production.


* **Performance Improvement**: The IDP pipeline achieves **92.9%** vendor accuracy, **96.4%** customer accuracy, and **90.5%** math accuracy.

* **Clean OCR Philosophy**: By stripping custom rule-based heuristics and header/footer splitting, the pipeline has been simplified down to scanner-like OCR combined with document understanding.
