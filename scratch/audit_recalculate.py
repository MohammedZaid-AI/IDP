import json

# Audited correctness for Qwen on the 14 aligned invoices
# True = Correct (✅), False = Wrong (❌)
qwen_correctness = {
    "1_BAHRA-CABLES-60129398.png": {
        "Document Number": False, "VAT Number": False, "Date": False, "Currency": False,
        "Vendor Arabic": False, "Vendor English": False, "Customer Arabic": False, "Customer English": False,
        "Address Arabic": False, "Address English": False, "Subtotal": False, "Tax": False, "Total": False
    },
    "1_BAHRI-BOLLORE-JED301286.png": {
        "Document Number": False, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": False, "Customer Arabic": True, "Customer English": False,
        "Address Arabic": False, "Address English": False, "Subtotal": False, "Tax": False, "Total": False
    },
    "1_BAIT-AL-BAKOURAH-50005.png": {
        "Document Number": False, "VAT Number": False, "Date": False, "Currency": False,
        "Vendor Arabic": True, "Vendor English": False, "Customer Arabic": True, "Customer English": False,
        "Address Arabic": False, "Address English": False, "Subtotal": False, "Tax": False, "Total": False
    },
    "1_CCS-CONSTRUCTION-COMPUTER-11341.png": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": False, "Vendor English": False, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": False, "Address English": False, "Subtotal": True, "Tax": True, "Total": True
    },
    "1_CONTRACTORS-AMBASSADOR-1738.png": {
        "Document Number": False, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": False,
        "Address Arabic": True, "Address English": False, "Subtotal": False, "Tax": False, "Total": False
    },
    "1_CPS-CONSTRUCTION-PLANT-490.png": {
        "Document Number": False, "VAT Number": False, "Date": False, "Currency": False,
        "Vendor Arabic": False, "Vendor English": False, "Customer Arabic": False, "Customer English": False,
        "Address Arabic": False, "Address English": False, "Subtotal": False, "Tax": False, "Total": False
    },
    "20220820_160723879.jpg": {
        "Document Number": True, "VAT Number": False, "Date": False, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": False, "Total": True
    },
    "20220820_160841493.jpg": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": False, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": False, "Tax": False, "Total": False
    },
    "20220820_160954815.jpg": {
        "Document Number": False, "VAT Number": False, "Date": False, "Currency": False,
        "Vendor Arabic": False, "Vendor English": False, "Customer Arabic": False, "Customer English": False,
        "Address Arabic": False, "Address English": False, "Subtotal": False, "Tax": False, "Total": False
    },
    "20220820_161037175.jpg": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": False
    },
    "4_JY2020-07-JV000603.png": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": False, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "4_JY2020-07-JV000710.png": {
        "Document Number": False, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": False, "Vendor English": False, "Customer Arabic": False, "Customer English": False,
        "Address Arabic": True, "Address English": False, "Subtotal": False, "Tax": False, "Total": False
    },
    "4_JY2020-07-JV000738.png": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": False, "Customer English": False,
        "Address Arabic": True, "Address English": False, "Subtotal": False, "Tax": False, "Total": False
    },
    "4_JY2020-07-JV000756.png": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": False, "Vendor English": True, "Customer Arabic": False, "Customer English": True,
        "Address Arabic": False, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    }
}

# Audited correctness for Gemma on the 14 aligned invoices
gemma_correctness = {
    "1_BAHRA-CABLES-60129398.png": {
        "Document Number": False, "VAT Number": False, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": False, "Customer Arabic": True, "Customer English": False,
        "Address Arabic": True, "Address English": False, "Subtotal": True, "Tax": True, "Total": True
    },
    "1_BAHRI-BOLLORE-JED301286.png": {
        "Document Number": True, "VAT Number": True, "Date": False, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": False, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "1_BAIT-AL-BAKOURAH-50005.png": {
        "Document Number": False, "VAT Number": False, "Date": False, "Currency": False,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": False, "Address English": False, "Subtotal": False, "Tax": False, "Total": False
    },
    "1_CCS-CONSTRUCTION-COMPUTER-11341.png": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "1_CONTRACTORS-AMBASSADOR-1738.png": {
        "Document Number": False, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": False,
        "Address Arabic": True, "Address English": False, "Subtotal": True, "Tax": True, "Total": True
    },
    "1_CPS-CONSTRUCTION-PLANT-490.png": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "20220820_160723879.jpg": {
        "Document Number": True, "VAT Number": False, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "20220820_160841493.jpg": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "20220820_160954815.jpg": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": False, "Vendor English": False, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "20220820_161037175.jpg": {
        "Document Number": False, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "4_JY2020-07-JV000603.png": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "4_JY2020-07-JV000710.png": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "4_JY2020-07-JV000738.png": {
        "Document Number": False, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": False, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    },
    "4_JY2020-07-JV000756.png": {
        "Document Number": True, "VAT Number": True, "Date": True, "Currency": True,
        "Vendor Arabic": True, "Vendor English": True, "Customer Arabic": True, "Customer English": True,
        "Address Arabic": True, "Address English": True, "Subtotal": True, "Tax": True, "Total": True
    }
}

fields = [
    'Document Number', 'VAT Number', 'Date', 'Currency',
    'Vendor Arabic', 'Vendor English', 'Customer Arabic', 'Customer English',
    'Address Arabic', 'Address English', 'Subtotal', 'Tax', 'Total'
]

def calculate_stats(correctness_dict):
    stats = {}
    for f in fields:
        correct = sum(1 for inv in correctness_dict.values() if inv[f])
        wrong = len(correctness_dict) - correct
        accuracy = (correct / len(correctness_dict)) * 100
        stats[f] = {"correct": correct, "wrong": wrong, "accuracy": f"{accuracy:.1f}%"}
    return stats

def main():
    qwen_stats = calculate_stats(qwen_correctness)
    gemma_stats = calculate_stats(gemma_correctness)
    
    print("="*60)
    print("RECALCULATED FIELD ACCURACIES (14 ALIGNED INVOICES)")
    print("="*60)
    print(f"{'Field':<20} | {'Qwen Correct':<12} | {'Qwen Acc':<8} | {'Gemma Correct':<13} | {'Gemma Acc':<9}")
    print("-"*75)
    for f in fields:
        q_c = qwen_stats[f]["correct"]
        q_a = qwen_stats[f]["accuracy"]
        g_c = gemma_stats[f]["correct"]
        g_a = gemma_stats[f]["accuracy"]
        print(f"{f:<20} | {q_c:<12} | {q_a:<8} | {g_c:<13} | {g_a:<9}")
    print("="*60)
    
    # Calculate group accuracies
    def get_group_acc(stats, group_fields):
        correct = sum(stats[f]["correct"] for f in group_fields)
        total = len(group_fields) * 14
        return f"{(correct / total) * 100:.1f}%"
        
    print("\nRECALCULATED METRICS FOR COMPARISON TABLE:")
    
    qwen_comp = {
        "valid_json": "100.0%", # Both models output valid JSON
        "vendor_acc": get_group_acc(qwen_stats, ["Vendor Arabic", "Vendor English"]),
        "customer_acc": get_group_acc(qwen_stats, ["Customer Arabic", "Customer English"]),
        "arabic_acc": get_group_acc(qwen_stats, ["Vendor Arabic", "Customer Arabic", "Address Arabic"]),
        "english_acc": get_group_acc(qwen_stats, ["Vendor English", "Customer English", "Address English"]),
        "doc_num": qwen_stats["Document Number"]["accuracy"],
        "vat": qwen_stats["VAT Number"]["accuracy"],
        "date": qwen_stats["Date"]["accuracy"],
        "totals": get_group_acc(qwen_stats, ["Subtotal", "Tax", "Total"])
    }
    
    gemma_comp = {
        "valid_json": "100.0%",
        "vendor_acc": get_group_acc(gemma_stats, ["Vendor Arabic", "Vendor English"]),
        "customer_acc": get_group_acc(gemma_stats, ["Customer Arabic", "Customer English"]),
        "arabic_acc": get_group_acc(gemma_stats, ["Vendor Arabic", "Customer Arabic", "Address Arabic"]),
        "english_acc": get_group_acc(gemma_stats, ["Vendor English", "Customer English", "Address English"]),
        "doc_num": gemma_stats["Document Number"]["accuracy"],
        "vat": gemma_stats["VAT Number"]["accuracy"],
        "date": gemma_stats["Date"]["accuracy"],
        "totals": get_group_acc(gemma_stats, ["Subtotal", "Tax", "Total"])
    }
    
    print("\nComparison Summary:")
    print(f"{'Metric':<20} | {'Qwen2.5-3B':<12} | {'Gemma4:E4B':<12} | {'Winner':<12}")
    print("-"*62)
    for m in qwen_comp:
        q_v = qwen_comp[m]
        g_v = gemma_comp[m]
        q_f = float(q_v.replace('%', ''))
        g_f = float(g_v.replace('%', ''))
        winner = "Gemma4:E4B" if g_f > q_f else ("Qwen2.5-3B" if q_f > g_f else "Tie")
        print(f"{m:<20} | {q_v:<12} | {g_v:<12} | {winner:<12}")

if __name__ == "__main__":
    main()
