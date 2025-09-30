from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import json
import os

app = FastAPI()

# Allow POST CORS from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Load telemetry bundle once (JSON file placed in project root)
try:
    json_path = os.path.join(os.path.dirname(__file__), "q-vercel-latency.json")
    print(">>> Loading telemetry bundle...")
    print(">>> Bundle path:", json_path)
    print(">>> Exists?", os.path.exists(json_path))
    
    with open(json_path, 'r') as f:
        telemetry_data = json.load(f)
    print(f">>> Loaded {len(telemetry_data)} records")
except Exception as e:
    print(f">>> Error loading telemetry data: {e}")
    telemetry_data = []
    
@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/")
async def metrics(request: Request):
    try:
        body = await request.json()
        regions = body.get("regions", [])
        threshold = body.get("threshold_ms", 180)

        if not telemetry_data:
            raise HTTPException(status_code=500, detail="Telemetry data not loaded")

        result = {}
        for region in regions:
            # Filter records for region
            records = [r for r in telemetry_data if r.get("region") == region]
            if not records:
                continue

            latencies = [r.get("latency_ms", 0) for r in records if "latency_ms" in r]
            uptimes = [r.get("uptime_pct", 0) for r in records if "uptime_pct" in r]

            if not latencies or not uptimes:
                continue

            avg_latency = round(float(np.mean(latencies)), 2)
            p95_latency = round(float(np.percentile(latencies, 95)), 2)
            avg_uptime = round(float(np.mean(uptimes)), 2)
            breaches = sum(1 for l in latencies if l > threshold)

            result[region] = {
                "avg_latency": avg_latency,
                "p95_latency": p95_latency,
                "avg_uptime": avg_uptime,
                "breaches": breaches
            }

        return {"regions": result}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
