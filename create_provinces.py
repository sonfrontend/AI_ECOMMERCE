import requests
import random

BASE_URL = "http://localhost:5000/api/ShippingFee"

provinces = [
    "Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Hải Phòng", "Cần Thơ", 
    "Bình Dương", "Đồng Nai", "Bà Rịa - Vũng Tàu", "Tây Ninh", "Bình Phước", 
    "Long An", "Tiền Giang", "Bến Tre", "Trà Vinh", "Vĩnh Long", 
    "Đồng Tháp", "An Giang", "Kiên Giang", "Sóc Trăng", "Bạc Liêu", 
    "Cà Mau", "Lâm Đồng", "Đắk Lắk", "Đắk Nông", "Gia Lai", 
    "Kon Tum", "Khánh Hòa", "Phú Yên", "Bình Định", "Quảng Ngãi", 
    "Quảng Nam", "Thừa Thiên Huế", "Quảng Trị", "Quảng Bình"
]

print(f"Bắt đầu tạo {len(provinces)} tỉnh thành...")

for province in provinces:
    # HCM là 10k, các tỉnh khác random từ 15k đến 39k (bước giá 1k)
    fee = 10000 if province == "Hồ Chí Minh" else random.randint(15, 39) * 1000
    
    payload = {
        "provinceName": province,
        "fee": fee
    }
    
    try:
        response = requests.post(BASE_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ Đã tạo tỉnh {province} - Phí: {fee}đ")
        else:
            print(f"❌ Lỗi khi tạo {province}: {response.text}")
    except Exception as e:
        print(f"⚠️ Lỗi kết nối khi tạo {province}: {e}")

print("Hoàn tất!")
