import requests

BASE_URL = "http://localhost:5000/api/Voucher/admin"

vouchers = [
    {"code": "WELCOME10K", "discountValue": 10000, "minOrderValue": 50000, "isActive": True},
    {"code": "SUMMER20K", "discountValue": 20000, "minOrderValue": 100000, "isActive": True},
    {"code": "FREESHIP30K", "discountValue": 30000, "minOrderValue": 150000, "isActive": True},
    {"code": "BIGSALE50K", "discountValue": 50000, "minOrderValue": 300000, "isActive": True},
    {"code": "VIP100K", "discountValue": 100000, "minOrderValue": 500000, "isActive": True}
]

print(f"Bắt đầu tạo {len(vouchers)} vouchers...")

for v in vouchers:
    try:
        response = requests.post(BASE_URL, json=v)
        if response.status_code == 200:
            print(f"✅ Đã tạo voucher {v['code']} - Giảm {v['discountValue']}đ (Đơn tối thiểu: {v['minOrderValue']}đ)")
        else:
            print(f"❌ Lỗi khi tạo {v['code']}: {response.text}")
    except Exception as e:
        print(f"⚠️ Lỗi kết nối khi tạo {v['code']}: {e}")

print("Hoàn tất!")
