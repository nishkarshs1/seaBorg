import requests
import json

queries = [
    "What is the temperature at 500m depth in the Indian Ocean?",
    "Where are the ARGO floats located?",
    "Show me salinity trend over time",
    "Tell me about ocean conditions near India"
]

for q in queries:
    print(f"\n--- Query: {q} ---")
    try:
        resp = requests.post("http://localhost:8001/api/chat", json={"message": q})
        print("Status:", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            print("Response:", json.dumps(data, indent=2))
        else:
            print("Error text:", resp.text)
    except Exception as e:
        print("Failed:", e)
