import csv
import io
import os
import sys
import threading
import uuid
from fractions import Fraction
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from wuggy import WuggyGenerator
from wuggy.generators.wuggygenerator import _language_plugins_base_dir, _BUNDLED_PLUGINS_DIR

# When running as a PyInstaller bundle, Flask can't locate templates and
# static files relative to the module file. Point it at sys._MEIPASS instead.
if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS
    app = Flask(__name__,
                template_folder=os.path.join(_base, 'wuggy', 'gui', 'templates'),
                static_folder=os.path.join(_base, 'wuggy', 'gui', 'static'))
else:
    app = Flask(__name__)

generator = WuggyGenerator()
generator_lock = threading.Lock()
jobs = {}


def serialize_value(v):
    if isinstance(v, Fraction):
        return str(v)
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, dict):
        return {k: serialize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [serialize_value(item) for item in v]
    return v


def serialize_match(match):
    return {k: serialize_value(v) for k, v in match.items()}


def compute_deviation_columns(match):
    tf = match.get("difference_statistics", {}).get("transition_frequencies", {})
    if not tf:
        return {"max_deviation": None, "summed_deviation": None, "max_deviation_position": None}
    abs_vals = {k: abs(v) for k, v in tf.items()}
    max_pos = max(abs_vals, key=abs_vals.get)
    return {
        "max_deviation": abs_vals[max_pos],
        "summed_deviation": sum(abs_vals.values()),
        "max_deviation_position": max_pos,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/languages", methods=["GET"])
def get_languages():
    with generator_lock:
        available = list(generator.supported_official_language_plugin_names)
        loaded = list(generator.bigramchains.keys())
        current = getattr(generator, "language_plugin_name", None)

    user_dir = _language_plugins_base_dir()
    bundled = set()
    if _BUNDLED_PLUGINS_DIR is not None and _BUNDLED_PLUGINS_DIR.exists():
        bundled = {p.name for p in _BUNDLED_PLUGINS_DIR.iterdir() if p.is_dir()}
    downloaded = {p.name for p in user_dir.iterdir() if p.is_dir()} if user_dir.exists() else set()

    # per-language availability: "bundled", "downloaded", or "remote"
    availability = {}
    for lang in available:
        if lang in downloaded:
            availability[lang] = "downloaded"
        elif lang in bundled:
            availability[lang] = "bundled"
        else:
            availability[lang] = "remote"

    return jsonify({
        "available": available,
        "loaded": loaded,
        "current": current,
        "availability": availability,
    })


@app.route("/api/language-info", methods=["GET"])
def language_info():
    with generator_lock:
        plugin = getattr(generator, "language_plugin", None)
        data_path = getattr(generator, "language_plugin_data_path", None)
        name = getattr(generator, "language_plugin_name", None)
        if plugin is None or name is None:
            return jsonify({"error": "No language loaded"}), 400
        return jsonify({
            "name": name,
            "data_path": str(data_path) if data_path else None,
            "bigram_data": getattr(plugin, "default_data", None),
            "word_lexicon": getattr(plugin, "default_word_lexicon", None),
            "neighbor_lexicon": getattr(plugin, "default_neighbor_lexicon", None),
            "lookup_lexicon": getattr(plugin, "default_lookup_lexicon", None),
        })


@app.route("/api/load-language", methods=["POST"])
def load_language():
    data = request.get_json()
    name = data.get("language")
    if not name:
        return jsonify({"error": "No language specified"}), 400

    def do_load():
        with generator_lock:
            plugins_dir = os.path.join(
                Path(__file__).parents[1], "plugins", "language_data", name
            )
            if not os.path.exists(plugins_dir):
                generator.download_language_plugin(name, auto_download=True)
            generator.load(name)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "type": "load", "language": name}

    def run():
        try:
            do_load()
            jobs[job_id]["status"] = "done"
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/load-language/<job_id>", methods=["GET"])
def load_language_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/syllabify", methods=["POST"])
def syllabify():
    data = request.get_json()
    words = data.get("words", [])
    results = []
    with generator_lock:
        for word in words:
            seg = generator.lookup_reference_segments(word)
            results.append({"word": word, "syllables": seg})
    return jsonify({"results": results})


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    words = data.get("words", [])
    settings = data.get("settings", {})
    syllabifications = data.get("syllabifications", {})

    if not words:
        return jsonify({"error": "No words provided"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "type": "generate",
        "total": len(words),
        "completed": 0,
        "current_word": None,
        "results": [],
    }

    def run():
        try:
            ncandidates = settings.get("ncandidates", 10)
            max_time = settings.get("max_search_time", 10)
            match_segment_length = settings.get("match_subsyllabic_segment_length", True)
            match_letter_length = settings.get("match_letter_length", True)
            concentric = settings.get("concentric_search", True)
            output_mode = settings.get("output_mode", "plain")

            overlap_num = settings.get("overlap_numerator", 2)
            overlap_den = settings.get("overlap_denominator", 3)
            if overlap_num is not None and overlap_den is not None:
                overlap_ratio = Fraction(int(overlap_num), int(overlap_den))
            else:
                overlap_ratio = None

            with generator_lock:
                for word in words:
                    jobs[job_id]["current_word"] = word
                    try:
                        # Inject user-provided syllabification so out-of-lexicon
                        # words (and manual overrides) can be generated.
                        custom_syl = syllabifications.get(word)
                        if custom_syl:
                            generator.lookup_lexicon[word] = custom_syl
                        matches = generator.generate_gui(
                            [word],
                            ncandidates_per_sequence=ncandidates,
                            max_search_time_per_sequence=max_time,
                            subsyllabic_segment_overlap_ratio=overlap_ratio,
                            match_subsyllabic_segment_length=match_segment_length,
                            match_letter_length=match_letter_length,
                            output_mode=output_mode,
                            concentric_search=concentric,
                            output_type=settings.get("output_type", "pseudowords"),
                        )
                        for m in matches:
                            result = serialize_match(m)
                            result.update(compute_deviation_columns(m))
                            jobs[job_id]["results"].append(result)
                    except Exception as e:
                        jobs[job_id]["results"].append({
                            "word": word,
                            "error": str(e),
                        })
                    jobs[job_id]["completed"] += 1

            jobs[job_id]["status"] = "done"
            jobs[job_id]["current_word"] = None
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/generate/<job_id>", methods=["GET"])
def generate_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    try:
        content = f.read().decode("utf-8")
    except UnicodeDecodeError:
        return jsonify({"error": "File must be UTF-8 encoded text"}), 400
    rows = []
    warnings = []
    for i, line in enumerate(content.strip().split("\n"), 1):
        if not line.strip():
            continue
        parts = line.strip().split("\t")
        if len(parts) > 3:
            warnings.append(f"Line {i} has {len(parts)} columns; only first 3 (Word, Syllables, Matching Expression) are used.")
        row = {"word": parts[0] if parts else ""}
        if len(parts) > 1:
            row["syllables"] = parts[1]
        if len(parts) > 2:
            row["matching_expression"] = parts[2]
        rows.append(row)
    return jsonify({"rows": rows, "warnings": warnings})


@app.route("/api/open-url", methods=["POST"])
def open_url():
    import webbrowser
    data = request.get_json()
    url = data.get("url", "")
    if url.startswith("https://"):
        webbrowser.open(url)
    return jsonify({"ok": True})


@app.route("/api/export-csv", methods=["POST"])
def export_csv():
    data = request.get_json()
    results = data.get("results", [])
    columns = data.get("columns", [])

    if not results:
        return jsonify({"error": "No results to export"}), 400

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in results:
        flat = {}
        for col in columns:
            val = row.get(col, "")
            if isinstance(val, dict):
                for k, v in val.items():
                    flat[f"{col}_{k}"] = v
            else:
                flat[col] = val
        writer.writerow(flat)

    output.seek(0)
    buf = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="wuggy_results.csv")
