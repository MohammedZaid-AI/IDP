import json

def validate_json(data):

    try:

        obj = json.loads(data)

        issues = []

        required_fields = [
            "invoice_number",
            "invoice_date",
            "vendor_name",
            "currency",
            "total_amount"
        ]

        for field in required_fields:

            if field not in obj:
                issues.append(f"Missing field: {field}")

            elif obj[field] is None:
                issues.append(f"Empty field: {field}")

            elif str(obj[field]).strip() == "":
                issues.append(f"Empty field: {field}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "data": obj
        }

    except Exception as e:

        return {
            "valid": False,
            "issues": [str(e)],
            "data": None
        }