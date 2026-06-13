import os
import uvicorn

if __name__ == "__main__":
    # Safely get the PORT environment variable natively in Python
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting SeaBorg backend on port {port}...")
    
    # Run the FastAPI app
    uvicorn.run("api.main:app", host="0.0.0.0", port=port)
