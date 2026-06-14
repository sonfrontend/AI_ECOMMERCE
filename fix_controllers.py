import os
import re

def fix_file(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple replacements
    content = content.replace('ArticleId', 'ProductId')
    content = content.replace('.Product.', '.ProductVariant.')
    content = content.replace('ProductCode', 'ProductId')
    content = content.replace('Price', 'CurrentPrice')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

base_dir = r"D:\Code\Do_an_tot_nghiep\BE_ECOMMERCE\Controllers"
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".cs"):
            fix_file(os.path.join(root, file))

# Fix services too
base_dir = r"D:\Code\Do_an_tot_nghiep\BE_ECOMMERCE\Services"
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".cs"):
            fix_file(os.path.join(root, file))
