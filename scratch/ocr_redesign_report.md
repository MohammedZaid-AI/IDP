# Redesigned OCR Pipeline Evaluation Report

This report evaluates the performance of the redesigned region-based OCR preprocessing pipeline on the invoice dataset in `uploads/`.

## OCR Redesign Results Table

| Invoice Filename | Original OCR Chars | Compressed OCR Chars | Reduction % | Invoice # | Vendor | Customer | Totals | Ends in done_reason="length"? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1_BAHRA-CABLES-60129398.png | 1181 | 1301 | -10.16% | No | Yes | Yes | Yes | No |
| 1_BAHRA-CABLES-60129398_9f2a8039864b.png | 1181 | 1301 | -10.16% | No | Yes | Yes | Yes | No |
| 1_BAHRA-CABLES-60129398_aa1188d31276.png | 1314 | 1434 | -9.13% | No | Yes | Yes | No | Yes |
| 1_BAHRI-BOLLORE-JED301286.png | 2282 | 2402 | -5.26% | Yes | Yes | Yes | Yes | Yes |
| 1_BAIT-AL-BAKOURAH-50005.png | 816 | 903 | -10.66% | Yes | Yes | Yes | Yes | No |
| 1_BAIT-AL-BAKOURAH-50005_f604debc50ee.png | 822 | 909 | -10.58% | Yes | Yes | Yes | Yes | No |
| 1_CCS-CONSTRUCTION-COMPUTER-11341.png | 1879 | 1851 | 1.49% | Yes | Yes | Yes | Yes | No |
| 1_CONTRACTORS-AMBASSADOR-1738.png | 1358 | 1478 | -8.84% | Yes | Yes | Yes | Yes | No |
| 1_CPS-CONSTRUCTION-PLANT-490.png | 1538 | 1658 | -7.80% | Yes | Yes | Yes | Yes | No |
| 20220820_160723879.jpg | 567 | 688 | -21.34% | Yes | Yes | No | Yes | No |
| 20220820_160841493.jpg | 551 | 638 | -15.79% | No | Yes | No | Yes | No |
| 20220820_160954815.jpg | 848 | 935 | -10.26% | No | Yes | No | Yes | Yes |
| 20220820_161037175.jpg | 1305 | 1392 | -6.67% | No | Yes | Yes | Yes | Yes |
| 4_JY2020-07-JV000603.png | 1248 | 1368 | -9.62% | No | Yes | No | No | Yes |
| 4_JY2020-07-JV000603_033bb84135e8.png | 1454 | 1574 | -8.25% | No | Yes | No | Yes | Yes |
| 4_JY2020-07-JV000710.png | 1196 | 1283 | -7.27% | Yes | Yes | Yes | Yes | Yes |
| 4_JY2020-07-JV000738.png | 1235 | 1286 | -4.13% | No | Yes | No | Yes | Yes |
| 4_JY2020-07-JV000738_1088f325b878.png | 1235 | 1286 | -4.13% | No | Yes | No | Yes | Yes |
| 4_JY2020-07-JV000756.png | 1010 | 1130 | -11.88% | Yes | Yes | No | Yes | No |

**Averages / Totals:**
- **Total Original Characters:** 23020
- **Total Compressed Characters:** 24817
- **Average Size Reduction:** -8.97%