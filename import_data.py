import pandas as pd
from sqlalchemy import create_engine
import urllib

def main():
    print("Starting import...")
    # Connection string
    params = urllib.parse.quote_plus(
        'Driver={ODBC Driver 17 for SQL Server};'
        'Server=DESKTOP-6MNENLA;'
        'Database=DB_ECOMMERCE;'
        'UID=sa;'
        'PWD=123456;'
        'TrustServerCertificate=yes;'
    )
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

    try:
        print("Reading Products.xlsx...")
        df_products = pd.read_excel('AI_Recommendation/Products.xlsx')
        print("Products columns:", df_products.columns.tolist())
        
        # Rename columns to match DB
        rename_map_products = {
            'IsActive': 'IsActived'
        }
        df_products.rename(columns=rename_map_products, inplace=True)
        
        # Handle nan
        df_products = df_products.where(pd.notnull(df_products), None)
        
        # Insert
        print("Inserting Products into DB...")
        df_products.to_sql('Products', engine, if_exists='append', index=False)
        print("Products imported successfully.")
    except Exception as e:
        print("Error importing products:", e)

    try:
        print("Reading ProductVariants.xlsx...")
        df_variants = pd.read_excel('AI_Recommendation/ProductVariants.xlsx')
        print("Variants columns before rename:", df_variants.columns.tolist())
        
        # Fix truncated column names if they exist in Excel, and map to DB
        rename_map_variants = {
            'IsActive': 'IsActived',
            'ockQuantity': 'StockQuantity',
            'oldQuantity': 'SoldQuantity',
            'riginalPrice': 'OriginalPrice',
            'urrentPrice': 'CurrentPrice'
        }
        # Iterate over columns and rename if they start/match the truncated names
        for col in df_variants.columns:
            if 'ockQuant' in col: rename_map_variants[col] = 'StockQuantity'
            if 'oldQuant' in col: rename_map_variants[col] = 'SoldQuantity'
            if 'riginal' in col or 'Original' in col: rename_map_variants[col] = 'OriginalPrice'
            if 'urrent' in col or 'Current' in col: rename_map_variants[col] = 'CurrentPrice'
            
        df_variants.rename(columns=rename_map_variants, inplace=True)
        print("Variants columns after rename:", df_variants.columns.tolist())
        
        if 'VariantId' in df_variants.columns:
            df_variants.drop(columns=['VariantId'], inplace=True)
            
        # Handle nan
        df_variants = df_variants.where(pd.notnull(df_variants), None)
        
        print("Inserting ProductVariants into DB...")
        df_variants.to_sql('ProductVariants', engine, if_exists='append', index=False)
        print("ProductVariants imported successfully.")
    except Exception as e:
        print("Error importing variants:", e)

if __name__ == "__main__":
    main()
