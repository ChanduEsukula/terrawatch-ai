# Upstream provenance and review

- Original repository: https://github.com/SMV09/earth-engine-webgis-python
- Original commit: `2f5e04e87b3963f73c7794befad9acc61fbbffd7` (main when cloned on 2026-10-16).
- Temporary clone: `/private/tmp/terrawatch-upstream.gBoeus/source` (outside this project; not required at runtime).
- Verified source directory: `videos/video12_Google Cloud Run Deployment Cloud Shell, Dockerfile, WebGIS Project Setup/WebGIS-app/`.
- Located by enumerating the checkout, including earlier tutorial versions; did not assume the supplied path.

## Reused files

| Upstream file | TerraWatch file | Changes |
| --- | --- | --- |
| `app.py` | `app.py` | Preserved Flask routes, Landsat collection, RGB/NDVI tiles and mean calculation structure; added lazy initialization, validation, resource bounds, cloud/saturation masking before compositing, safe errors, liveness endpoint and local binding. |
| `config.py` | `config.py` | Replaced Secret Manager initialization with environment configuration and existing local Earth Engine/ADC credentials; validated ROI; capped pixels; serialized initialization. |
| `requirements.txt` | `requirements.in`, `requirements.txt` | Replaced tutorial environment dump with four direct dependencies and a fully pinned resolved runtime set. |
| `Dockerfile` | `Dockerfile` | Python 3.13, non-root user, explicit source copies, no compiler, pinned wheel dependencies, one Gunicorn worker. Local recipe only. |
| `templates/index.html` | `templates/index.html` | Preserved Leaflet map, OSM basemap and RGB/NDVI layer controls; TerraWatch title, configurable ROI bounds, request feedback, safe text rendering, Leaflet integrity checks and attribution link. |
| repository `LICENSE` | `LICENSES/upstream-MIT.txt` | Exact upstream MIT license retained, including `Copyright (c) 2026 SMV09`. |

New files include README, review/verification notes, offline tests, environment example and ignore rules. No tutorial setup/billing/deployment scripts, credential files, prior video copies or unrelated assets were imported.

## Inspection findings and resolution

- **Credentials:** No actual private key, access token or password found in the five selected source areas. Upstream uses `YOUR CLOUD PROJECT ID` and secret name `gee-secret`; both were removed. The original default ROI is in Kerala, India and is now configurable. This review concerns the selected source, not a complete audit of upstream Git history.
- **Startup:** `SECRET_ID = "gee-secret" // Secret Manager Name` is invalid Python syntax. Import-time initialization also requires Google Secret Manager and would prevent the home page from starting without access. Replaced with lazy initialization on valid analysis requests; missing configuration returns HTTP 503.
- **Dependencies:** Upstream duplicates Gunicorn (pinned 21.2.0 plus unpinned), leaves Flask-Limiter and Secret Manager unpinned, and freezes numerous older transitive packages. No package was declared formally deprecated based solely on age. Removed unnecessary direct Secret Manager dependency; upgraded Earth Engine and Gunicorn to current PyPI versions checked on the review date. PyPI lists Python >=3.10 for the chosen EE/Limiter/Gunicorn versions. The package named `Deprecated` in the lockfile is a legitimate transitive utility used by `limits`, not a deprecation finding.
- **Configuration:** Added explicit `EE_PROJECT`, optional bounded `EE_ROI`, and documented existing user credentials or ADC. No credentials are acquired automatically, no services are enabled, no project is created.
- **Security/resource use:** Upstream returns raw exception details and renders API values with `innerHTML`, permits unbounded date spans and `maxPixels=1e13`, and binds the local server to all interfaces. Added generic upstream error responses, `textContent`, date/ROI/pixel bounds, headers, JSON rate-limit errors and loopback binding. Rate limiting remains in memory and per process; this unauthenticated baseline is intended for local use only.
- **Analysis behavior:** Landsat scaling now runs per scene before median compositing. QA masking removes fill/cloud/shadow/cirrus/dilated cloud and saturated pixels. An NDVI expression retains negative reflectance pixels that `normalizedDifference` would mask. Empty collections and all-masked output return HTTP 404. These calculations have offline contract tests but no live scientific validation yet.
- **Container:** Upstream runs as root, adds an unnecessary compiler, copies the whole context and fixes port 8080 despite claiming environment port support. The local recipe now runs as a non-root user and explicitly listens on 8080; it has not been built or deployed.

## License attribution

Upstream is MIT licensed at the exact commit above. Its complete copyright and permission notice is preserved verbatim in `LICENSES/upstream-MIT.txt`; distribute that file with reused source and substantial derivatives. TerraWatch's original root `LICENSE` remains unchanged (Copyright 2026 ChanduEsukula). The container copies both license notices and this provenance file.

## Reference documentation

- Earth Engine local authentication/project selection: https://developers.google.com/earth-engine/guides/auth
- Landsat 8 collection, scale factors and QA bands: https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2
- Dependency release metadata: https://pypi.org/project/earthengine-api/, https://pypi.org/project/Flask/, https://pypi.org/project/Flask-Limiter/, https://pypi.org/project/gunicorn/
