import os
import pyodbc
import pickle
import numpy as np
from PIL import Image
from feature_extractor import FeatureExtractor

# Cấu hình
IMAGE_DIR = r'D:\Code\Do_an_tot_nghiep\BE_ECOMMERCE\wwwroot\images'
OUTPUT_FILE = 'image_features.pkl'

server = r'DESKTOP-6MNENLA'
db = 'DB_ECOMMERCE'
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db};UID=sa;PWD=123456'

def main():
    fe = FeatureExtractor()
    features_dict = {}

    try:
        print("Dang ket noi toi SQL Server...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("Ket noi Database thanh cong!")

        # Lấy danh sách sản phẩm (Lấy ảnh chính, nếu không có thì lấy ảnh của ProductVariant đầu tiên)
        cursor.execute("""
            SELECT ProductId AS ArticleId, ImageUrl 
            FROM (
                SELECT p.ProductId, 
                       COALESCE(p.ImageUrl, (SELECT TOP 1 pv.ImageUrl FROM ProductVariants pv WHERE pv.ProductId = p.ProductId AND pv.ImageUrl IS NOT NULL)) AS ImageUrl 
                FROM Products p
            ) t
            WHERE ImageUrl IS NOT NULL
        """)
        rows = cursor.fetchall()
        
        print(f"Tim thay {len(rows)} san pham co hinh anh. Bat dau trich xuat dac trung...")
        
        count = 0
        for row in rows:
            article_id = row.ArticleId
            image_name = os.path.basename(row.ImageUrl.replace('\\', '/'))
            
            img_path = os.path.join(IMAGE_DIR, image_name)
            
            if os.path.exists(img_path):
                try:
                    img = Image.open(img_path)
                    feature = fe.extract(img)
                    features_dict[article_id] = feature
                    count += 1
                    if count % 100 == 0:
                        print(f"  Da xu ly {count} anh...")
                except Exception as e:
                    print(f"Loi khi xu ly anh {img_path}: {e}")
            else:
                pass
                # print(f"Khong tim thay file anh: {img_path}")
                
        # Lưu ra file pickle
        with open(OUTPUT_FILE, 'wb') as f:
            pickle.dump(features_dict, f)
            
        print(f"Hoan tat! Da trich xuat va luu dac trung cua {count} anh vao {OUTPUT_FILE}.")

    except Exception as e:
        print(f"CO LOI XAY RA: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    main()
