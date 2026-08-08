import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from services.geocode import geocode, GeocodeError
from services.routing import road_distance_km, great_circle_km
from services.compare import compare
from services.groq_ai import parse_query, generate_summary

load_dotenv()

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/compare", methods=["POST"])
def api_compare():
    body = request.get_json(force=True, silent=True) or {}
    origin_text = (body.get("origin") or "").strip()
    destination_text = (body.get("destination") or "").strip()
    free_text = (body.get("query") or "").strip()

    # Free-text mode: "cheapest way from Kolkata to Delhi" -> parsed by Groq/regex
    if free_text and not (origin_text and destination_text):
        parsed = parse_query(free_text)
        if not parsed:
            return jsonify({
                "error": "Couldn't figure out an origin and destination from that. "
                         "Try phrasing it as \"from X to Y\", or fill in the two fields."
            }), 400
        origin_text, destination_text = parsed["origin"], parsed["destination"]

    if not origin_text or not destination_text:
        return jsonify({"error": "Both origin and destination are required."}), 400

    try:
        origin = geocode(origin_text)
        destination = geocode(destination_text)
    except GeocodeError as e:
        return jsonify({"error": str(e)}), 400

    air_km = great_circle_km(origin["lat"], origin["lon"], destination["lat"], destination["lon"])
    road_km = road_distance_km(origin["lat"], origin["lon"], destination["lat"], destination["lon"])

    result = compare(road_km, air_km)
    summary = generate_summary(
        origin["display_name"], destination["display_name"], result["options"], result["badges"]
    )

    return jsonify({
        "origin": origin,
        "destination": destination,
        "road_km": round(road_km, 1),
        "air_km": round(air_km, 1),
        "options": result["options"],
        "badges": result["badges"],
        "summary": summary,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
