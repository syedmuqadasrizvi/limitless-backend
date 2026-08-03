from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Limitless Clipping Engine")

# Lovable UI se connection allow karne ke liye settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClipRequest(BaseModel):
    youtube_url: str
    clip_count: int = 5
    duration: int = 30
    aspect_ratio: str = "9:16"
    include_gameplay: bool = False
    gameplay_preset: str = "Subway Surfers"
    include_music: bool = False

@app.get("/")
def home():
    return {"status": "Limitless Clipping API is Running"}

@app.post("/api/generate-clips")
def generate_clips(data: ClipRequest):
    print(f"URL: {data.youtube_url}")
    return {
        "success": True,
        "message": "Processing started",
        "clips": [
            {
                "id": 1,
                "title": "Clip #1",
                "duration": f"{data.duration}s",
                "ratio": data.aspect_ratio,
                "download_url": "https://www.w3schools.com/html/mov_bbb.mp4"
            }
        ]
    }