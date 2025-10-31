from flask import Flask, jsonify
import os
from datetime import datetime
from flask_cors import CORS   # <— thêm dòng này

app = Flask(__name__)
CORS(app)   # <— bật CORS cho toàn bộ app

# CHỈNH CHỖ NÀY THEO MÁY BẠN
BASE_PATH = r"\\NCNAS\homes\daocta\T10\POD4 Xmas Ugly Sweatshirt\mk\1"

# 2 thư mục con cố định
THUMB_DIR_NAME = "thumbnail"
PREVIEW_DIR_NAME = "ct"


def list_png_recursive(root_dir):
    """
    Trả về danh sách TƯƠNG ĐỐI của tất cả file .png bên dưới root_dir (đệ quy).
    Ví dụ:
      root_dir = .../thumbnail/girl book/hair
      -> ['hair1/black.png', 'hair1/blonde.png', 'hair2/red.png', ...]
    Nếu root_dir không tồn tại -> []
    """
    results = []
    if not os.path.isdir(root_dir):
        return results

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # dirpath: đường dẫn tuyệt đối tới thư mục hiện tại
        # để lấy đường dẫn tương đối so với root_dir
        rel_dir = os.path.relpath(dirpath, root_dir)
        for f in filenames:
            if f.lower().endswith(".png"):
                # nếu đang đúng ngay root_dir thì rel_dir sẽ là '.'
                if rel_dir == ".":
                    rel_path = f
                else:
                    rel_path = os.path.join(rel_dir, f)
                results.append(rel_path)
    return results


def build_group(product_name, group_name):
    """
    product_name: ví dụ "girl book"
    group_name: ví dụ "book", "eye", "hair", ...
    Với group có nhiều cấp (hair/hair1/*.png, hair/hair2/*.png) thì ta sẽ
    đi đệ quy và gom hết png lại thành options.
    """
    thumb_dir = os.path.join(BASE_PATH, THUMB_DIR_NAME, product_name, group_name)
    preview_dir = os.path.join(BASE_PATH, PREVIEW_DIR_NAME, product_name, group_name)

    # Lấy toàn bộ file .png (đệ quy)
    thumb_files = list_png_recursive(thumb_dir)

    options = []
    order = 1
    for rel_path in sorted(thumb_files):
        # rel_path có thể là "hair1/black.png" hoặc "black.png"
        filename_no_ext = os.path.splitext(os.path.basename(rel_path))[0]

        # Để sinh id ổn định: thay dấu \ hoặc / bằng _
        safe_rel = rel_path.replace("\\", "/")
        safe_rel = safe_rel.replace("/", "_")

        option_id = f"{group_name}-{safe_rel}"

        options.append({
            "id": option_id,
            "order": order,
            # tên hiển thị: group + (thư mục con nếu có)
            # ví dụ: "hair / hair1 / black"
            "name": rel_path.replace("\\", "/"),
            # EXTENSION sẽ ghép thumbnail_dir + rel_path để lấy file
            "thumbnail_file": rel_path,
            "preview_file": rel_path  # nếu ct giống cấu trúc thì ok
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
    (và đệ quy trong từng group)
    """
    # thư mục chứa các group trong thumbnail
    thumbnail_root = os.path.join(BASE_PATH, THUMB_DIR_NAME, product_name)

    if not os.path.isdir(thumbnail_root):
        return jsonify({"error": f"thumbnail folder not found: {thumbnail_root}"}), 404

    # liệt kê các group theo thumbnail (book, eye, glasses, hair, outfit1, outfit2, skin,...)
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
    app.run(host="0.0.0.0", port=5001, debug=True)
