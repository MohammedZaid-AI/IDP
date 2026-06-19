import asyncio
import json
from dotenv import load_dotenv
load_dotenv()
from services.multi_model import FieldExtractionService

def main():
    service = FieldExtractionService()
    
    ocr_text_bahra = """1. Document Number: 60129398
2. Document Date: 02.01.2019
3. Vendor Name: Bahra Cables
4. Customer Name: The Civil Works Joint Venture Of Saudi Arabian Bechtel Company, Almabani General Contractors and Consolidated Contractors Company W.L.L.
5. Currency: SAR (Saudi Arabia Rial)
6. Amount-related text blocks:
   - Gross Amt (SAR): 20,085.71
   - VAT Amt (SAR): 993.61
   - VAT %: 5%
   - VAT Amt (SAR): 411.36
   - VAT %: 5%"""

    res_bahra = service.extract_fields(ocr_text_bahra, "invoice")
    print("BAHRA GPT Output:", vars(res_bahra))
    
    ocr_text_cps = """1. Document Number: 490  
2. Document Date: Knigswinter, 17.10.2018  
3. Vendor Name: CPS Construction Plant Service GmbH  
4. Customer Name: Almabani General Contractors  
5. Currency: EUR  
6. Amount-related text blocks:
   - Total Price ex works: EUR 216,00
   - Packing and Pre-Carriage: EUR 60,00
   - Total Price FCA Koenigswinter, Germany: EUR 276,00"""

    res_cps = service.extract_fields(ocr_text_cps, "invoice")
    print("CPS GPT Output:", vars(res_cps))

if __name__ == "__main__":
    main()
