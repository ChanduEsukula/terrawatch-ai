"""TerraWatch baseline, adapted from SMV09's MIT-licensed WebGIS tutorial."""
from datetime import date
import os

import ee
from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import (EarthEngineUnavailable, MAX_DATE_DAYS, MAX_PIXELS,
                    ROI_COORDS, SCALE, get_roi, initialize_ee)

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=1024, RATELIMIT_STORAGE_URI="memory://")
limiter = Limiter(get_remote_address, app=app, default_limits=["50 per hour"])


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index():
    return render_template("index.html", roi=ROI_COORDS)


@app.get("/healthz")
@limiter.exempt
def health():
    # Liveness only: deliberately does not claim Earth Engine readiness.
    return jsonify(status="ok", earth_engine="not_checked")


def get_landsat(start, end, roi):
    return (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .filterBounds(roi).filterDate(start, end)
            .filter(ee.Filter.lt("CLOUD_COVER", 20)))


def scale(img):
    # Mask fill, dilated cloud, cirrus, cloud, shadow and saturated pixels.
    mask = img.select("QA_PIXEL").bitwiseAnd(31).eq(0)
    optical = img.select("SR_B.*").multiply(0.0000275).add(-0.2)
    return img.addBands(optical, None, True).updateMask(mask).updateMask(img.select("QA_RADSAT").eq(0))


def validate_dates(start, end):
    try:
        first, last = date.fromisoformat(start or ""), date.fromisoformat(end or "")
    except ValueError:
        raise ValueError("Provide start and end in YYYY-MM-DD format") from None
    if first.isoformat() != start or last.isoformat() != end:
        raise ValueError("Provide start and end in YYYY-MM-DD format")
    if first < date(2013, 3, 18) or last > date.today() or not 0 < (last-first).days <= MAX_DATE_DAYS:
        raise ValueError("Use Landsat 8 dates from 2013-03-18 through today; end must follow start by at most 366 days")
    return start, end


@app.get("/get_stats")
@limiter.limit("10 per minute")
def get_stats():
    try:
        start, end = validate_dates(request.args.get("start"), request.args.get("end"))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    try:
        initialize_ee()
        roi = get_roi()
        collection = get_landsat(start, end, roi)
        if collection.size().getInfo() == 0:
            return jsonify(error="No Landsat scenes found for these dates and ROI"), 404
        image = collection.map(scale).median().clip(roi)
        # expression preserves valid negative reflectances, unlike normalizedDifference.
        ndvi = image.expression("(nir - red) / (nir + red)", {
            "nir": image.select("SR_B5"), "red": image.select("SR_B4")
        }).rename("ndvi")
        ndvi_value = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=roi, scale=SCALE,
            maxPixels=MAX_PIXELS).get("ndvi").getInfo()
        if ndvi_value is None:
            return jsonify(error="No valid pixels remain after cloud masking"), 404
        rgb_map = image.getMapId({"bands": ["SR_B4", "SR_B3", "SR_B2"], "min": 0, "max": 0.3})
        ndvi_map = ndvi.getMapId({"min": -1, "max": 1, "palette": ["brown", "yellow", "green"]})
        return jsonify(start=start, end=end, mean_ndvi=ndvi_value,
                       rgb=rgb_map["tile_fetcher"].url_format,
                       ndvi=ndvi_map["tile_fetcher"].url_format)
    except EarthEngineUnavailable as exc:
        return jsonify(error=str(exc)), 503
    except Exception:
        app.logger.exception("Earth Engine analysis failed")
        return jsonify(error="Earth Engine analysis failed; check server logs"), 502


@app.errorhandler(429)
def rate_limited(error):
    return jsonify(error="Request limit reached; try again later"), 429


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8080")), debug=False)
