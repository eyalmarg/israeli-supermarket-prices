import os
import sys

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(__file__))
import queries  # noqa: E402

load_dotenv()

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "static"),
)

MAX_BASKET_ITEMS = 100


def _city_arg():
    city = request.args.get("city", "").strip()
    return city or None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search")
def api_search():
    term = request.args.get("q", "").strip()
    if len(term) < 2:
        return jsonify({"error": "נא להזין לפחות 2 תווים לחיפוש"}), 400
    return jsonify(queries.search_products(term))


@app.route("/api/products/<item_code>")
def api_product(item_code):
    product = queries.get_product(item_code.strip(), city=_city_arg())
    if product is None:
        return jsonify({"error": "המוצר לא נמצא"}), 404
    return jsonify(product)


@app.route("/api/basket", methods=["POST"])
def api_basket():
    body = request.get_json(silent=True) or {}
    items = []
    for raw in (body.get("items") or [])[:MAX_BASKET_ITEMS]:
        code = str(raw.get("item_code", "")).strip()
        try:
            qty = float(raw.get("qty", 1))
        except (TypeError, ValueError):
            qty = 1.0
        if code and 0 < qty <= 1000:
            items.append({"item_code": code, "qty": qty})
    if not items:
        return jsonify({"error": "הסל ריק"}), 400
    city = (body.get("city") or "").strip() or None
    return jsonify(queries.compare_basket(items, city=city))


@app.route("/api/cities")
def api_cities():
    return jsonify(queries.list_cities())


@app.route("/api/supermarkets")
def api_supermarkets():
    return jsonify(queries.list_supermarkets())


@app.route("/api/stats")
def api_stats():
    return jsonify(queries.get_stats())


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=port)
