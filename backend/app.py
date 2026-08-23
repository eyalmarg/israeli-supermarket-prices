import os
import sys
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
import queries  # noqa: E402

load_dotenv()

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "static"),
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search")
def api_search():
    term = request.args.get("q", "").strip()
    if len(term) < 2:
        return jsonify({"error": "נא להזין לפחות 2 תווים לחיפוש"}), 400
    limit = min(int(request.args.get("limit", 30)), 100)
    results = queries.search_products(term, limit=limit)
    return jsonify(results)


@app.route("/api/compare")
def api_compare():
    item_code = request.args.get("item_code", "").strip()
    if not item_code:
        return jsonify({"error": "נא לספק item_code"}), 400
    results = queries.compare_item(item_code)
    return jsonify(results)


@app.route("/api/supermarkets")
def api_supermarkets():
    return jsonify(queries.list_supermarkets())


@app.route("/api/stats")
def api_stats():
    return jsonify(queries.get_stats())


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(debug=True, port=port)
