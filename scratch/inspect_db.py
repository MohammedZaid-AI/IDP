import sqlite3
import pandas as pd

def main():
    conn = sqlite3.connect("database/idp.sqlite3")
    cursor = conn.cursor()
    
    # List tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    print("Tables:", tables)
    
    for table in tables:
        df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 5", conn)
        print(f"\nTable: {table} (columns: {df.columns.tolist()})")
        print(df.head(2))
        
    conn.close()

if __name__ == "__main__":
    main()
