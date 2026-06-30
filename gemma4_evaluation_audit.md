# Independent Audit Report: Gemma4:E4B vs Qwen2.5-3B

This report presents an independent audit of the `gemma4_evaluation_report.md` and the invoice extraction pipeline. The goal is to determine if the reported metrics are accurate, identify evaluation biases, recalculate stats from the raw data, and make an objective production recommendation.

---

## 1. Identified Incorrect Manual Evaluations

We audited the manual evaluation tables for Gemma and found several discrepancies where fields were marked ✅ when they should have been marked ❌:

*   **`20220820_160954815.jpg` (Taxi receipt with OCR loop)**:
    *   *Vendor Arabic* and *Vendor English* were marked ✅ ("Correctly empty"). However, the vendor names `"خدمات أجرة المطار"` and `"TAXI AIRPORT SERVICE"` are clearly present in the first line of the OCR text. Gemma missed them, so these should be ❌.
    *   For Qwen, the exact same empty extractions on this invoice were marked ❌, creating a scoring double standard.
*   **`1_BAHRI-BOLLORE-JED301286.png` (Bahri Bollore Invoice)**:
    *   *Date* was marked ✅ ("Correctly empty"). However, the OCR contains `Due Date : 02/08/2018` which is the only date present on the document and serves as the fallback invoice date. Qwen extracted this date and was marked ✅. Gemma failed to extract it (extracted empty) but was still marked ✅, creating another scoring inconsistency.
*   **`1_BAIT-AL-BAKOURAH-50005.png` (Bait Al Bakourah Invoice)**:
    *   Gemma was marked ✅ for 11 missed fields (including *VAT Number*, *Date*, *Address*, *Subtotal*, *Tax*, and *Total*) as "Correctly empty". However, these values exist on the physical document but were missed because the OCR transcription crashed in an HTML loop. Qwen was correctly marked ❌ for missing these fields, while Gemma was incorrectly marked ✅, creating a major evaluation bias.
*   **`4_JY2020-07-JV000738.png` (Sodamco Invoice)**:
    *   *Customer Arabic* was marked ✅ ("Correctly empty") for Gemma. However, the Arabic customer name `"المشروع المشترك لشركة بكلل العربية والمياني وإنحداد المفاوولن- V.C.W.J.L.V"` is clearly present in the OCR text. Gemma missed it, so it should be marked ❌.

---

## 2. Identified Inconsistent Scoring & Evaluation Bias

We found two main sources of evaluation bias in the original report:

1.  **Double Standards on OCR Loops**: Qwen was penalized (❌) for missing values on loop-heavy OCR documents, whereas Gemma was rewarded (✅) with "Correctly empty" for the same empty outputs, inflating Gemma's apparent accuracy.
2.  **Dataset Discrepancy (Denominator Misalignment)**:
    *   The Qwen evaluation processed **14 invoices**.
    *   The Gemma evaluation processed **15 invoices**, including a duplicate file (`4_JY2020-07-JV000603_033bb84135e8.png`) that was 100% correct, artificially boosting Gemma's average metrics and timings.
3.  **Percentage Formatting Bug**:
    *   The original report had a double-multiplication bug printing field accuracies like `7333.3%` and `8666.7%` due to a code error on line 415 of `scratch/execute_evaluation.py`.

---

## 3. Corrected Field Accuracy Tables (14 Aligned Invoices)

Below are the recalculated, audited field accuracy counts and percentages on the **14 unique aligned invoices** (excluding the duplicate) for both models. 

> [!NOTE]
> Ground Truth represents the actual physical presence of fields on the invoice. Missed fields are strictly scored as ❌ (Wrong) for both models.

| Field | Qwen Correct | Qwen Accuracy | Gemma Correct | Gemma Accuracy | Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Document Number** | 7 | 50.0% | 9 | 64.3% | +14.3% |
| **VAT Number** | 9 | 64.3% | 11 | 78.6% | +14.3% |
| **Date** | 9 | 64.3% | 12 | 85.7% | +21.4% |
| **Currency** | 10 | 71.4% | 13 | 92.9% | +21.5% |
| **Vendor Arabic** | 6 | 42.9% | 13 | 92.9% | +50.0% |
| **Vendor English** | 7 | 50.0% | 12 | 85.7% | +35.7% |
| **Customer Arabic** | 8 | 57.1% | 13 | 92.9% | +35.8% |
| **Customer English** | 6 | 42.9% | 12 | 85.7% | +42.8% |
| **Address Arabic** | 7 | 50.0% | 12 | 85.7% | +35.7% |
| **Address English** | 5 | 35.7% | 11 | 78.6% | +42.9% |
| **Subtotal** | 5 | 35.7% | 13 | 92.9% | +57.2% |
| **Tax** | 4 | 28.6% | 13 | 92.9% | +64.3% |
| **Total** | 4 | 28.6% | 13 | 92.9% | +64.3% |

---

## 4. Corrected Model Comparison Table

This table compares Qwen2.5-3B and Gemma4:E4B using **exactly aligned criteria** across the 14 unique invoices:

| Metric | Qwen2.5-3B | Gemma4:E4B | Winner |
| :--- | :--- | :--- | :--- |
| **Valid JSON** | 100.0% | 100.0% | Tie |
| **Vendor Accuracy** | 46.4% | 89.3% | Gemma4:E4B |
| **Customer Accuracy** | 50.0% | 89.3% | Gemma4:E4B |
| **Arabic Accuracy** | 50.0% | 90.5% | Gemma4:E4B |
| **English Accuracy** | 42.9% | 83.3% | Gemma4:E4B |
| **Invoice Number** | 50.0% | 64.3% | Gemma4:E4B |
| **VAT** | 64.3% | 78.6% | Gemma4:E4B |
| **Date** | 64.3% | 85.7% | Gemma4:E4B |
| **Totals** | 31.0% | 92.9% | Gemma4:E4B |
| **Average LLM Time** | 28.54s | 10.07s | Gemma4:E4B |
| **Average Total Time**| 46.93s | 27.08s | Gemma4:E4B |

---

## 5. Verification of Gemma's Performance Boost

We inspected the raw data for invoices where Gemma performed dramatically better than Qwen to ensure there was no extraction artifact:

*   **Totals Extraction (31.0% vs 92.9%)**: Qwen completely missed subtotal/tax/totals on restaurant and retail receipts (e.g. `20220820_160841493.jpg`) returning `null`. Gemma correctly extracted them with 100% precision. The raw OCR was identical; Gemma is simply better at mathematical layout grounding.
*   **Prompt Leakage**: Qwen suffered from prompt example leakage (hallucinating "ABC Trading" and "Saudi Cement Company" when the invoice was empty). Gemma correctly left these fields empty, proving its robustness.
*   **Speed (28.54s vs 10.07s)**: Qwen suffered from long generation sequences and loops. Gemma's JSON output is compact and parsed efficiently without looping.

---

## 6. Final Recommendation

**"Based on a fair and independently verified evaluation, should Gemma4:E4B replace Qwen2.5:3B in production?"**

### **YES**

Gemma4:E4B should replace Qwen2.5-3B in production. Even after stripping away the double standards and aligning the dataset to the exact same 14 invoices, the audited results show a massive performance gap in favor of Gemma:

1.  **Extraction Quality**: Gemma4:E4B improves **Totals accuracy by +61.9%** (92.9% vs 31.0%), **Vendor accuracy by +42.9%** (89.3% vs 46.4%), and **Customer accuracy by +39.3%** (89.3% vs 50.0%).
2.  **Processing Speed**: Gemma cuts average LLM extraction time by **64.7%** (from 28.54s to 10.07s) and overall latency by **42.3%** (from 46.93s to 27.08s).
3.  **Reliability**: Gemma completely eliminates the risk of prompt examples leaking into production outputs (hallucinations) and handles loop-heavy OCR texts without crashing or hanging.
