# TerraWatch AI

Local Flask + Leaflet baseline adapted from [SMV09's Earth Engine WebGIS tutorial](https://github.com/SMV09/earth-engine-webgis-python). Explore Landsat 8 RGB imagery and mean NDVI for a configured rectangle, with switchable RGB/NDVI map layers.

## Local setup

Use Python 3.13 (verified with 3.13.7 on macOS arm64). Run from the repository root:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements.txt
python app.py
```

Open http://127.0.0.1:8080. The map page and `/healthz` start without Google credentials. Leaflet assets and OpenStreetMap tiles require internet access; they are not bundled for offline mapping. Satellite requests require Earth Engine authentication. Stop with Ctrl+C.

`requirements.in` records reviewed direct dependencies; `requirements.txt` pins all 41 resolved runtime dependencies. The lock was resolved on Python 3.13/macOS arm64; other platforms and the Docker image have not been executed. Re-resolve and review intentionally when changing Python/platform or updating dependencies. Normal installation uses the pinned file.

## Earth Engine configuration

No project, credential or paid service is provisioned by this application. For live analysis, use an **existing** project already registered for Earth Engine and an account with appropriate access. Follow [Google's authentication instructions](https://developers.google.com/earth-engine/guides/auth). If you do not already have access, the baseline can still run locally; leave analysis blocked.

```sh
cp .env.example .env
# Edit .env: set EE_PROJECT to your existing project ID.
set -a
source .env
set +a
# Only if you need to authorize your own account interactively:
earthengine authenticate
python app.py
```

`.env` is loaded by the shell, not automatically by Python. Restart the server after configuration changes. Existing Earth Engine user credentials or Application Default Credentials (ADC) are used by `ee.Initialize(project=...)`. If you already use ADC, no additional login is needed. `GOOGLE_APPLICATION_CREDENTIALS` may reference an existing credential file outside the repository; never put keys or tokens in source control.

Optional `EE_ROI` is a JSON array `[west,south,east,north]` using longitude/latitude degrees. The default is `[75.8,10.4,76.5,11.0]`. Bounds must be ordered and cover at most one square degree; antimeridian crossing is unsupported. Scale is 30 m and maximum pixels are 10 million. Invalid ROI configuration fails startup with a configuration error.

Select ISO dates from 2013-03-18 through today; the end is exclusive and must be later than start by at most 366 days. The backend selects Landsat 8 Collection 2 Tier 1 Level 2 scenes with <20% scene cloud cover, masks QA flags, scales optical reflectance, composites the median, and computes NDVI over the rectangle. This is a tutorial baseline, not a validated environmental monitoring product.

## Checks

```sh
source .venv/bin/activate
python -m unittest discover -s tests -v
python -m pip check
python -m compileall -q app.py config.py tests
gunicorn --check-config app:app
```

The 11 offline tests mock Earth Engine responses; they do not demonstrate real Google access or satellite results. `/healthz` checks local liveness only and returns `earth_engine: not_checked`. Valid `/get_stats` requests return 503 when project/authentication is unavailable, 404 for no data, and 502 for unexpected Earth Engine failures. Invalid dates return 400, rate limits return 429.

An alternative local server is `gunicorn --bind 127.0.0.1:8080 --workers 1 --threads 4 --timeout 120 app:app`. This app has no user authentication and uses in-memory rate limits (50/hour overall, plus 10/minute for analysis); keep it local. EE request timeouts are 30 seconds with one retry after initialization; first credential/discovery initialization uses SDK defaults. Map tile URLs are transient and should not be treated as a persistent export.

The Dockerfile is an unbuilt local recipe with a fixed internal port 8080. No Google Cloud deployment or service-enablement workflow is included.

See [UPSTREAM.md](UPSTREAM.md) for provenance, inspection findings and modifications, [VERIFICATION.md](VERIFICATION.md) for actual execution results, and [the upstream MIT notice](LICENSES/upstream-MIT.txt) for attribution alongside the root [LICENSE](LICENSE).
