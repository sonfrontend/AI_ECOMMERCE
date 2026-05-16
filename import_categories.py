import pandas as pd
import pyodbc
import numpy as np

# --- 1. Cấu hình kết nối ---
server = r'DESKTOP-6MNENLA'
db = 'DB_ECOMMERCE'

# Đưa chuỗi kết nối vào đúng biến conn_str mà pyodbc cần
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db};UID=sa;PWD=123456'

try:
    print("⏳ Đang kết nối tới SQL Server...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("✅ Kết nối Database thành công!")

    # --- 2. Đọc file Excel ---
    df_cat = pd.read_excel('categories.xlsx', engine='openpyxl')
    
    # Xử lý các giá trị NaN của Pandas thành None của Python để SQL hiểu là NULL
    df_cat = df_cat.replace({np.nan: None})

    print(f"⏳ Đang đổ {len(df_cat)} dòng vào bảng Categories...")

    # --- 3. MỞ KHÓA cột Id (Bắt buộc với EF Core) ---
    cursor.execute("SET IDENTITY_INSERT Categories ON")

  # --- 4. Chèn dữ liệu từng dòng ---
    # Truyền thêm giá trị 1 (True) cho cột IsActived
    insert_query = """
        INSERT INTO Categories (Id, Name, ParentId, IsActived, CreatedAt, UpdatedAt) 
        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """ 
    
    for index, row in df_cat.iterrows():
        # Ép kiểu an toàn trước khi insert
        cat_id = int(row['Id'])
        cat_name = str(row['Name'])
        parent_id = int(row['ParentId']) if row['ParentId'] is not None else None
        
        cursor.execute(insert_query, cat_id, cat_name, parent_id)

    # --- 5. KHÓA LẠI cột Id (Rất quan trọng) ---
    cursor.execute("SET IDENTITY_INSERT Categories OFF")

    # Lưu thay đổi (Commit)
    conn.commit()
    print("🎉 HOÀN TẤT! Đã import danh mục thành công.")

except Exception as e:
    print(f"❌ CÓ LỖI XẢY RA: {e}")
finally:
    if 'conn' in locals():
        conn.close()