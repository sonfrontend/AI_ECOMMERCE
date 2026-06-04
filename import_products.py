import pandas as pd
import pyodbc
import numpy as np
from datetime import datetime

# --- 1. Cấu hình kết nối ---
server = r'DESKTOP-6MNENLA'
db = 'DB_ECOMMERCE'
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db};UID=sa;PWD=123456'

try:
    print("Dang ket noi toi SQL Server...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("Ket noi Database thanh cong!")

    # --- 2. Lấy danh sách CategoryId hợp lệ ---
    cursor.execute("SELECT Id FROM Categories")
    valid_categories = {row[0] for row in cursor.fetchall()}

    # --- 3. Xóa dữ liệu cũ ---
    print("Dang xoa du lieu cu trong bang ProductVariants va Products...")
    cursor.execute("DELETE FROM ProductVariants")
    cursor.execute("DELETE FROM Products")
    conn.commit()

    # --- 4. Đọc và Import bảng Products ---
    print("Dang doc file Products.xlsx...")
    df_prod = pd.read_excel('Products.xlsx', engine='openpyxl')
    df_prod = df_prod.replace({np.nan: None})

    print(f"Dang do {len(df_prod)} dong vao bang Products...")
    insert_prod_query = """
        INSERT INTO Products (
            ProductId, ProductName, CategoryId, Description, DiscountPercentage,
            DiscountStartDate, DiscountEndDate, ImageUrl, SoldQuantity, IsActived, CreatedAt, UpdatedAt
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    for index, row in df_prod.iterrows():
        cat_id = None
        if row['CategoryId'] is not None and not pd.isna(row['CategoryId']):
            try:
                parsed_cat = int(row['CategoryId'])
                if parsed_cat in valid_categories:
                    cat_id = parsed_cat
            except ValueError:
                pass

        cursor.execute(insert_prod_query,
            str(row['ProductId']) if row['ProductId'] else None,
            str(row['ProductName']) if row['ProductName'] else None,
            cat_id,
            str(row['Description']) if row['Description'] else None,
            int(row['DiscountPercentage']) if row['DiscountPercentage'] is not None else 0,
            row['DiscountStartDate'] if pd.notna(row['DiscountStartDate']) else None,
            row['DiscountEndDate'] if pd.notna(row['DiscountEndDate']) else None,
            str(row['ImageUrl']) if row['ImageUrl'] else None,
            int(row['SoldQuantity']) if row['SoldQuantity'] is not None else 0,
            1 if row.get('IsActive', 1) in [1, True, 'True', 'true'] else 0,
            row['CreatedAt'] if pd.notna(row['CreatedAt']) else datetime.now(),
            row['UpdatedAt'] if pd.notna(row['UpdatedAt']) else datetime.now()
        )
    conn.commit()
    print("Da import xong bang Products!")

    # --- 4. Đọc và Import bảng ProductVariants ---
    print("Dang doc file ProductVariants.xlsx...")
    df_var = pd.read_excel('ProductVariants.xlsx', engine='openpyxl')
    df_var = df_var.replace({np.nan: None})

    print(f"Dang do {len(df_var)} dong vao bang ProductVariants...")
    insert_var_query = """
        INSERT INTO ProductVariants (
            ProductId, SKU, Color, Size, StockQuantity,
            SoldQuantity, OriginalPrice, CurrentPrice, ImageUrl, IsActived, CreatedAt, UpdatedAt
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for index, row in df_var.iterrows():
        cursor.execute(insert_var_query,
            str(row['ProductId']) if row['ProductId'] else None,
            str(row['SKU']) if row['SKU'] else None,
            str(row['Color']) if row['Color'] else None,
            str(row['Size']) if row['Size'] else None,
            int(row['StockQuantity']) if row['StockQuantity'] is not None else 0,
            int(row['SoldQuantity']) if row['SoldQuantity'] is not None else 0,
            float(row['OriginalPrice']) if row['OriginalPrice'] is not None else 0.0,
            float(row['CurrentPrice']) if row['CurrentPrice'] is not None else 0.0,
            str(row['ImageUrl']) if row['ImageUrl'] else None,
            1 if row.get('IsActive', 1) in [1, True, 'True', 'true'] else 0,
            row['CreatedAt'] if pd.notna(row['CreatedAt']) else datetime.now(),
            row['UpdatedAt'] if pd.notna(row['UpdatedAt']) else datetime.now()
        )
    conn.commit()
    print("HOAN TAT! Da import toan bo du lieu thanh cong.")

except pyodbc.IntegrityError as e:
    print(f"LOI RANG BUOC (Khoa chinh / Khoa ngoai):")
    print(f"Chi tiet: {e}")
except Exception as e:
    print(f"CO LOI XAY RA: {e}")
finally:
    if 'conn' in locals():
        conn.close()