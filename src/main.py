import os
from flask import Flask, request, jsonify, make_response, redirect, url_for
import uuid
import json
import ast
import openrouteservice
import secrets
from datetime import datetime
from flasgger import Swagger
from functools import wraps
from dotenv import load_dotenv
from models import db, Route, RouteStep, ApiKey  # make sure ApiKey is imported

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////app/data/routes.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Provide your ORS API Key (consider using environment variables for production)
ORS_API_KEY = "5b3ce3597851110001cf6248dd952248d5e3474e87d768da5b5aff3d"
ors_client = openrouteservice.Client(key=ORS_API_KEY)

app.config["SERVER_NAME"] = "localhost:5000"


with app.app_context():
    db.create_all()

# Initialize Flasgger
swagger = Swagger(app)

# -----------------------------
# ADMIN PASSWORD DECORATOR
# -----------------------------
def require_admin_password(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Retrieve the admin password from the environment variable
        admin_password = os.environ.get("ADMIN_PASSWORD")
        provided_password = request.headers.get("Admin-Password")
        if not provided_password or provided_password != admin_password:
            return make_response(jsonify({"error": "Unauthorized: Invalid admin password"}), 401)
        return f(*args, **kwargs)
    return decorated

# -----------------------------
# API Key Endpoints (Admin Only)
# -----------------------------
@app.route("/api/v1/admin/apikeys", methods=["GET"])
@require_admin_password
def list_api_keys():
    """List all API keys (Admin Only)"""
    keys = ApiKey.query.all()
    keys_list = [{
        "key": key.key,
        "owner": key.owner,
        "created_at": key.created_at.isoformat()
    } for key in keys]
    return jsonify({"keys": keys_list})

# Optionally, if you want an admin endpoint to create an API key:
@app.route("/api/v1/admin/apikeys", methods=["POST"])
@require_admin_password
def create_api_key():
    """
    Create a new API key manually (Admin Only).
    You can then provide this key manually to your frontend.
    """
    data = request.get_json() or {}
    owner_name = data.get("owner", None)
    new_key_value = secrets.token_hex(16)  # generate a random 32-char hex string

    new_key = ApiKey(key=new_key_value, owner=owner_name)
    db.session.add(new_key)
    db.session.commit()

    return jsonify({
        "api_key": new_key_value,
        "owner": owner_name,
        "message": "API key created (admin only)"
    }), 201

# -----------------------------
# Protected Routes Endpoint (using API key)
# -----------------------------
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Expect the key in header "X-API-Key"
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify({"error": "Missing API key"}), 401
        # Check if the key exists in the database
        valid = ApiKey.query.filter_by(key=api_key).first()
        if not valid:
            return jsonify({"error": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/api/v1/routes", methods=["POST"])
@require_api_key
def create_route():
    """
    Create a new route using OpenRouteService, always allowing alternative_routes.
    - If only origin/destination (no steps), we do one call with alternative_routes.
    - If multiple steps, we do multi-segment calls and combine them.
    - Attempts to return only alternatives differing in >=2 segments, else falls back.
    ---
    tags:
      - Routes
    parameters:
      - in: header
        name: X-API-Key
        required: true
        type: string
        default: "MY_RANDOM_API_KEY"
        description: "API key to authorize this request"
      - in: body
        name: body
        required: true
        schema:
          id: CreateRoute
          required:
            - origin
            - destination
          properties:
            user_id:
              type: string
            origin:
              type: object
              properties:
                coordinates:
                  type: array
                  items:
                    type: number
            destination:
              type: object
              properties:
                coordinates:
                  type: array
                  items:
                    type: number
            preferences:
              type: array
              items:
                type: string
            steps:
              type: array
              items:
                type: object
                properties:
                  location:
                    type: string
                  notes:
                    type: string
                  coordinates:
                    type: array
                    items:
                      type: number
    responses:
      201:
        description: Route created successfully
        schema:
          id: CreateRouteResponse
          properties:
            id:
              type: string
            origin:
              type: object
            destination:
              type: object
            preferences:
              type: array
              items:
                type: string
            distance_m:
              type: number
            duration_s:
              type: number
            geometry:
              type: object
            details:
              type: string
            alternatives:
              type: array
              description: Up to 2 other full-route options
              items:
                type: object
                properties:
                  total_distance_m:
                    type: number
                  total_duration_s:
                    type: number
                  segments:
                    type: array
                    items:
                      type: object
    """
    data = request.get_json()
    if not data or "origin" not in data or "destination" not in data:
        return jsonify({"error": "Bad request, missing required fields"}), 400

    origin_coords = data["origin"].get("coordinates")
    destination_coords = data["destination"].get("coordinates")
    if not origin_coords or not destination_coords:
        return jsonify({"error": "Missing coordinates in origin/destination"}), 400

    steps_data = data.get("steps", [])
    preferences = data.get("preferences", [])

    # Build all waypoints: origin -> (steps) -> destination
    waypoints = [origin_coords]
    for step in steps_data:
        if "coordinates" in step:
            waypoints.append(step["coordinates"])
    waypoints.append(destination_coords)

    # -----------------------------
    # 1) CASE: EXACTLY 2 WAYPOINTS
    # -----------------------------
    if len(waypoints) == 2:
        try:
            # Single call with alternative_routes
            route_response = ors_client.directions(
                coordinates=waypoints,  # just origin & destination
                profile="driving-car",
                format="geojson",
                alternative_routes={
                    "target_count": 3,
                    "share_factor": 0.6,
                    "weight_factor": 1.6
                }
            )
        except Exception as e:
            return jsonify({"error": f"ORS error: {str(e)}"}), 500

        features = route_response.get("features", [])
        if not features:
            return jsonify({"error": "No features in ORS response"}), 500

        # Build a list of single-segment alternatives
        single_alts = []
        for feat in features:
            props = feat["properties"]
            dist = props["summary"]["distance"]
            dur = props["summary"]["duration"]
            geom = feat["geometry"]
            single_alts.append({
                "distance_m": dist,
                "duration_s": dur,
                "geometry": geom
            })

        # Sort by distance, best route is first
        single_alts.sort(key=lambda a: a["distance_m"])
        best_alt = single_alts[0]

        # Since there is only ONE segment, it can't differ in >=2 segments.
        # => We'll return no alternative routes in this scenario
        route_id = str(uuid.uuid4())
        new_route = Route(
            id=route_id,
            user_id=data.get("user_id"),
            origin=json.dumps(data["origin"]),
            destination=json.dumps(data["destination"]),
            preferences=str(preferences),
            details="Route created via ORS (2-waypoints). No alt can differ by >=2 segments.",
            distance_m=best_alt["distance_m"],
            duration_s=best_alt["duration_s"],
            geometry=json.dumps(best_alt["geometry"])
        )
        db.session.add(new_route)

        # Optionally store steps
        for index, step in enumerate(steps_data, start=1):
            new_step = RouteStep(
                route_id=route_id,
                step_order=index,
                location=step.get("location", ""),
                notes=step.get("notes", "")
            )
            db.session.add(new_step)

        db.session.commit()

        # Build final JSON
        best_response = {
            "id": route_id,
            "origin": data["origin"],
            "destination": data["destination"],
            "preferences": preferences,
            "distance_m": best_alt["distance_m"],
            "duration_s": best_alt["duration_s"],
            "geometry": best_alt["geometry"],
            "details": "Best 2-waypoints route stored in DB",
            "alternatives": []  # forced empty
        }
        return jsonify(best_response), 201

    # --------------------------------
    # 2) CASE: MULTIPLE STEPS (≥3 WPs)
    # --------------------------------
    import itertools

    segment_alternatives = []
    for i in range(len(waypoints) - 1):
        seg_start = waypoints[i]
        seg_end = waypoints[i + 1]

        try:
            # Each segment with up to 3 alternatives
            segment_resp = ors_client.directions(
                coordinates=[seg_start, seg_end],
                profile="driving-car",
                format="geojson",
                alternative_routes={
                    "target_count": 3,
                    "share_factor": 0.6,
                    "weight_factor": 1.6
                }
            )
        except Exception as e:
            return jsonify({"error": f"ORS error: {str(e)}"}), 500

        feats = segment_resp.get("features", [])
        if not feats:
            return jsonify({"error": "No features for segment"}), 500

        alt_list = []
        # Store 'alt_index' for easy segment-level comparison
        for alt_index, feat in enumerate(feats):
            props = feat["properties"]
            distance_m = props["summary"]["distance"]
            duration_s = props["summary"]["duration"]
            geometry = feat["geometry"]
            alt_list.append({
                "alt_index": alt_index,  # crucial for comparing segments later
                "distance_m": distance_m,
                "duration_s": duration_s,
                "geometry": geometry
            })
        segment_alternatives.append(alt_list)

    # Combine them (Cartesian product) => e.g., 3^N combos
    all_combos = list(itertools.product(*segment_alternatives))
    if not all_combos:
        return jsonify({"error": "No route combos found"}), 500

    # Build a list of possible full routes
    full_routes = []
    for combo_idx, combo_tuple in enumerate(all_combos):
        total_dist = sum(alt["distance_m"] for alt in combo_tuple)
        total_dur = sum(alt["duration_s"] for alt in combo_tuple)
        segments_info = []
        for seg_i, alt_obj in enumerate(combo_tuple):
            segments_info.append({
                "alt_index": alt_obj["alt_index"],
                "segment_index": seg_i,
                "distance_m": alt_obj["distance_m"],
                "duration_s": alt_obj["duration_s"],
                "geometry": alt_obj["geometry"]
            })

        full_routes.append({
            "combo_index": combo_idx,
            "total_distance_m": total_dist,
            "total_duration_s": total_dur,
            "segments": segments_info
        })

    # Sort by distance, pick the best route
    full_routes.sort(key=lambda r: r["total_distance_m"])
    best_route = full_routes[0]

    # Function to count how many segments differ between two routes
    def count_segment_diffs(route_a, route_b):
        """Return how many segments differ in 'alt_index' between route_a and route_b."""
        diffs = 0
        for seg_a, seg_b in zip(route_a["segments"], route_b["segments"]):
            if seg_a["alt_index"] != seg_b["alt_index"]:
                diffs += 1
        return diffs

    # 1) Try to find any routes that differ from best_route in >=2 segments
    valid_alts = []
    for candidate in full_routes[1:]:
        if count_segment_diffs(best_route, candidate) >= 2:
            valid_alts.append(candidate)

    # 2) If none found, fallback to the next best 2 overall
    if not valid_alts:
        other_alts = full_routes[1:3]
    else:
        # otherwise, take up to 2 from the valid set
        other_alts = valid_alts[:2]

    # Store best route in DB (use geometry of first segment or combine them as you wish)
    route_id = str(uuid.uuid4())
    best_distance = best_route["total_distance_m"]
    best_duration = best_route["total_duration_s"]
    best_geometry = best_route["segments"][0]["geometry"]

    new_route = Route(
        id=route_id,
        user_id=data.get("user_id"),
        origin=json.dumps(data["origin"]),
        destination=json.dumps(data["destination"]),
        preferences=str(preferences),
        details="Route created via ORS (multi-stop best route)",
        distance_m=best_distance,
        duration_s=best_duration,
        geometry=json.dumps(best_geometry)
    )
    db.session.add(new_route)

    # Optionally store steps
    for index, step in enumerate(steps_data, start=1):
        new_step = RouteStep(
            route_id=route_id,
            step_order=index,
            location=step.get("location", ""),
            notes=step.get("notes", "")
        )
        db.session.add(new_step)

    db.session.commit()

    # Build final response
    best_response = {
        "id": route_id,
        "origin": data["origin"],
        "destination": data["destination"],
        "preferences": preferences,
        "distance_m": best_distance,
        "duration_s": best_duration,
        "geometry": best_geometry,
        "details": "Best multi-stop route stored in DB"
    }

    # Format alternatives
    alt_responses = []
    for alt in other_alts:
        alt_responses.append({
            "total_distance_m": alt["total_distance_m"],
            "total_duration_s": alt["total_duration_s"],
            "segments": alt["segments"]
        })

    best_response["alternatives"] = alt_responses
    return jsonify(best_response), 201


@app.route("/api/v1/routes", methods=["GET"])
@require_api_key
def list_routes():
    """
    List all routes
    ---
    tags:
      - Routes
    parameters:
      - in: header
        name: X-API-Key
        required: true
        type: string
        default: "MY_RANDOM_API_KEY"
        description: "API key to authorize this request"
      - in: query
        name: limit
        type: integer
        required: false
      - in: query
        name: offset
        type: integer
        required: false
    responses:
      200:
        description: A list of routes
    """

    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", type=int, default=0)

    query = Route.query
    if limit:
        query = query.limit(limit).offset(offset)
    all_routes = query.all()

    results = []
    for r in all_routes:
        steps = [
            {
                "id": step.id,
                "step_order": step.step_order,
                "location": step.location,
                "notes": step.notes
            }
            for step in r.steps
        ]

        route_geometry = json.loads(r.geometry) if r.geometry else None

        results.append({
            "id": r.id,
            "origin": json.loads(r.origin),
            "destination": json.loads(r.destination),
            "preferences": ast.literal_eval(r.preferences),
            "details": r.details,
            "distance_m": r.distance_m,
            "duration_s": r.duration_s,
            "geometry": route_geometry,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "steps": steps
        })
    return jsonify(results), 200


@app.route("/api/v1/routes/<route_id>", methods=["GET"])
@require_api_key
def get_route(route_id):
    """
    Get details of a specific route
    ---
    tags:
      - Routes
    parameters:
      - in: header
        name: X-API-Key
        required: true
        type: string
        default: "MY_RANDOM_API_KEY"
        description: "API key to authorize this request"
      - in: path
        name: route_id
        required: true
        type: string
    responses:
      200:
        description: Details of the route
      404:
        description: Route not found
    """

    route = Route.query.get(route_id)
    if not route:
        return jsonify({"error": "Route not found"}), 404

    origin_dict = json.loads(route.origin)
    destination_dict = json.loads(route.destination)
    route_geometry = json.loads(route.geometry) if route.geometry else None

    return jsonify({
        "id": route.id,
        "origin": origin_dict,
        "destination": destination_dict,
        "preferences": json.loads(route.preferences),
        "details": route.details,
        "distance_m": route.distance_m,
        "duration_s": route.duration_s,
        "geometry": route_geometry,
        "steps": [
            {
                "id": step.id,
                "step_order": step.step_order,
                "location": step.location,
                "notes": step.notes
            }
            for step in route.steps
        ]
    }), 200


@app.route("/api/v1/routes/<route_id>", methods=["DELETE"])
@require_api_key
def delete_route(route_id):
    """
    Delete a route
    ---
    tags:
      - Routes
    parameters:
      - in: header
        name: X-API-Key
        required: true
        type: string
        default: "MY_RANDOM_API_KEY"
        description: "API key to authorize this request"
      - in: path
        name: route_id
        required: true
        type: string
    responses:
      204:
        description: Route deleted
      404:
        description: Route not found
    """

    route = Route.query.get(route_id)
    if not route:
        return jsonify({"error": "Route not found"}), 404

    db.session.delete(route)
    db.session.commit()
    return "", 204


@app.route("/api/v1/routes/<route_id>/steps", methods=["POST"])
@require_api_key
def add_route_step(route_id):
    """
    Add a step (POI) to an existing route
    ---
    tags:
      - Steps
    parameters:
      - in: header
        name: X-API-Key
        required: true
        type: string
        default: "MY_RANDOM_API_KEY"
        description: "API key to authorize this request"
      - in: path
        name: route_id
        required: true
        type: string
      - in: body
        name: body
        required: true
        schema:
          id: CreateStep
          properties:
            step_order:
              type: integer
            location:
              type: string
            notes:
              type: string
    responses:
      201:
        description: Step added
      404:
        description: Route not found
    """
    route = Route.query.get(route_id)
    if not route:
        return jsonify({"error": "Route not found"}), 404

    data = request.get_json()
    new_step = RouteStep(
        route_id=route_id,
        step_order=data.get("step_order", 1),
        location=data.get("location", ""),
        notes=data.get("notes", "")
    )
    db.session.add(new_step)
    db.session.commit()

    return jsonify({"message": "Step added", "step_id": new_step.id}), 201
  

@app.route("/")
def home():
    return redirect(url_for("apidocs", _external=True))

@app.route("/apidocs/")
def apidocs():
    return "<h1>API Documentation</h1><p>Your API docs go here.</p>"


if __name__ == "__main__":
    app.run(debug=True, port=5000)
