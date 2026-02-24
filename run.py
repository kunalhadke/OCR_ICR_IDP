"""
Quick-start script: python run.py
All settings configurable via environment variables (see backend/config.py).
"""
import uvicorn
from backend.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
