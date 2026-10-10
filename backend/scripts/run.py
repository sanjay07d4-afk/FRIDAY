import sys
import os
import uvicorn

# Add backend root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

if __name__ == "__main__":
    print(f"Starting FRIDAY AI Backend on http://{settings.HOST}:{settings.PORT} (Timezone: {settings.TIMEZONE})...")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
