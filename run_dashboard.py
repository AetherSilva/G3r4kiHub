"""
Entry point for running the admin dashboard only
Use this to run just the web interface without the bot
"""

import sys
import uvicorn
from config import settings

if __name__ == "__main__":
    print("🚀 Starting G3r4kiHub Admin Dashboard")
    print(f"📊 Access at http://localhost:{8001}")
    print("Press Ctrl+C to stop")
    
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8001,
        reload=not settings.debug_mode,
        log_level=settings.log_level.lower()
    )
