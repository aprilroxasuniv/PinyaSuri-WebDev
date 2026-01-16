from flask import Flask, render_template, request, jsonify
import json
import os
import random
from werkzeug.utils import secure_filename
from datetime import datetime
from ai.dummy_ai import analyze_image

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_FILE = os.path.join(BASE_DIR, "data",  "logs.json")

UPLOAD_FOLDER = "static/uploads"

if not os.path.exists(LOGS_FILE):
    with open(LOGS_FILE, "w") as f:
        json.dump([], f)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def load_logs():
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "r") as f:
            return json.load(f)
    return []

def save_logs(logs):
    with open(LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=4)


@app.route("/api/test-ai")
def test_ai():
    result = analyze_image("static/test.jpg")
    return jsonify(result)

# ================= BASIC PAGES =================

@app.route('/')
def splash():
    return render_template('splash.html')


@app.route('/homepage')
def homepage():
    return render_template('homepage.html')


@app.route('/upload-section')
def upload_section():
    return render_template('upload-section.html')


@app.route('/management-strategies')
def management_strategies():
    selected_affliction = request.args.get("affliction")

    return render_template(
        "management-strategies.html",
        selected_affliction=selected_affliction
    )


# ================= DATA LOGS =================

@app.route("/data-logs")
def data_logs():
    logs = load_logs()

    for log in logs:
        if log["type"] == "upload" and "date" not in log:
            old_dt = datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S")
            log["date"] = old_dt.strftime("%B %d, %Y")
            log["time"] = old_dt.strftime("%H:%M:%S")
            log["timestamp"] = f"{log['date']} {log['time']}"

    save_logs(logs)
    return render_template("data-logs.html", logs=logs)

# ================= DATA LOG ID DETAIL =================
@app.route("/data-log/<log_id>")
def data_log_detail(log_id):
    logs = load_logs()

    log = next((l for l in logs if str(l.get("id")) == str(log_id)), None)

    if not log:
        return "Log not found", 404

    return render_template("data-log-detail.html", log=log)

# ================= API (RASPBERRY PI) =================
# ---------------- ROUTES ---------------- #
@app.route("/api/upload-log", methods=["POST"])
def upload_log():
    try:
        metadata = json.loads(request.form.get("metadata", "{}"))
        images = request.files.getlist("images")

        if not images:
            return jsonify({"error": "No images uploaded."}), 400

        waypoints = []
        healthy_count = 0
        affliction_counter = {}

        for idx, image in enumerate(images):
            filename = secure_filename(image.filename)
            image.save(os.path.join(UPLOAD_FOLDER, filename))

            # 🔁 Dummy AI for now
            affliction = random.choice([
                "Healthy Pineapple",
                "Crown Rot Disease",
                "Fruit Rot Disease",
                "Mealybug Wilt Disease",
                "Root Rot Disease",
                "Multiple Crown Disorder",
                "Fruit Fasciation Disorder"
            ])
            confidence = round(random.uniform(0.85, 0.99), 2)

            if affliction == "Healthy Pineapple":
                healthy_count += 1
            else:
                affliction_counter[affliction] = affliction_counter.get(affliction, 0) + 1

            waypoints.append({
                "waypoint_id": f"WP{idx+1}",
                "image": f"uploads/{filename}",
                "affliction": affliction,
                "confidence": confidence,
                "recommendation": (
                    "No disease detected"
                    if affliction == "Healthy Pineapple"
                    else "Apply appropriate treatment"
                )
            })

        diseased_count = len(images) - healthy_count
        dominant_affliction = (
            max(affliction_counter, key=affliction_counter.get)
            if affliction_counter else "None"
        )

        summary = {
            "total_waypoints": len(images),
            "healthy_count": healthy_count,
            "diseased_count": diseased_count,
            "dominant_affliction": dominant_affliction,
            "overall_risk": (
                "Low" if diseased_count == 0 else
                "Moderate" if diseased_count < len(images)/2 else "High"
            ),
            "flight_status": (
                "Healthy" if diseased_count == 0 else "Attention Needed"
            )
        }

        flight_log = {
            "id": f"FLIGHT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": "flight",
            "date": metadata.get("date", datetime.now().strftime("%B %d, %Y")),
            "start_time": metadata.get("start_time", "N/A"),
            "end_time": metadata.get("end_time", "N/A"),
            "summary": summary,
            "waypoints": waypoints
        }

        logs = load_logs()
        logs.append(flight_log)
        save_logs(logs)

        return jsonify({"message": "Flight log saved successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/save-upload-result", methods=["POST"])
def save_upload_result():
    image = request.files.get("image")

    affliction = request.form.get("affliction", "Unknown")
    recommendation = request.form.get("recommendation", "")

    try:
        confidence = float(request.form.get("confidence", 0))
    except ValueError:
        confidence = 0.0

    now = datetime.now()
    date = now.strftime("%B %d, %Y") 
    time = now.strftime("%H:%M:%S")
    timestamp = f"{date} {time}"

    if not image:
        return jsonify({"message": "No image provided"}), 400

    filename = secure_filename(image.filename)

    # ✅ SAVE IMAGE CORRECTLY
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    image.save(image_path)

    # ✅ RELATIVE PATH FOR HTML
    image_relative_path = f"uploads/{filename}"

    log_entry = {
    "type": "upload",
    "date": date,
    "time": time,
    "image": image_relative_path,

    # ✅ FIXED
    "affliction": affliction,          # string
    "afflictions": [affliction],       # list (for buttons)

    "confidence": confidence,
    "recommendation": recommendation,
    "timestamp": timestamp
}

    # ✅ LOAD → APPEND → SAVE
    logs = load_logs()
    logs.append(log_entry)
    save_logs(logs)

    return jsonify({"message": "Data log saved successfully"}), 201

@app.route("/api/upload-flight-log", methods=["POST"])
def upload_flight_log():
    try:
        metadata = json.loads(request.form.get("metadata", "{}"))
        images = request.files.getlist("images")

        flight_id = metadata.get("flight_id")
        date = metadata.get("date")
        start_time = metadata.get("start_time")
        end_time = metadata.get("end_time")

        if not flight_id or not images:
            return jsonify({"error": "Missing flight_id or images"}), 400

        logs = load_logs()

        waypoints = []
        affliction_counter = {}
        healthy_count = 0

        if preview_image is None:
            preview_image = "images/placeholder.png"


        for idx, img in enumerate(images):
            filename = secure_filename(img.filename)
            img.save(os.path.join(UPLOAD_FOLDER, filename))

            if idx == 0:
                preview_image = f"uploads/{filename}"


            # 🔁 Placeholder AI (replace later)
            affliction = random.choice([
                "Healthy Pineapple",
                "Crown Rot Disease",
                "Fruit Rot Disease",
                "Mealybug Wilt Disease",
                "Root Rot Disease",
                "Multiple Crown Disorder",
                "Fruit Fasciation Disorder"
            ])
            confidence = round(random.uniform(0.85, 0.99), 2)

            recommendation = (
                "No disease detected"
                if affliction == "Healthy Pineapple"
                else "Apply appropriate treatment"
            )

            if affliction == "Healthy Pineapple":
                healthy_count += 1
            else:
                affliction_counter[affliction] = affliction_counter.get(affliction, 0) + 1

            waypoints.append({
                "waypoint_id": f"WP{idx+1}",
                "image": filename,
                "affliction": affliction,
                "confidence": confidence,
                "recommendation": recommendation
            })

        diseased_count = len(images) - healthy_count
        dominant_affliction = (
            max(affliction_counter, key=affliction_counter.get)
            if affliction_counter else "None"
        )

        overall_risk = (
            "Low" if diseased_count == 0 else
            "Moderate" if diseased_count < len(images) / 2 else
            "High"
        )

        flight_status = (
            "Healthy" if diseased_count == 0 else "Attention Needed"
        )

        flight_log = {
            "id": flight_id,
            "type": "flight",
            "date": date,
            "start_time": start_time,
            "end_time": end_time,

            # 👇 NEW: preview image for data-logs page
            "image": preview_image,

            "summary": {
                "total_waypoints": len(images),
                "healthy_count": healthy_count,
                "diseased_count": diseased_count,
                "dominant_affliction": dominant_affliction,
                "overall_risk": overall_risk,
                "flight_status": flight_status
            },
            "waypoints": waypoints
        }

        logs.append(flight_log)
        save_logs(logs)

        return jsonify({
            "status": "success",
            "message": "Flight log uploaded successfully",
            "flight_id": flight_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= RUN SERVER =================

if __name__ == '__main__':
    app.run(host='192.168.1.6', port=5000, debug=True)
