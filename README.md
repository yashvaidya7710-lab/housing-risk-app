# Housing Instability Risk Compass — India (Render-ready)

Estimates the probability that a household is at risk of housing instability in the next 12 months, framed as a Design-Thinking journey (Empathize -> Define -> Ideate -> Prototype -> Test).

## Files
- `app.py` — Flask app; trains the RandomForest model from embedded, documented risk-factor data at startup (no external model file needed)
- `templates/index.html`, `static/style.css`, `static/script.js` — frontend
- `requirements.txt`, `Procfile` — deploy config

## Deploy to Render
1. Put all files at the ROOT of a GitHub repo (app.py and requirements.txt visible at top level).
2. Push to GitHub.
3. Render -> New -> Web Service -> connect the repo.
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Deploy. First boot is ~10-20s slower because the model trains at startup.

## Local test
```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Important
This is an educational / awareness tool trained on a documented-risk-factor synthetic dataset (see the Colab notebook for the literature basis), calibrated to Indian urban rent/income ranges. It is **not** validated against real case outcomes and must not be used, as-is, to make housing, welfare, or eligibility decisions about real people. For that, partner with your local ULB / housing authority / an NGO like ActionAid, and have the model validated and audited on real, consented case data before any deployment that affects people.