from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import subprocess
import imageio_ffmpeg

app = FastAPI(title="Limitless Clipping Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "static_clips"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app.mount("/clips", StaticFiles(directory=OUTPUT_DIR), name="clips")

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
    return {"status": "running", "message": "Limitless Clipping Engine is Active"}

@app.post("/api/generate-clips")
def generate_clips(data: ClipRequest):
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        raw_video_path = os.path.join(OUTPUT_DIR, "source_video.mp4")
        
        # Extractor args to bypass YouTube bot block on Render IPs
        yt_cmd = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=android,ios",
            "-f", "b[ext=mp4]/w[ext=mp4]/best",
            "-o", raw_video_path,
            "--force-overwrites",
            "--no-playlist",
            data.youtube_url
        ]
        
        res = subprocess.run(yt_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise Exception(f"yt-dlp download failed: {res.stderr[:200]}")

        generated_clips = []
        
        count_to_process = min(data.clip_count, 3)
        for i in range(1, count_to_process + 1):
            start_time = (i - 1) * data.duration
            output_filename = f"clip_{i}.mp4"
            output_filepath = os.path.join(OUTPUT_DIR, output_filename)
            
            vf_filter = "crop=ih*(9/16):ih" if data.aspect_ratio == "9:16" else "scale=1280:720"
                
            ffmpeg_cmd = [
                ffmpeg_exe, "-y",
                "-ss", str(start_time),
                "-i", raw_video_path,
                "-t", str(data.duration),
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-c:a", "aac",
                output_filepath
            ]
            subprocess.run(ffmpeg_cmd, check=True)

            clip_url = f"https://limitless-clipping-api.onrender.com/clips/{output_filename}"
            
            generated_clips.append({
                "id": i,
                "title": f"Limitless Clip #{i}",
                "duration": f"{data.duration}s",
                "ratio": data.aspect_ratio,
                "download_url": clip_url
            })

        return {
            "success": True,
            "count": len(generated_clips),
            "clips": generated_clips
        }

    except Exception as e:
        print("Error details:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
