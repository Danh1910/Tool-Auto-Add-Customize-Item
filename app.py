from flask import Flask, jsonify
import os
from datetime import datetime

app = Flask(__name__)

# CHỈNH CHỖ NÀY THEO MÁY BẠN
BASE_PATH = r"\\NCNAS\homes\daocta\T10\POD4 Xmas Ugly Sweatshirt\mk\1"

# 2 thư mục con cố định
THUMB_DIR_NAME = "thumbnail"
PREVIEW_DIR_NAME = "ct"


def list_png(path):
    """Trả về danh sách file .png trong thư mục (không đệ quy)."""
    if not os.path.isdir(path):
        return []
    return [f for f in os.listdir(path) if f.lower().endswith(".png")]


def build_group(product_name, group_name):
    """
    product_name: ví dụ "girl book"
    group_name: ví dụ "book", "eye", ...
    """
    thumb_dir = os.path.join(BASE_PATH, THUMB_DIR_NAME, product_name, group_name)
    preview_dir = os.path.join(BASE_PATH, PREVIEW_DIR_NAME, product_name, group_name)

    thumb_files = list_png(thumb_dir)
    # giả sử tên file 2 bên giống nhau
    options = []
    order = 1
    for filename in sorted(thumb_files):
        option_id = f"{group_name}-{order}"
        options.append({
            "id": option_id,
            "order": order,
            "name": os.path.splitext(filename)[0],
            "thumbnail_file": filename,
            "preview_file": filename  # nếu khác thì sau này bổ sung map
        })
        order += 1

    return {
        "key": group_name,
        "label": f"Choose {group_name.capitalize()}",
        "thumbnail_dir": thumb_dir,
        "preview_dir": preview_dir,
        "options": options
    }


@app.route("/products/<path:product_name>", methods=["GET"])
def get_product(product_name):
    """
    Ví dụ gọi:
      http://127.0.0.1:5000/products/girl%20book
    sẽ đọc:
      \\...\\thumbnail\\girl book\\*
      \\...\\ct\\girl book\\*
    """
    # thư mục chứa các group trong thumbnail
    thumbnail_root = os.path.join(BASE_PATH, THUMB_DIR_NAME, product_name)
    preview_root = os.path.join(BASE_PATH, PREVIEW_DIR_NAME, product_name)

    if not os.path.isdir(thumbnail_root):
        return jsonify({"error": f"thumbnail folder not found: {thumbnail_root}"}), 404

    # liệt kê các group theo thumbnail (book, eye, glasses, hair, outfit 1, outfit2, skin,...)
    group_names = [
        d for d in os.listdir(thumbnail_root)
        if os.path.isdir(os.path.join(thumbnail_root, d))
    ]

    groups = []
    for gname in group_names:
        grp = build_group(product_name, gname)
        groups.append(grp)

    result = {
        "product_name": product_name,
        "product_code": product_name.replace(" ", "-").lower(),
        "base_path": BASE_PATH,
        "groups": groups,
        "meta": {
            "generated_by": "flask-ncnas-scanner",
            "generated_at": datetime.now().isoformat()
        }
    }

    # in ra terminal cho bạn xem
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))

    return jsonify(result)


if __name__ == "__main__":
    # host=0.0.0.0 để máy khác trong LAN gọi được
    app.run(host="0.0.0.0", port=5000, debug=True)
