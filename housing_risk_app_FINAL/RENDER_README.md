# Render setup

Python: 3.11.11

Build:
python -m pip install --upgrade pip setuptools wheel && python -m pip install --only-binary=:all: -r requirements.txt

Start:
gunicorn app:app --bind 0.0.0.0:$PORT

No environment variables are required.
