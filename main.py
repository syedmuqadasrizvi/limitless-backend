from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import subprocess
import imageio_ffmpeg
import json
import uuid

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

class InfoRequest(BaseModel):
    youtube_url: str

@app.get("/")
def home():
    return {"status": "running", "message": "Limitless Clipping Engine is Active"}

# Fetch Dynamic Title, Thumbnail, and Duration
@app.post("/api/fetch-info")
def fetch_info(data: InfoRequest):
    try:
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=android,ios",
            data.youtube_url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            info = json.loads(res.stdout)
            dur_sec = info.get("duration", 0)
            m, s = divmod(dur_sec, 60)
            h, m = divmod(m, 60)
            dur_str = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"
            return {
                "success": True,
                "title": info.get("title", "YouTube Video"),
                "thumbnail": info.get("thumbnail", ""),
                "uploader": info.get("uploader", "YouTube Channel"),
                "duration": dur_str
            }
    except Exception as e:
        print("Fetch info error:", str(e))
        
    return {
        "success": False,
        "title": "YouTube Video",
        "thumbnail": "",
        "uploader": "YouTube Channel",
        "duration": "N/A"
    }

# Render Clips directly from Direct Stream (No Bunny Fallback)
@app.post("/api/generate-clips")
def generate_clips(data: ClipRequest):
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        # 1. Get direct stream URL using yt-dlp
        stream_cmd = [
            "yt-dlp",
            "-g",
            "-f", "b[ext=mp4]/w[ext=mp4]/best",
            "--extractor-args", "youtube:player_client=android,ios",
            data.youtube_url
        ]
        res = subprocess.run(stream_cmd, capture_output=True, text=True)
        
        if res.returncode != 0 or not res.stdout.strip():
            raise Exception("Could not fetch YouTube stream URL. Check link.")
            
        stream_url = res.stdout.strip().split("\n")[0]
        generated_clips = []
        
        # Respect user's EXACT clip_count
        for i in range(1, data.clip_count + 1):
            start_sec = (i - 1) * (data.duration + 5)
            unique_id = uuid.uuid4().hex[:6]
            output_filename = f"clip_{i}_{unique_id}.mp4"
            output_filepath = os.path.join(OUTPUT_DIR, output_filename)
            
            vf_filter = "crop=ih*(9/16):ih" if data.aspect_ratio == "9:16" else "scale=1280:720"
            
            # 2. FFmpeg directly cuts from stream without local file download block
            ffmpeg_cmd = [
                ffmpeg_exe, "-y",
                "-ss", str(start_sec),
                "-i", stream_url,
                "-t", str(data.duration),
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-c:a", "aac",
                output_filepath
            ]
            
            ff_res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if ff_res.returncode == 0 and os.path.exists(output_filepath):
                clip_url = f"https://limitless-clipping-api.onrender.com/clips/{output_filename}"
            else:
                raise Exception(f"FFmpeg rendering failed for clip {i}")

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
        print("Backend error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
