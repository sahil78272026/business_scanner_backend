"""
Entry point — run with: python run.py
Or use: uvicorn app.main:app --reload --port 5000
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=5000, reload=True)
