from flask import Flask, jsonify
import os
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# GIẢ ĐỊNH: mày chạy docker như vầy:
# docker run -it --name ncnas-scanner -p 5003:5000 \
#   -v "Z:\auto_add_listing:/ncnas/auto_add_listing" \
#   ncnas-scanner
#
# => bên trong container sẽ có: /ncnas/auto_add_listing/...
BASE_ROOT = "/ncnas/auto_add_listing"

THUMB_DIR_NAME = "thumbnail"


def list_dir_safe(path):
    try:
        return sorted(os.listdir(path))
    except Exception as e:
        return [f"<cannot list: {e}>"]


@app.route("/products", methods=["GET"])
def list_base_root():
    """
    GET /products
    → liệt kê bên trong:
       /ncnas/auto_add_listing/POD4 Xmas Ugly Sweatshirt/thumbnail
    và nếu có thì đi tiếp vào 'girl book'
    """
    # 1) kiểm tra đã mount chưa
    if not os.path.isdir(BASE_ROOT):
        return jsonify({
            "error": "BASE_ROOT does not exist inside container",
            "base_root": BASE_ROOT,
            "hint": r"Chạy lại: docker run -v ""Z:\auto_add_listing:/ncnas/auto_add_listing"" ...",
            "parent_dir": os.path.dirname(BASE_ROOT),
            "list_parent": list_dir_safe(os.path.dirname(BASE_ROOT))
        }), 404

    # 2) tới folder POD4...
    pod4_path = os.path.join(BASE_ROOT, "POD4 Xmas Ugly Sweatshirt")
    if not os.path.isdir(pod4_path):
        return jsonify({
            "error": "POD4 Xmas Ugly Sweatshirt does not exist inside container",
            "expected_path": pod4_path,
            "hint": "Kiểm tra lại tên folder trong Z:\\auto_add_listing",
            "auto_add_listing_list": list_dir_safe(BASE_ROOT)
        }), 404

    # 3) tới thumbnail
    thumb_path = os.path.join(pod4_path, "thumbnail")
    if not os.path.isdir(thumb_path):
        return jsonify({
            "error": "thumbnail does not exist inside container",
            "expected_path": thumb_path,
            "pod4_list": list_dir_safe(pod4_path)
        }), 404

    # 4) tới girl book (có khoảng trắng)
    girl_book_path = os.path.join(thumb_path, "girl book")
    if not os.path.isdir(girl_book_path):
        return jsonify({
            "error": "girl book does not exist inside container",
            "expected_path": girl_book_path,
            "thumbnail_list": list_dir_safe(thumb_path)
        }), 404

    # 5) liệt kê bên trong girl book
    entries = []
    for name in list_dir_safe(girl_book_path):
        full_path = os.path.join(girl_book_path, name)
        entries.append({
            "name": name,
            "is_dir": os.path.isdir(full_path),
            "full_path": full_path
        })

    return jsonify({
        "target": girl_book_path,
        "exists": True,
        "entries": entries,
        "meta": {
            "generated_at": datetime.now().isoformat()
        }
    })






# 2) ENDPOINT CŨ: đọc product cụ thể
@app.route("/products/<path:relpath>", methods=["GET"])
def get_product(relpath):
    """
    relpath là phần SAU /ncnas/daocta
    ví dụ user gọi:
      /products/T10/POD4 Xmas Ugly Sweatshirt/mk/1/girl book

    thì:
      parts = ["T10", "POD4 Xmas Ugly Sweatshirt", "mk", "1", "girl book"]
      product_name = "girl book"
      base_path    = /ncnas/daocta/T10/POD4 Xmas Ugly Sweatshirt/mk/1
    """
    parts = relpath.split("/")
    if len(parts) < 2:
        return jsonify({
            "error": "Need at least base_path and product_name",
            "received": relpath,
            "example": "GET /products/T10/POD4 Xmas Ugly Sweatshirt/mk/1/girl book"
        }), 400

    product_name = parts[-1]            # "girl book"
    subdir = os.path.join(*parts[:-1])  # "T10/.../mk/1"
    base_path = os.path.join(BASE_ROOT, subdir)

    # 0. check base root
    if not os.path.isdir(BASE_ROOT):
        return jsonify({
            "error": "BASE_ROOT does not exist inside container",
            "base_root": BASE_ROOT,
            "hint": "Kiểm tra -v Z:\\daocta:/ncnas/daocta trong docker run",
            "list_base_root_parent": list_dir_safe(os.path.dirname(BASE_ROOT))
        }), 404

    # 1. check base_path (tức là .../mk/1)
    if not os.path.isdir(base_path):
        return jsonify({
            "error": "Product base path does not exist",
            "base_root": BASE_ROOT,
            "requested_subdir": subdir,
            "full_base_path": base_path,
            "list_base_root": list_dir_safe(BASE_ROOT)
        }), 404

    # 2. check thumbnail root
    thumb_root = os.path.join(base_path, THUMB_DIR_NAME, product_name)
    if not os.path.isdir(thumb_root):
        return jsonify({
            "error": "product thumbnail folder not found",
            "expected_product_thumbnail": thumb_root,
            "note": "Trong thư mục này phải có các group như eye, hair, ...",
            "list_thumbnail_parent": list_dir_safe(os.path.join(base_path, THUMB_DIR_NAME)),
            "received_product_name": product_name
        }), 404

    # 3. liệt kê group trong thumbnail
    group_names = [
        d for d in os.listdir(thumb_root)
        if os.path.isdir(os.path.join(thumb_root, d))
    ]

    groups = [build_group(base_path, product_name, g) for g in group_names]

    result = {
        "product_name": product_name,
        "product_code": product_name.replace(" ", "-").lower(),
        "base_root": BASE_ROOT,
        "base_path": base_path,
        "groups": groups,
        "meta": {
            "generated_by": "flask-ncnas-scanner",
            "generated_at": datetime.now().isoformat()
        },
        "debug": {
            "relpath": relpath,
            "parts": parts,
            "group_names": group_names
        }
    }

    import json
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)

    return jsonify(result)


if __name__ == "__main__":
    # để log ra console cho dễ debug
    app.run(host="0.0.0.0", port=5000, debug=True)
