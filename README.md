# Deluzex Backend

This is a FastAPI project with a basic health API.

## Project Structure

- `app/main.py`: The entry point for the FastAPI application.
- `app/api/endpoints/health.py`: Contains the `/health` API endpoint.
- `app/core/config.py`: Contains the application configuration.
- `requirements.txt`: Python dependencies.

## Running Locally

1. Create a virtual environment: `python -m venv venv`
2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `uvicorn app.main:app --reload`