import pandas as pd
import pyodbc
import time

# Database connection string
DB_CONNECTION_STRING = "Driver={ODBC Driver 17 for SQL Server};Server=DESKTOP-6MNENLA;Database=DB_ECOMMERCE;UID=sa;PWD=123456;TrustServerCertificate=yes;"

def import_transactions():
    print("Connecting to database...")
    conn = pyodbc.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()

    print("Loading Transactions.xlsx...")
    df = pd.read_excel('Transactions.xlsx')
    
    # If the column name is 'OrderDate', rename to 'TDat'
    if 'OrderDate' in df.columns:
        df = df.rename(columns={'OrderDate': 'TDat'})

    # We need to map SKU (from Excel) to VariantId (from DB)
    print("Loading ProductVariants map...")
    cursor.execute("SELECT SKU, VariantId FROM ProductVariants")
    rows = cursor.fetchall()
    sku_to_variant = {row.SKU: row.VariantId for row in rows}

    print("Preparing data for insertion...")
    insert_data = []
    skipped = 0
    
    for index, row in df.iterrows():
        sku = str(row['SKU'])
        if sku in sku_to_variant:
            variant_id = sku_to_variant[sku]
            tdat = row['TDat']
            # handle cases where date is a string
            if isinstance(tdat, str):
                tdat = pd.to_datetime(tdat)
                
            customer_id = str(row['CustomerId'])
            price = float(row['Price'])
            
            insert_data.append((
                tdat.strftime('%Y-%m-%d %H:%M:%S'),
                customer_id,
                variant_id,
                price,
                1 # SalesChannelId default
            ))
        else:
            skipped += 1

    print(f"Total valid transactions ready to import: {len(insert_data)} (Skipped: {skipped} because SKU not in DB)")
    
    if len(insert_data) > 0:
        print("Inserting into Transactions table in batches...")
        
        insert_query = """
            INSERT INTO Transactions (TDat, CustomerId, VariantId, Price, SalesChannelId)
            VALUES (?, ?, ?, ?, ?)
        """
        
        # Batch insert
        batch_size = 1000
        start_time = time.time()
        
        for i in range(0, len(insert_data), batch_size):
            batch = insert_data[i:i+batch_size]
            cursor.executemany(insert_query, batch)
            conn.commit()
            print(f"Inserted {min(i+batch_size, len(insert_data))}/{len(insert_data)} records...")
            
        end_time = time.time()
        print(f"Import completed successfully in {end_time - start_time:.2f} seconds!")
    else:
        print("No records to insert.")
        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    import_transactions()
