# Render deployment

Use:
Build Command:
`pip install --upgrade pip setuptools wheel && pip install -r requirements.txt`

Start Command:
`gunicorn app:app --bind 0.0.0.0:$PORT`

Python runtime: 3.11.11

The package is a Flask application and the dependencies are kept on versions compatible
with Python 3.11.
