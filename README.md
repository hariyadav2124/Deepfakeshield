# DEEPFAKEshield

A Flask-based API for deepfake detection and reporting.

## Features
- Upload images/videos for deepfake analysis
- RESTful API endpoints
- Admin dashboard for results and reports
- User authentication (login/register)
- Report generation

## Project Structure
```
DEEPFAKEshiled/
├── app.py                # Main Flask app entry point
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── api/
│   ├── __init__.py
│   └── deepfake_api.py   # API logic
├── database/
│   └── db.sql            # Database schema
├── deepfake/
│   ├── pyvenv.cfg
│   └── ...               # Virtual environment files
├── reports/              # Generated reports
├── static/
│   ├── css/
│   ├── js/
│   └── uploads/          # Uploaded files
├── templates/            # HTML templates
```

## Setup & Installation
1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd DEEPFAKE_API
   ```
2. **Create and activate a virtual environment**
   ```bash
   python -m venv deepfake
   # On Windows
   deepfake\Scripts\activate
   # On Unix/Mac
   source deepfake/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application**
   ```bash
   python app.py
   ```

## Usage
- Access the web interface at `http://localhost:5000/`
- Use API endpoints as documented in `api/deepfake_api.py`

## Folder Details
- `api/`: API logic and endpoints
- `database/`: Database schema and migrations
- `deepfake/`: Virtual environment (not required to commit)
- `reports/`: Generated reports
- `static/`: Static files (CSS, JS, uploads)
- `templates/`: HTML templates

## License
