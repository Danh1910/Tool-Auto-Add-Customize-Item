from flask import Flask, jsonify
import os
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# BÊN TRONG CONTAINER: nhớ mount /ncnas vào đúng chỗ
BASE_PATH = "/NCNAS/daocta/T10/POD4 Xmas Ugly Sweatshirt/mk/1"

THUMB_DIR_NAME = "thumbnail"
PREVIEW_DIR_NAME = "ct"


def list_dir_safe(path):
    """Trả về list file/folder trong path, nếu không đọc được thì trả về []"""
    try:
        return sorted(os.listdir(path))
    except Exception as e:
        return [f"<cannot list: {e}>"]


def list_png_recursive(root_dir):
    results = []
    if not os.path.isdir(root_dir):
        return results

    for dirpath, dirnames, filenames in os.walk(root_dir):
        rel_dir = os.path.relpath(dirpath, root_dir)
        for f in filenames:
            if f.lower().endswith(".png"):
                if rel_dir == ".":
                    rel_path = f
                else:
                    rel_path = os.path.join(rel_dir, f)
                results.append(rel_path)
    return results


def build_group(product_name, group_name):
    thumb_dir = os.path.join(BASE_PATH, THUMB_DIR_NAME, product_name, group_name)
    preview_dir = os.path.join(BASE_PATH, PREVIEW_DIR_NAME, product_name, group_name)

    thumb_files = list_png_recursive(thumb_dir)

    options = []
    order = 1
    for rel_path in sorted(thumb_files):
        safe_rel = rel_path.replace("\\", "/").replace("/", "_")
        option_id = f"{group_name}-{safe_rel}"

        options.append({
            "id": option_id,
            "order": order,
            "name": rel_path.replace("\\", "/"),
            "thumbnail_file": rel_path,
            "preview_file": rel_path
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
    # 0. check base path
    if not os.path.isdir(BASE_PATH):
        return jsonify({
            "error": "BASE_PATH does not exist in container",
            "base_path": BASE_PATH,
            "hint": "Kiểm tra docker -v đã mount đúng chưa",
            "parent_dir_of_base_path": os.path.dirname(BASE_PATH),
            "list_parent": list_dir_safe(os.path.dirname(BASE_PATH))
        }), 404

    # 1. check thumbnail root (không có product_name)
    thumb_root_no_product = os.path.join(BASE_PATH, THUMB_DIR_NAME)
    if not os.path.isdir(thumb_root_no_product):
        return jsonify({
            "error": "thumbnail root (without product) not found",
            "thumbnail_root": thumb_root_no_product,
            "list_base_path": list_dir_safe(BASE_PATH)
        }), 404

    # 2. check thumbnail + product
    thumbnail_root = os.path.join(thumb_root_no_product, product_name)

    if not os.path.isdir(thumbnail_root):
        return jsonify({
            "error": "product thumbnail folder not found",
            "expected_product_thumbnail": thumbnail_root,
            "note": "Thư mục này phải tồn tại và bên trong có các nhóm như 'hair','eye',... ",
            "list_thumbnail_root": list_dir_safe(thumb_root_no_product),
            "received_product_name": product_name
        }), 404

    # 3. liệt kê group
    group_names = [
        d for d in os.listdir(thumbnail_root)
        if os.path.isdir(os.path.join(thumbnail_root, d))
    ]

    groups = [build_group(product_name, g) for g in group_names]

    result = {
        "product_name": product_name,
        "product_code": product_name.replace(" ", "-").lower(),
        "base_path": BASE_PATH,
        "groups": groups,
        "meta": {
            "generated_by": "flask-ncnas-scanner",
            "generated_at": datetime.now().isoformat()
        },
        "debug": {
            "thumbnail_root": thumbnail_root,
            "group_names": group_names
        }
    }

    # in ra container
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)

    return jsonify(result)


if __name__ == "__main__":
    # chạy đúng port 5000 như docker map
    app.run(host="0.0.0.0", port=5000)
