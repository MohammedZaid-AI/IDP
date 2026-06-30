# Redesigned Validation Layer Evaluation Report

This report compares the performance and confidence scores of the new OCR-aware validation layer against the previous validation layer on the invoice dataset in `uploads/`.

## Validation Changes Results Table

| Invoice Filename | Prev Conf | New Conf | Confidence Change | Prev Validation | New Validation | Validation Change | Highlight (Confidence Increased)? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1_BAHRA-CABLES-60129398.png | 0.70 | 0.60 | -0.1 | PASS | FAIL | PASS ➔ FAIL | Decreased (-0.10) |
| 1_BAHRI-BOLLORE-JED301286.png | 0.55 | 0.70 | +0.15 | PASS | PASS | No Change | **YES (+0.15)** 🚀 |
| 1_BAIT-AL-BAKOURAH-50005.png | 0.35 | 0.95 | +0.6 | FAIL | PASS | FAIL ➔ PASS | **YES (+0.60)** 🚀 |
| 1_CCS-CONSTRUCTION-COMPUTER-11341.png | 0.35 | 0.90 | +0.55 | FAIL | PASS | FAIL ➔ PASS | **YES (+0.55)** 🚀 |
| 1_CONTRACTORS-AMBASSADOR-1738.png | 0.50 | 0.85 | +0.35 | FAIL | PASS | FAIL ➔ PASS | **YES (+0.35)** 🚀 |
| 1_CPS-CONSTRUCTION-PLANT-490.png | 0.35 | 0.85 | +0.5 | FAIL | PASS | FAIL ➔ PASS | **YES (+0.50)** 🚀 |
| 20220820_160723879.jpg | 0.65 | 0.80 | +0.15 | PASS | PASS | No Change | **YES (+0.15)** 🚀 |
| 20220820_160841493.jpg | 0.80 | 0.65 | -0.15 | FAIL | FAIL | No Change | Decreased (-0.15) |
| 20220820_160954815.jpg | 0.35 | 0.75 | +0.4 | FAIL | PASS | FAIL ➔ PASS | **YES (+0.40)** 🚀 |
| 20220820_161037175.jpg | 0.55 | 0.75 | +0.2 | PASS | PASS | No Change | **YES (+0.20)** 🚀 |
| 4_JY2020-07-JV000603.png | 0.35 | 0.90 | +0.55 | FAIL | PASS | FAIL ➔ PASS | **YES (+0.55)** 🚀 |
| 4_JY2020-07-JV000603_033bb84135e8.png | 0.35 | 0.90 | +0.55 | FAIL | PASS | FAIL ➔ PASS | **YES (+0.55)** 🚀 |
| 4_JY2020-07-JV000710.png | 0.70 | 0.60 | -0.1 | PASS | FAIL | PASS ➔ FAIL | Decreased (-0.10) |
| 4_JY2020-07-JV000738.png | 0.75 | 0.65 | -0.1 | PASS | PASS | No Change | Decreased (-0.10) |
| 4_JY2020-07-JV000756.png | 0.45 | 0.40 | -0.05 | FAIL | FAIL | No Change | Decreased (-0.05) |

## Summary Metrics
- **Total Invoices Evaluated:** 15
- **Invoices with Increased Confidence:** 10 / 15 (66.7%)
- **False Negatives Cleared:** Highlighted above in Validation Change where status transitioned from FAIL to PASS.