import pandas as pd
import json
import os

MASTER_FILE = "master.xlsx"

def export_excel(data, mode):

    parsed = json.loads(data)

    df = pd.DataFrame([parsed])

    if mode == "Create New Excel":

        path = "output.xlsx"

        df.to_excel(
            path,
            index=False
        )

        return path

    if mode == "Append To Master Excel":

        if os.path.exists(MASTER_FILE):

            existing = pd.read_excel(
                MASTER_FILE
            )

            combined = pd.concat(
                [existing, df],
                ignore_index=True
            )

            combined.to_excel(
                MASTER_FILE,
                index=False
            )

        else:

            df.to_excel(
                MASTER_FILE,
                index=False
            )

        return MASTER_FILE