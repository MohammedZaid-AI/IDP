import json

def check():
    with open('scratch/extracted_manual_evals.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    fields = [
        'Document Number', 'VAT Number', 'Date', 'Currency',
        'Vendor Arabic', 'Vendor English', 'Customer Arabic', 'Customer English',
        'Address Arabic', 'Address English', 'Subtotal', 'Tax', 'Total'
    ]

    results = {field: {'correct': 0, 'wrong': 0} for field in fields}

    for filename, table in data.items():
        for line in table.splitlines():
            if not line.strip().startswith('|'):
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 4:
                continue
            field_name = parts[1]
            status = parts[2]
            if field_name in fields:
                if '✅' in status:
                    results[field_name]['correct'] += 1
                elif '❌' in status:
                    results[field_name]['wrong'] += 1

    for field in fields:
        counts = results[field]
        total = counts['correct'] + counts['wrong']
        acc = counts['correct'] / total if total > 0 else 0
        print(f'{field}: correct={counts["correct"]}, wrong={counts["wrong"]}, total={total}, acc={acc:.1%}')

if __name__ == "__main__":
    check()
