import pandas as pd
import pyodbc
import numpy as np
from datetime import datetime

# --- 1. Cấu hình kết nối ---
server = r'DESKTOP-6MNENLA'
db = 'DB_ECOMMERCE'
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db};UID=sa;PWD=123456'

try:
    print("⏳ Đang kết nối tới SQL Server...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("✅ Kết nối Database thành công!")

    # --- 2. Đọc file Excel ---
    # Đảm bảo tên file này khớp với tên file Excel đang nằm trong máy bạn
    file_name = 'products.xlsx' 
    df_prod = pd.read_excel(file_name, engine='openpyxl')
    
    # Xử lý các giá trị NaN của Pandas thành None của Python để SQL hiểu là NULL
    df_prod = df_prod.replace({np.nan: None})

    print(f"⏳ Đang xử lý mã SKU và đổ {len(df_prod)} dòng vào bảng Products...")

    # --- 3. Câu lệnh Insert (Chính xác 13 cột và 13 dấu ?) ---
    insert_query = """
        INSERT INTO Products (
            ArticleId, ProductCode, ProductName, CategoryId, Color, 
            Size, Price, StockQuantity, ImageUrl, Description,
            IsActived, CreatedAt, UpdatedAt
        ) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # --- 4. Chèn dữ liệu từng dòng ---
    for index, row in df_prod.iterrows():
        # Lấy mã gốc 10 số và 7 số
        base_article_id = str(row['ArticleId']).split('.')[0].zfill(10)
        product_code = str(row['ProductCode']).split('.')[0].zfill(7)
        
        # Xử lý dọn dẹp chuỗi Size
        size = str(row['Size']).strip() if pd.notna(row['Size']) else ""
        
        # TẠO MÃ DUY NHẤT (SKU): Ghép Size vào mã ArticleId để tránh trùng Khóa chính
        if size and size.lower() != 'nan' and size.lower() != 'none':
            unique_article_id = f"{base_article_id}-{size}"
        else:
            unique_article_id = base_article_id
            
        # Truyền chính xác 13 tham số vào Database
        cursor.execute(insert_query, 
            unique_article_id,                                # 1. Đã dùng mã SKU duy nhất
            product_code,                                     # 2. ProductCode
            str(row['ProductName']),                          # 3. ProductName
            int(row['CategoryId']),                           # 4. CategoryId
            str(row['Color']) if pd.notna(row['Color']) else None, # 5. Color
            size if size and size.lower() != 'nan' else None, # 6. Size
            float(row['Price']),                              # 7. Price
            int(row['StockQuantity']),                        # 8. StockQuantity
            str(row['ImageUrl']) if pd.notna(row['ImageUrl']) else None, # 9. ImageUrl
            str(row['Description']) if pd.notna(row['Description']) else None, # 10. Description
            1,                                                # 11. IsActived = True
            datetime.now(),                                   # 12. CreatedAt
            datetime.now()                                    # 13. UpdatedAt
        )

    # Lưu thay đổi (Commit)
    conn.commit()
    print("🎉 HOÀN TẤT XUẤT SẮC! Đã import toàn bộ Sản phẩm thành công.")

except pyodbc.IntegrityError as e:
    print(f"❌ LỖI RÀNG BUỘC (Khóa chính / Khóa ngoại):")
    print(f"Chi tiết: {e}")
except Exception as e:
    print(f"❌ CÓ LỖI XẢY RA: {e}")
finally:
    if 'conn' in locals():
        conn.close()