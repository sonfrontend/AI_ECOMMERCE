import pandas as pd
import numpy as np

print("⏳ Đang đọc file dữ liệu...")
df_products = pd.read_csv('Products.xlsx')
df_categories = pd.read_csv('Categories_Full.xlsx')

# --- BƯỚC QUAN TRỌNG: Dọn dẹp tên cột ---
# Xóa bỏ mọi khoảng trắng thừa hoặc ký tự ẩn (BOM) ở đầu/cuối tên cột
df_products.columns = df_products.columns.str.strip().str.replace('\ufeff', '')
df_categories.columns = df_categories.columns.str.strip().str.replace('\ufeff', '')

print("👉 Tên các cột trong bảng Categories thực tế là:", df_categories.columns.tolist())

# Tự động nhận diện tên cột là 'Id' hay 'CategoryId'
id_col_name = 'CategoryId' if 'CategoryId' in df_categories.columns else 'Id'
print(f"✅ Hệ thống đã tự động chọn cột Mã danh mục là: '{id_col_name}'")

# 1. Lấy danh sách các CategoryId thực tế đang được sử dụng bởi Sản phẩm
used_category_ids = set(df_products['CategoryId'].dropna().astype(int).unique())

# 2. Tạo một bộ từ điển để tra cứu ParentId nhanh
category_dict = {}
for _, row in df_categories.iterrows():
    cat_id = int(row[id_col_name]) 
    parent_id = int(row['ParentId']) if pd.notna(row['ParentId']) else None
    category_dict[cat_id] = parent_id

# 3. Thuật toán TRUY NGƯỢC GIA PHẢ
categories_to_keep = set(used_category_ids)

print(f"🔍 Bắt đầu dò ngược từ {len(categories_to_keep)} danh mục gốc (Cấp 3)...")

added_new_parents = True
while added_new_parents:
    added_new_parents = False
    current_kept = list(categories_to_keep)
    for cat_id in current_kept:
        parent_id = category_dict.get(cat_id)
        if parent_id is not None and parent_id not in categories_to_keep:
            categories_to_keep.add(parent_id)
            added_new_parents = True 

# 4. Lọc bỏ các Danh mục rác ra khỏi bảng Categories ban đầu
df_filtered_categories = df_categories[df_categories[id_col_name].isin(categories_to_keep)].copy()
df_filtered_categories = df_filtered_categories.sort_values(by=['Level', id_col_name])

# 5. Xuất ra file Excel mới
file_output = 'Categories_Filtered_Clean.xlsx'
df_filtered_categories.to_excel(file_output, index=False)

print(f"🎉 HOÀN TẤT!")
print(f"👉 Tổng danh mục ban đầu: {len(df_categories)}")
print(f"👉 Danh mục thực tế được giữ lại (Đã gồm Cha/Ông nội): {len(df_filtered_categories)}")
print(f"👉 File kết quả đã được lưu tại: {file_output}")