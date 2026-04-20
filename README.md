# Simple Flask Notes App

This is a minimal example of a Flask application with an SQLite database and a small HTML/CSS frontend.

Setup

1. Create and activate a virtual environment (recommended):

   python -m venv .venv
   .\.venv\Scripts\activate

2. Install requirements:

   pip install -r requirements.txt

3. Initialize the SQLite database:

   python init_db.py

4. Run the app:

   python app.py

By default the app listens only on localhost (127.0.0.1). To host
the app on your LAN so other devices can access it, set HOST to
0.0.0.0 and optionally set PORT. Example (Windows cmd.exe):

   set HOST=0.0.0.0
   set PORT=5000
   python app.py

Or one-liner (PowerShell):

   $env:HOST='0.0.0.0'; $env:PORT='5000'; python app.py

Then open http://<your-machine-ip>:5000/ from other devices on the same network.

For production deployments use a WSGI server (gunicorn/uwsgi) behind a
reverse proxy; the above is intended for simple LAN hosting during
development or demos.
