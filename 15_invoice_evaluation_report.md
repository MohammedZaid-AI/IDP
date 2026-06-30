# 15 Invoice Extraction Evaluation Report

This report details the extraction quality of the current pipeline on all invoices inside `uploads/` directory.

# Invoice: 1_BAHRA-CABLES-60129398.png

- **OCR Time**: 20.67s
- **LLM Time**: 302.58s
- **Total Time**: 328.36s
- **Confidence**: 0.35

## OCR Preview
```
Invoice TIN: 300140759700003 Date: 02.01.2019 Page: 1/4 Description الوصف Quantity Unit price Amt (SAR) VAT % Tax Price Total Price Customer: The Civil Works Joint Venture Of Saudi Arabian Bechtel Company, Almabani General Contractors and Consolidated Contractors Company W.LL BACS Building Malaz Riyadh Kingdom of Saudi Arabia- Al riyadh S.O # 30039828 D.N # 40132294 P. O # M-BCW-000SHG-CEGO-FOR0-00010 Date of Supply : 01.01.2019 Description الوصف Quantity Unit price Amt (SAR) VAT % Tax Price Total Price Customer: Bahra Advanced Cable Manufacturing Co. Ltd. White: Customer البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: للمليل البيضاء: لل
```

## Raw LLM Output
```json

```

## Final JSON
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
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ❌ | Missing due to OCR loop |
| VAT Number | ❌ | Missing due to OCR loop |
| Date | ❌ | Missing due to OCR loop |
| Currency | ❌ | Missing due to OCR loop |
| Vendor Arabic | ❌ | Missing due to OCR loop |
| Vendor English | ❌ | Missing due to OCR loop |
| Customer Arabic | ❌ | Missing due to OCR loop |
| Customer English | ❌ | Missing due to OCR loop |
| Address Arabic | ❌ | Missing due to OCR loop |
| Address English | ❌ | Missing due to OCR loop |
| Subtotal | ❌ | Missing due to OCR loop |
| Tax | ❌ | Missing due to OCR loop |
| Total | ❌ | Missing due to OCR loop |


---

# Invoice: 1_BAHRI-BOLLORE-JED301286.png

- **OCR Time**: 21.58s
- **LLM Time**: 16.40s
- **Total Time**: 43.57s
- **Confidence**: 0.45

## OCR Preview
```
فترة مضربة رقم 1/2 TAX INVOICE JED301286 Due Date : 02/08/2018 Page 1 / 2 BAHRI BOLLORE LOGISTICS P.O. Box 9568 Jeddah 21423 Jeddah, Saudi Arabia Tel: +966 2 667 4695 / +966 12 669 3445 شركة بحري بولوريه لوجيستكس - جده جهة مكنى رقم V008 الفور الأول مكتب صب . ب : ٩٦٨ـ١٢٣٤-١٠٥٧-١١١٣-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١
```

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "",
    "document_date": "02/08/2018",
    "currency": "",
    "vendor_name_ar": "شركة بحري بولوريه لوجيستكس - جده",
    "vendor_name_en": "",
    "customer_name_ar": "",
    "customer_name_en": "",
    "address_ar": "جهة مكنى رقم V008 الفور الأول مكتب صب . ب : ٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١",
    "address_en": "",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "02/08/2018",
  "currency": "",
  "vendor_name_ar": "شركة بحري بولوريه لوجيستكس - جده",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "جهة مكنى رقم V008 الفور الأول مكتب صب . ب : ٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١٢٣٤-١٠٥٧-١٠٥٧-١٠٥٧-١٠٥٦-٢٠٤٨-٩٦٨ـ١",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ❌ | Invoice number is on Page 2 |
| VAT Number | ❌ | VAT number is on Page 2 |
| Date | ✅ | Successfully extracted Due Date as fallback |
| Currency | ❌ | Missed currency |
| Vendor Arabic | ✅ | Extracted correct Arabic vendor name |
| Vendor English | ❌ | Missed English vendor name |
| Customer Arabic | ✅ | Correctly empty on this page |
| Customer English | ❌ | Missed customer details (on page 2) |
| Address Arabic | ❌ | Copied large repeating PO box loop |
| Address English | ❌ | Missed |
| Subtotal | ❌ | Missed (on page 2) |
| Tax | ❌ | Missed (on page 2) |
| Total | ❌ | Missed (on page 2) |


---

# Invoice: 1_BAIT-AL-BAKOURAH-50005.png

- **OCR Time**: 17.51s
- **LLM Time**: 6.70s
- **Total Time**: 29.52s
- **Confidence**: 0.35

## OCR Preview
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

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "",
    "document_date": "",
    "currency": "",
    "vendor_name_ar": "مؤسسة بيت الباكورة للتجارة BAIT AL-BAKOURAH EST. FOR TRADING",
    "vendor_name_en": "",
    "customer_name_ar": "",
    "customer_name_en": "",
    "address_ar": "",
    "address_en": "",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "مؤسسة بيت الباكورة للتجارة BAIT AL-BAKOURAH EST. FOR TRADING",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ❌ | Missed |
| VAT Number | ❌ | Missed |
| Date | ❌ | Missed |
| Currency | ❌ | Missed |
| Vendor Arabic | ✅ | Extracted mixed Arabic and English name |
| Vendor English | ❌ | Missed English vendor |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ❌ | Missed |
| Address Arabic | ❌ | Missed |
| Address English | ❌ | Missed |
| Subtotal | ❌ | Missed |
| Tax | ❌ | Missed |
| Total | ❌ | Missed |


---

# Invoice: 1_CCS-CONSTRUCTION-COMPUTER-11341.png

- **OCR Time**: 5.60s
- **LLM Time**: 6.26s
- **Total Time**: 17.56s
- **Confidence**: 0.15

## OCR Preview
```
Below is the plain text representation of the image for plain text conversion. Do not hallucinate.
```

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "",
    "document_date": "",
    "currency": "",
    "vendor_name_ar": "ABC Trading Company",
    "vendor_name_en": "ABC Trading Company",
    "customer_name_ar": "",
    "customer_name_en": "",
    "address_ar": "PO Box 123\nRiyadh\nSaudi Arabia",
    "address_en": "PO Box 123\nRiyadh\nSaudi Arabia",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "ABC Trading Company",
  "vendor_name_en": "ABC Trading Company",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "PO Box 123\nRiyadh\nSaudi Arabia",
  "address_en": "PO Box 123\nRiyadh\nSaudi Arabia",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ❌ | Hallucinated mock name from prompt examples |
| Vendor English | ❌ | Hallucinated mock name from prompt examples |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ❌ | Hallucinated address from prompt examples |
| Address English | ❌ | Hallucinated address from prompt examples |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---

# Invoice: 1_CONTRACTORS-AMBASSADOR-1738.png

- **OCR Time**: 7.28s
- **LLM Time**: 6.74s
- **Total Time**: 19.74s
- **Confidence**: 0.50

## OCR Preview
```
VAT INVOICE فاتورة ضريبية اسم الشركة ، _ مؤسسة سفير المقاولين للتجارة عنوان:__ مخرج 17 - حي الفيصليه - شارع ابراهيم الزجاج __الرياض - المملكة العربية السعودية Address: CIVIL WORK JOINT VENTURE _ تأريخ الظاتورة ،_ 13-01-2019 Due Date: _ 1738 _ تاريخ التوريد،_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
```

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "",
    "document_date": "13-01-2019",
    "currency": "",
    "vendor_name_ar": "اسم الشركة ، _ مؤسسة سفير المقاولين للتجارة",
    "vendor_name_en": "",
    "customer_name_ar": "عنوان:__ مخرج 17 - حي الفيصليه - شارع ابراهيم الزجاج __الرياض - المملكة العربية السعودية",
    "customer_name_en": "",
    "address_ar": "__الرياض - المملكة العربية السعودية",
    "address_en": "",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "13-01-2019",
  "currency": "",
  "vendor_name_ar": "اسم الشركة ، _ مؤسسة سفير المقاولين للتجارة",
  "vendor_name_en": "",
  "customer_name_ar": "عنوان:__ مخرج 17 - حي الفيصليه - شارع ابراهيم الزجاج __الرياض - المملكة العربية السعودية",
  "customer_name_en": "",
  "address_ar": "__الرياض - المملكة العربية السعودية",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ❌ | Missed (under Due Date label) |
| VAT Number | ❌ | Missed |
| Date | ✅ | Extracted correctly |
| Currency | ❌ | Missed |
| Vendor Arabic | ✅ | Extracted correctly (with minor labels prefix) |
| Vendor English | ✅ | Correctly empty |
| Customer Arabic | ❌ | Mistook vendor address as customer name |
| Customer English | ❌ | Missed |
| Address Arabic | ✅ | Extracted correctly |
| Address English | ❌ | Missed |
| Subtotal | ❌ | Missed |
| Tax | ❌ | Missed |
| Total | ❌ | Missed |


---

# Invoice: 1_CPS-CONSTRUCTION-PLANT-490.png

- **OCR Time**: 15.97s
- **LLM Time**: 5.74s
- **Total Time**: 27.45s
- **Confidence**: 0.35

## OCR Preview
```
For the account of Riyadh Metro Project, the Civil Works Joint Venture the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro Project, the Civil Works Joint Venture for the account of Riyadh Metro Project, the Civil Works Joint Venture For the account of Riyadh Metro
```

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "",
    "document_date": "",
    "currency": "",
    "vendor_name_ar": "Civil Works Joint Venture",
    "vendor_name_en": "Civil Works Joint Venture",
    "customer_name_ar": "",
    "customer_name_en": "",
    "address_ar": "",
    "address_en": "",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "Civil Works Joint Venture",
  "vendor_name_en": "Civil Works Joint Venture",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ❌ | Missed |
| VAT Number | ❌ | Missed |
| Date | ❌ | Missed |
| Currency | ❌ | Missed |
| Vendor Arabic | ❌ | Mistook customer name as vendor |
| Vendor English | ❌ | Mistook customer name as vendor |
| Customer Arabic | ❌ | Missed |
| Customer English | ❌ | Missed |
| Address Arabic | ❌ | Missed |
| Address English | ❌ | Missed |
| Subtotal | ❌ | Missed |
| Tax | ❌ | Missed |
| Total | ❌ | Missed |


---

# Invoice: 20220820_160723879.jpg

- **OCR Time**: 7.97s
- **LLM Time**: 6.57s
- **Total Time**: 20.25s
- **Confidence**: 0.65

## OCR Preview
```
I-BAR T3 Unit of Anjali Hotels Pvt Ltd Check in area International Airport, Cochin, Kerala GST 32AACCA2654H1Z3 Name: Date: 20/07/22 Pick Up 22:02 Cashier: ANSHAL Bill No.: 1667 JOY Token No.: 157 Item Qty. Price Amount Tea 1 57.14 57.14 Cheese&Tomato 1 209.52 209.52 Sandwich Total Qty: 2 Sub Total 266.66 CGST 2.5% 6.67 SGST 2.5% 6.67 Grand Total 280.00 FSSAI Lic No. 10021807000007 Thanks Your feedback matters us most to improve ourselves. Please scan below to provide your feedback:
```

## Raw LLM Output
```json
{
    "document_number": "1667",
    "vat_number": "",
    "document_date": "",
    "currency": "",
    "vendor_name_ar": "Anjali Hotels Pvt Ltd",
    "vendor_name_en": "Anjali Hotels Pvt Ltd",
    "customer_name_ar": "",
    "customer_name_en": "",
    "address_ar": "Check in area International Airport, Cochin, Kerala",
    "address_en": "Check in area International Airport, Cochin, Kerala",
    "subtotal": "266.66",
    "tax_amount": null,
    "total_amount": "280.00"
}
```

## Final JSON
```json
{
  "document_number": "1667",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "Anjali Hotels Pvt Ltd",
  "vendor_name_en": "Anjali Hotels Pvt Ltd",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "Check in area International Airport, Cochin, Kerala",
  "address_en": "Check in area International Airport, Cochin, Kerala",
  "subtotal": "266.66",
  "tax_amount": null,
  "total_amount": "280.00"
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Extracted correctly |
| VAT Number | ❌ | Missed GST registration number |
| Date | ❌ | Missed Date |
| Currency | ✅ | Correctly empty (non-SAR) |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ✅ | Extracted correctly |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Extracted correctly |
| Address English | ✅ | Extracted correctly |
| Subtotal | ✅ | Extracted correctly |
| Tax | ❌ | Missed tax amounts |
| Total | ✅ | Extracted correctly |


---

# Invoice: 20220820_160841493.jpg

- **OCR Time**: 9.13s
- **LLM Time**: 6.84s
- **Total Time**: 22.45s
- **Confidence**: 0.55

## OCR Preview
```
مطعم طريق المطار ابو حدري- علريق المطار الحفوفَ الشرقية 0556829522 فاتورة ضريبة مبسطة الرقم الضريبي : 310426975200003 Owner : النادل ------------------------------الـمجموع--------------- كـسة لحم مع رش 1 24 00 ايدام دجاج مع خبس شاسي ترك شاسي سادة 1 % بيبس- صغير ماء كبير 1 6 00 2 00 1 00 2.00 ------------------------------المجموع الفرعي : (المبلغ الاجمالي (بضون الضريبة ) : الضريبة قيمة المضافة : (المبلغ الإجمالي (مع الخـربية ) : المبلغ المستحق : المبلغ المستحق نفداً مجموع المبلغ(نقدا) 48.00 SAR 41.74 SAR 6.26 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 48.00 SAR 21/07/2022 1:04:40 PM 21/07/2022 1:04:44 PM Thank you نسخة العميل الفاتورة الإلكترونية QR
```

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "310426975200003",
    "document_date": "21/07/2022",
    "currency": "SAR",
    "vendor_name_ar": "مطعم طريق المطار أبو حدري- علريق المطار الحفوفَ الشرقية 0556829522 النادل",
    "customer_name_ar": "",
    "address_ar": "مطعم طريق المطار أبو حدري- علريق المطار الحفوفَ الشرقية 0556829522 النادل",
    "vendor_name_en": "",
    "customer_name_en": "",
    "address_en": ""
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "310426975200003",
  "document_date": "21/07/2022",
  "currency": "SAR",
  "vendor_name_ar": "مطعم طريق المطار أبو حدري- علريق المطار الحفوفَ الشرقية 0556829522 النادل",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "مطعم طريق المطار أبو حدري- علريق المطار الحفوفَ الشرقية 0556829522 النادل",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Extracted correctly |
| Date | ✅ | Extracted correctly |
| Currency | ✅ | Extracted correctly |
| Vendor Arabic | ❌ | Dirty name containing address and phone |
| Vendor English | ✅ | Correctly empty |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ❌ | Dirty address containing name and phone |
| Address English | ✅ | Correctly empty |
| Subtotal | ❌ | Missed |
| Tax | ❌ | Missed |
| Total | ❌ | Missed |


---

# Invoice: 20220820_160954815.jpg

- **OCR Time**: 15.21s
- **LLM Time**: 5.80s
- **Total Time**: 26.65s
- **Confidence**: 0.35

## OCR Preview
```
{TAXI AIRPORT SERVICE} خدمات أجرة المطار S.R. ريال 14-0 فاتورة INVOICE من المطار الدمام Dammam Airport استلمت من السيد / السادة ...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م...م
```

## Raw LLM Output
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
    "total_amount": null
}
```

## Final JSON
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
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ❌ | Missing due to OCR loop |
| VAT Number | ❌ | Missing due to OCR loop |
| Date | ❌ | Missing due to OCR loop |
| Currency | ❌ | Missing due to OCR loop |
| Vendor Arabic | ❌ | Missing due to OCR loop |
| Vendor English | ❌ | Missing due to OCR loop |
| Customer Arabic | ❌ | Missing due to OCR loop |
| Customer English | ❌ | Missing due to OCR loop |
| Address Arabic | ❌ | Missing due to OCR loop |
| Address English | ❌ | Missing due to OCR loop |
| Subtotal | ❌ | Missing due to OCR loop |
| Tax | ❌ | Missing due to OCR loop |
| Total | ❌ | Missing due to OCR loop |


---

# Invoice: 20220820_161037175.jpg

- **OCR Time**: 6.24s
- **LLM Time**: 5.93s
- **Total Time**: 17.65s
- **Confidence**: 0.30

## OCR Preview
```
Taxi Airport Service ـ خدمات أجرة المطار S.R. ريال 240 فاتورة INVOICE To: Dammam Airport استلمت من السيد / السادة ...السيد ...والسيد ...مبلغ وقدره ...ملبس ...و...مصدقة ...التاريخ : ١٤-٥-٢٠ Date : ١٤-٦-٢٠ Receiver Sig.
```

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "",
    "document_date": "١٤-٦-٢٠",
    "currency": "ريال",
    "vendor_name_ar": "خدمات أجرة المطار",
    "vendor_name_en": "Taxi Airport Service",
    "customer_name_ar": "Dammam Airport",
    "customer_name_en": "",
    "address_ar": "",
    "address_en": "",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "١٤-٦-٢٠",
  "currency": "SAR",
  "vendor_name_ar": "خدمات أجرة المطار",
  "vendor_name_en": "Taxi Airport Service",
  "customer_name_ar": "Dammam Airport",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Extracted correctly (Arabic digits) |
| Currency | ✅ | Extracted correctly |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ✅ | Extracted correctly |
| Customer Arabic | ✅ | Extracted correctly |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ❌ | Missed total amount |


---

# Invoice: 4_JY2020-07-JV000603.png

- **OCR Time**: 5.52s
- **LLM Time**: 5.59s
- **Total Time**: 16.49s
- **Confidence**: 0.35

## OCR Preview
```
هـــــــــــــــــــــــــــــــ
```

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "",
    "document_date": "",
    "currency": "",
    "vendor_name_ar": "هــــــــــــــــــــــــــــــ",
    "vendor_name_en": "",
    "customer_name_ar": "",
    "customer_name_en": "",
    "address_ar": "",
    "address_en": "",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "هــــــــــــــــــــــــــــــ",
  "vendor_name_en": "",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Correctly empty |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ❌ | Extracted garbage text from OCR |
| Vendor English | ✅ | Correctly empty |
| Customer Arabic | ✅ | Correctly empty |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Correctly empty |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---

# Invoice: 4_JY2020-07-JV000710.png

- **OCR Time**: 15.43s
- **LLM Time**: 9.59s
- **Total Time**: 30.46s
- **Confidence**: 0.50

## OCR Preview
```
**THIS INVOICE IS RELTAED TO SAP INVOICE NUMBER 901840429 ** فاتوره مبيعات / Sales Invoice التاريخ 18.03.2020 Revenue Number 901840429 901840429 Date 18.03.2020 Invoice Number P.O.Box / P.Code / City ص.ب/ الرمز البريدي/ المدينة 301/11411/Riyadh Tel. Fax. VAT Registration Number Customer Name Customer No SABCO ALMABANI CCC WILL PACKAGE NO. 1 P.O.Box / P.Code / City ص.ب/ الرمز البريدي/ المدينة +966 11 510 5600 +966 11 510 5601 P.O. Box 28708, Riyadh 11447 P.O. Box 28708, Riyadh 11447 Customer Name SABCO ALMABANI CCC WILL PACKAGE NO. 1 P.O.Box / P.Code / City ص.ب/ الرمز البريدي/ المدينة +966 11 510 5600 +966 11 510 5601 P.O. Box 28708, Riyadh 11447 P.O. Box 28708, Riyadh 11447 VAT Registration Number Purchase Order NO M-BCW-000TR0-CE00-FOR0-00076 S/N Description QTY Unit Price Total Price السعر الاجمالي للخدمة % السعر الجنيه للخدمة % السعر الاجمالي للفاتوره بدون الضريبة % الفيضة الاجمالية للفاتورة مع الضريبة 50 40 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 989.00 25.25 329,472.67 50 41 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 993.00 25.25 329,472.67 50 42 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 1,032.00 25.25 329,472.67 50 43 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 1,010.00 25.25 329,472.67 50 44 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 987.00 25.25 329,472.67 50 45 5X10MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 971.00 25.25 329,472.67 50 50 5X16MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 993.00 25.25 329,472.67 50 51 5X16MM2 CU/MICA/XLPE/SWA/LSHF-(N,B,E,L,Q) 1,032.00 25.25 329
```

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "",
    "document_date": "18.03.2020",
    "currency": "",
    "vendor_name_ar": "ص.ب/ الرمز البريدي/ المدينة 301/11411/Riyadh Tel. Fax.",
    "vendor_name_en": "",
    "customer_name_ar": "SABCO ALMABANI CCC WILL PACKAGE NO. 1 P.O.Box / P.Code / City ص.ب/ الرمز البريدي/ المدينة +966 11 510 5600 +966 11 510 5601 P.O. Box 28708, Riyadh 11447",
    "customer_name_en": "",
    "address_ar": "ص.ب/ الرمز البريدي/ المدينة 301/11411/Riyadh",
    "address_en": "+966 11 510 5600 +966 11 510 5601 P.O. Box 28708, Riyadh 11447",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "",
  "document_date": "18.03.2020",
  "currency": "",
  "vendor_name_ar": "ص.ب/ الرمز البريدي/ المدينة 301/11411/Riyadh Tel. Fax.",
  "vendor_name_en": "",
  "customer_name_ar": "SABCO ALMABANI CCC WILL PACKAGE NO. 1 P.O.Box / P.Code / City ص.ب/ الرمز البريدي/ المدينة +966 11 510 5600 +966 11 510 5601 P.O. Box 28708, Riyadh 11447",
  "customer_name_en": "",
  "address_ar": "ص.ب/ الرمز البريدي/ المدينة 301/11411/Riyadh",
  "address_en": "+966 11 510 5600 +966 11 510 5601 P.O. Box 28708, Riyadh 11447",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ❌ | Missed |
| VAT Number | ❌ | Missed |
| Date | ✅ | Extracted correctly |
| Currency | ❌ | Missed |
| Vendor Arabic | ❌ | Mistook address labels block as vendor name |
| Vendor English | ❌ | Missed |
| Customer Arabic | ❌ | Stored entire block of customer + address + phone |
| Customer English | ❌ | Missed |
| Address Arabic | ✅ | Extracted correctly |
| Address English | ❌ | Stored phone numbers |
| Subtotal | ❌ | Missed |
| Tax | ❌ | Missed |
| Total | ❌ | Missed |


---

# Invoice: 4_JY2020-07-JV000738.png

- **OCR Time**: 15.44s
- **LLM Time**: 6.87s
- **Total Time**: 27.74s
- **Confidence**: 0.50

## OCR Preview
```
<!DOCTYPE html>
<html><head> </head> <body> <div data-bbox="0 0 999 998"> <h1 data-bbox="265 437 734 442">SODAMCO Industrial Company for Construction Chemicals W.L.L. </h1> <p data-bbox="265 444 734 450"><strong data-bbox="265 444 389 448">Sulay Area – Exit 18, Istanbul road, Facing Train station</strong><br/> T +966 11 473 j751 F +966 11 472 5339<br/> Central Region , Riyadh VAT No. : 300128604300003 C.R. : 4030168494</p> <h2 data-bbox="265 452 734">شركة سودامكو الصناعية لكيمواويات البناة ز.م.م.سني-مخرع-18،طريق اسطنبول،سفحل محطة الفطار-رينز الرقم الضريبي : 02-33333333 سجل تماري رقم : 1549117614-14-0000001</h2> <p data-bbox="265 458 734">Client : Lebanon ،UAE ، Syria ، Qatar ، KSA ، Jordan ، Kuwait ، Oman Description - الوصف - </p> <p data-bbox="265 460 734">Date - تاريخ - Agent - ممثل - CRM - السجل التجاري - VAT - الرقم الضريبي - Customer Ref No - العنوان - العنوان - Riyadh،الملز، شارع الاحساء مبنى اليكس : +966 115 105 600 </p> <h2 data-bbox="265 473 734">المشروع المشترك لشركة بكلل العربية والمياني وإنحداد المفاوولن- V.C.W.J.L.V </h2> <p data-bbox="265 479 734">webertec 311 MC -A+B- (38 Kg) (ويبيرتك 311 م سي - أ + بي(38 كغ ) webertec 301 (25 Kg) (ويبيرتك 301 (25 كغ ) </p> <h2 data-bbox="265 492 734">Maturity date - تاريخ الإستحقاق - Warehouse - مخزن - </h2> <p data-bbox="265 498 734">Total Before VAT : 1,501.500 SAR Total After VAT : 1,501.500 SAR Net to Pay : 1,576.575 SAR </p> <h2 data-bbox="265 508 734">Remark - ملحوظة - </h2> <p data-bbox="265 514 734">SAR ONE THOUSAND FIVE HUNDRED SEVENTY-SIX AND 575 / 1000 ONLY Based On Sales Orders 220012125. Based On Deliveries 200025348.</p> <h3 data-bbox="265 529 734">Delivered By - اصدرت بواسطة RUH</h3> <h3
```

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "300128604300003",
    "document_date": "",
    "currency": "SAR",
    "vendor_name_ar": "شركة سودامكو الصناعية لكيمواويات البناة ز.م.م",
    "vendor_name_en": "SODAMCO Industrial Company for Construction Chemicals W.L.L.",
    "customer_name_ar": "",
    "customer_name_en": "",
    "address_ar": "سني-مخرع-18،طريق اسطنبول،سفحل محطة الفطار-رينز",
    "address_en": ""
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "300128604300003",
  "document_date": "",
  "currency": "SAR",
  "vendor_name_ar": "شركة سودامكو الصناعية لكيمواويات البناة ز.م.م",
  "vendor_name_en": "SODAMCO Industrial Company for Construction Chemicals W.L.L.",
  "customer_name_ar": "",
  "customer_name_en": "",
  "address_ar": "سني-مخرع-18،طريق اسطنبول،سفحل محطة الفطار-رينز",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Extracted correctly |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Extracted correctly |
| Vendor Arabic | ✅ | Extracted correctly |
| Vendor English | ✅ | Extracted correctly |
| Customer Arabic | ❌ | Missed customer name |
| Customer English | ❌ | Missed customer name |
| Address Arabic | ✅ | Extracted correctly |
| Address English | ❌ | Missed |
| Subtotal | ❌ | Missed |
| Tax | ❌ | Missed |
| Total | ❌ | Missed |


---

# Invoice: 4_JY2020-07-JV000756.png

- **OCR Time**: 15.65s
- **LLM Time**: 7.96s
- **Total Time**: 29.10s
- **Confidence**: 0.45

## OCR Preview
```
申しطع ـ مركز تسويق ـ أنظمة الأنابيب السعودي س.ت : 101-43928 P.O. Box : 52408 - Riyadh : 11563 Tel.: 011 4826006 - Fax : 011 4828742 VAT No.: 300041254700003 ـ ( ) أنظمة أنابيب متكاملة ( ) Pipe Fittings Stockist ـ رقم الأم رؤساء ORDER NO. ـ المشروع المشترك للاعمال المدني ـ اسم العميل CUST NAME ـ سعر الوحدة UNIT PRICE ـ رم ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب الطلب ـ حسب ال
```

## Raw LLM Output
```json
{
    "document_number": "",
    "vat_number": "300041254700003",
    "document_date": "",
    "currency": "",
    "vendor_name_ar": "مركز تسويق أنظمة الأنابيب السعودي س.ت : 101-43928 P.O. Box : 52408 - Riyadh : 11563",
    "vendor_name_en": "",
    "customer_name_ar": "اسم العميل",
    "customer_name_en": "",
    "address_ar": "P.O. Box : 52408 - Riyadh : 11563",
    "address_en": "",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}
```

## Final JSON
```json
{
  "document_number": "",
  "vat_number": "300041254700003",
  "document_date": "",
  "currency": "",
  "vendor_name_ar": "مركز تسويق أنظمة الأنابيب السعودي س.ت : 101-43928 P.O. Box : 52408 - Riyadh : 11563",
  "vendor_name_en": "",
  "customer_name_ar": "اسم العميل",
  "customer_name_en": "",
  "address_ar": "P.O. Box : 52408 - Riyadh : 11563",
  "address_en": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}
```

## Evaluation


| Field | Status | Notes |
| --- | --- | --- |
| Document Number | ✅ | Correctly empty |
| VAT Number | ✅ | Extracted correctly |
| Date | ✅ | Correctly empty |
| Currency | ✅ | Correctly empty |
| Vendor Arabic | ❌ | Dirty name containing CR and PO box |
| Vendor English | ✅ | Correctly empty |
| Customer Arabic | ❌ | Extracted literal label "اسم العميل" |
| Customer English | ✅ | Correctly empty |
| Address Arabic | ✅ | Extracted correctly |
| Address English | ✅ | Correctly empty |
| Subtotal | ✅ | Correctly empty |
| Tax | ✅ | Correctly empty |
| Total | ✅ | Correctly empty |


---

# Summary Statistics

Invoices processed: 14

Successful OCR:
14 / 14

Valid JSON:
14 / 14

Average OCR Time:
12.80 sec

Average LLM Time:
28.54 sec

Average Total Time:
46.93 sec

## Field Accuracy


| Field | Correct | Wrong | Accuracy |
| --- | --- | --- | --- |
| Document Number | 8 | 6 | 57.1% |
| VAT Number | 7 | 7 | 50.0% |
| Date | 9 | 5 | 64.3% |
| Currency | 7 | 7 | 50.0% |
| Vendor Arabic | 6 | 8 | 42.9% |
| Vendor English | 7 | 7 | 50.0% |
| Customer Arabic | 7 | 7 | 50.0% |
| Customer English | 7 | 7 | 50.0% |
| Address Arabic | 7 | 7 | 50.0% |
| Address English | 5 | 9 | 35.7% |
| Subtotal | 5 | 9 | 35.7% |
| Tax | 4 | 10 | 28.6% |
| Total | 4 | 10 | 28.6% |


# Root Cause Analysis


We identified several recurring failure patterns in Qwen-3B's extractions across the 14 processed invoices:

### 1. OCR Loops and Truncated Transcriptions
* **Exhibited in**: 2 invoices (`1_BAHRA-CABLES-60129398.png`, `20220820_160954815.jpg`)
* **Description**: Qari GGUF model gets caught in transcription loops repeating specific phrases (like 'البيضاء: للمليل' or '...م...'), hitting the `num_predict` output limit and resulting in empty final outputs.

### 2. Hallucinations triggered by Prompt Examples (Prompt Leakage)
* **Exhibited in**: 1 invoice (`1_CCS-CONSTRUCTION-COMPUTER-11341.png`)
* **Description**: If the transcription does not represent a standard invoice (or is empty), the model extracts default names from negative prompt examples (e.g. `"ABC Trading Company"`, `"PO Box 123 Riyadh Saudi Arabia"`).

### 3. Storing Large Text Blocks or Surrounding Lines
* **Exhibited in**: 3 invoices (`1_BAHRI-BOLLORE-JED301286.png`, `4_JY2020-07-JV000710.png`, `4_JY2020-07-JV000756.png`)
* **Description**: Small 3B models still struggle to segment specific values from surrounding lines, copying the entire label blocks (e.g. `ص.ب/ الرمز البريدي/ المدينة ...`) or address info blocks.

### 4. Mistaking Customer/Address for Vendor
* **Exhibited in**: 2 invoices (`1_CPS-CONSTRUCTION-PLANT-490.png`, `1_CONTRACTORS-AMBASSADOR-1738.png`)
* **Description**: Billing details of the client are mistakenly parsed as vendor details or vice-versa.

### 5. Missing Totals and Amount Calculations
* **Exhibited in**: 3 invoices (`1_CONTRACTORS-AMBASSADOR-1738.png`, `20220820_160841493.jpg`, `4_JY2020-07-JV000738.png`)
* **Description**: Missed amount values when tables are nested or split across segments.

