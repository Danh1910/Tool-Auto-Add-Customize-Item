# app.py
from flask import Flask, jsonify, request
import os
from datetime import datetime
from flask_cors import CORS
import requests  # <— new


app = Flask(__name__)
# bật CORS toàn cục + cho phép header Range nếu browser/element cần
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

# ===== CẤU HÌNH THEO ĐƯỜNG DẪN MỚI =====
BASE_PATH = r"\\NCNAS\web\customize_listing\hoangtt"
THUMB_DIR_NAME = "thumbnailImage"
PREVIEW_DIR_NAME = "overlayImage"

def list_png_recursive(root_dir: str):
    """
    Trả về danh sách TƯƠNG ĐỐI của tất cả file .png bên dưới root_dir (đệ quy).
    Ví dụ:
      root_dir = .../thumbnailImage/Book
      -> ['book-(1).png', 'v2/book-(2).png', ...]
    Nếu dir không tồn tại -> []
    """
    results = []
    if not os.path.isdir(root_dir):
        return results

    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.lower().endswith(".png"):
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, root_dir)
                # chuẩn hóa slash cho client
                results.append(rel.replace("\\", "/"))
    # sắp xếp ổn định để client map theo thứ tự
    results.sort()
    return results

def build_group_summary(product_name: str, group_name: str):
    """Tạo object group (label + số lượng option + đường dẫn + danh sách file)."""
    thumb_dir = os.path.join(BASE_PATH, product_name, THUMB_DIR_NAME, group_name)
    preview_dir = os.path.join(BASE_PATH, product_name, PREVIEW_DIR_NAME, group_name)

    thumb_list = list_png_recursive(thumb_dir)
    overlay_list = list_png_recursive(preview_dir)

    # số lượng option lấy theo thumbnail (như logic cũ)
    num_png = len(thumb_list)

    return {
        "key": group_name,
        "label": f"Choose {group_name.capitalize()}",
        "number_option": num_png,
        "thumbnail_dir": thumb_dir,
        "preview_dir": preview_dir,
        # mới thêm: danh sách file tương đối
        "thumbnail": thumb_list,
        "overlay": overlay_list
    }

@app.route("/products", methods=["GET"])
def get_product_summary():
    """
    Gọi:
      http://127.0.0.1:5003/products?sku=SKU_ABC
    → trả về danh sách group kèm danh sách file thumbnail/overlay.
    """
    product_name = request.args.get("sku")
    if not product_name:
        return jsonify({"error": "Missing required param: sku"}), 400

    thumbnail_root = os.path.join(BASE_PATH, product_name, THUMB_DIR_NAME)

    if not os.path.isdir(thumbnail_root):
        return jsonify({
            "error": f"thumbnail folder not found: {thumbnail_root}"
        }), 404

    # Lấy danh sách group con trong thumbnailImage
    group_names = [
        d for d in os.listdir(thumbnail_root)
        if os.path.isdir(os.path.join(thumbnail_root, d))
    ]
    group_names.sort()

    groups_summary = [build_group_summary(product_name, gname) for gname in group_names]

    result = {
        "product_name": product_name,
        "product_code": product_name.replace(" ", "-").lower(),
        "base_path": BASE_PATH,
        "groups": groups_summary,
        "meta": {
            "generated_by": "flask-ncnas-summary",
            "generated_at": datetime.now().isoformat()
        }
    }

    return jsonify(result)

# ---- (NEW) PROXY ẢNH ----
ALLOWED_PROXY_HOSTS = {"files.bkteam.top"}  # để tránh bị lợi dụng proxy

@app.get("/proxy")
def proxy_image():
    """
    Dùng:  /proxy?u=<public_image_url>
    Ví dụ: /proxy?u=https%3A%2F%2Ffiles.bkteam.top%2Fcustomize_listing%2F...
    """
    u = request.args.get("u", "").strip()
    if not u:
        return jsonify({"error": "missing param u"}), 400

    # Chặn host lạ
    try:
        from urllib.parse import urlparse
        host = urlparse(u).hostname or ""
    except Exception:
        return jsonify({"error": "invalid url"}), 400

    if host not in ALLOWED_PROXY_HOSTS:
        return jsonify({"error": f"host not allowed: {host}"}), 400

    # Forward 1 số header hữu ích (Range nếu phía client yêu cầu)
    headers = {}
    if "Range" in request.headers:
        headers["Range"] = request.headers["Range"]

    try:
        r = requests.get(u, headers=headers, stream=True, timeout=20)
    except requests.RequestException as e:
        return jsonify({"error": f"upstream fetch failed: {str(e)}"}), 502

    # Chuẩn bị streaming Response
    def gen():
        for chunk in r.iter_content(chunk_size=64 * 1024):
            if chunk:
                yield chunk

    # Lấy content-type từ upstream
    content_type = r.headers.get("Content-Type", "application/octet-stream")
    status_code = r.status_code  # hỗ trợ 206 Partial Content nếu có Range

    resp = Response(stream_with_context(gen()), status=status_code, mimetype=content_type)

    # Pass-through 1 số header (nếu có)
    passthrough = [
        "Content-Length", "Content-Range", "Accept-Ranges", "Last-Modified", "ETag", "Cache-Control"
    ]
    for h in passthrough:
        if h in r.headers:
            resp.headers[h] = r.headers[h]

    # CORS cho content script
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Range"

    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
