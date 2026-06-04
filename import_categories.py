`import pandas as pd
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
    # Đảm bảo file Excel có đủ 4 cột: Id, Name, ParentId, Level
    df_cat = pd.read_excel('Categories_Full.xlsx', engine='openpyxl')
    
    # Xử lý các giá trị NaN của Pandas thành None của Python để SQL hiểu là NULL
    df_cat = df_cat.replace({np.nan: None})

    print(f"⏳ Đang đổ {len(df_cat)} dòng vào bảng Categories...")

    # --- 3. MỞ KHÓA cột Id (Bắt buộc với EF Core) ---
    cursor.execute("SET IDENTITY_INSERT Categories ON")

    # --- 4. Chèn dữ liệu từng dòng ---
    # BỔ SUNG: Thêm cột Level và thêm 1 dấu ? vào VALUE
    insert_query = """
        INSERT INTO Categories (Id, Name, ParentId, Level, IsActived, CreatedAt, UpdatedAt) 
        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """ 
    
    for index, row in df_cat.iterrows():
        # Ép kiểu an toàn trước khi insert
        # Lưu ý: Tên chuỗi trong ngoặc vuông row['...'] phải khớp chính xác 100% với tên cột trên dòng 1 của file Excel
        cat_id = int(row['Id'])
        cat_name = str(row['Name'])
        parent_id = int(row['ParentId']) if row['ParentId'] is not None else None
        
        # BỔ SUNG: Lấy dữ liệu Level từ Excel
        level = int(row['Level']) if row['Level'] is not None else 1
        
        # Truyền 4 tham số vào execute (khớp với 4 dấu ?)
        cursor.execute(insert_query, cat_id, cat_name, parent_id, level)

    # --- 5. KHÓA LẠI cột Id (Rất quan trọng) ---
    cursor.execute("SET IDENTITY_INSERT Categories OFF")

    # Lưu thay đổi (Commit)
    conn.commit()
    print("🎉 HOÀN TẤT! Đã import danh mục thành công.")

except pyodbc.ProgrammingError as e:
    print(f"❌ LỖI SQL: Có thể bảng Categories trong CSDL chưa có cột 'Level'.")
    print(f"Chi tiết: {e}")
except Exception as e:
    print(f"❌ CÓ LỖI XẢY RA: {e}")
finally:
    if 'conn' in locals():
        conn.close()`