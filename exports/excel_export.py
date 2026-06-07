import json
import pandas as pd

def export_excel(data):

    parsed = json.loads(data)

    df = pd.DataFrame([parsed])

    path = "output.xlsx"

    df.to_excel(
        path,
        index=False
    )

    return path