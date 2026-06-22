"""
bitacora_server.py — Flask server para Bitácora del Tiempo
Endpoints: POST /generate_daily_batch, POST /generate_single, GET /health
Deploy: Render.com (Free Web Service)
"""

import os
import json
import logging
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from script_writer import generate_script_and_metadata
from image_generator import get_historical_image
from voice_generator import generate_voice
from video_generator import create_short_video
from youtube_uploader import upload_to_youtube

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/tmp/bitacora")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _run_pipeline(event_date=None):
    """Ejecuta el pipeline completo para un Short."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    work_dir = os.path.join(OUTPUT_DIR, ts)
    os.makedirs(work_dir, exist_ok=True)
    log.info(f"[{ts}] Iniciando pipeline")

    script_data = generate_script_and_metadata(event_date=event_date)
    log.info(f"[{ts}] Guion OK: {script_data['title'][:60]}")

    image_path = get_historical_image(
        query=script_data.get("image_query", script_data["title"]),
        year=script_data.get("year"),
        work_dir=work_dir,
    )
    log.info(f"[{ts}] Imagen OK: {image_path}")

    audio_path = generate_voice(
        text=script_data["narration"],
        output_path=os.path.join(work_dir, "narration.wav"),
    )
    log.info(f"[{ts}] Voz OK: {audio_path}")

    video_path = create_short_video(
        image_path=image_path,
        audio_path=audio_path,
        script_data=script_data,
        output_path=os.path.join(work_dir, "short.mp4"),
    )
    log.info(f"[{ts}] Video OK: {video_path}")

    yt_result = upload_to_youtube(
        video_path=video_path,
        title=script_data["yt_title"],
        description=script_data["yt_description"],
        tags=script_data["tags"],
        thumbnail_path=script_data.get("thumbnail_path"),
    )
    log.info(f"[{ts}] YouTube OK: {yt_result['url']}")

    return {
        "status": "ok",
        "timestamp": ts,
        "title": script_data["title"],
        "year": script_data.get("year"),
        "youtube_url": yt_result["url"],
        "video_id": yt_result["video_id"],
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat(), "version": "2.0.0"})


@app.route("/generate_single", methods=["POST"])
def generate_single():
    body = request.get_json(silent=True) or {}
    try:
        result = _run_pipeline(event_date=body.get("date"))
        return jsonify(result), 200
    except Exception as e:
        log.error(traceback.format_exc())
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/generate_daily_batch", methods=["POST"])
def generate_daily_batch():
    body = request.get_json(silent=True) or {}
    count = int(body.get("count", 10))
    results, errors = [], []
    for i in range(count):
        try:
            log.info(f"Batch {i+1}/{count}")
            results.append(_run_pipeline())
        except Exception as e:
            log.error(traceback.format_exc())
            errors.append({"index": i, "error": str(e)})
    return jsonify({
        "status": "ok",
        "generated": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
