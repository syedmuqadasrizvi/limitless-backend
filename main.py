from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import subprocess
import imageio_ffmpeg

app = FastAPI(title="Limitless Clipping Engine")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directory for processed video clips
OUTPUT_DIR = "static_clips"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Serve generated clips as public static files
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
        
        # 1. Download YouTube Video via yt-dlp
        yt_cmd = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", raw_video_path,
            "--force-overwrites",
            data.youtube_url
        ]
        subprocess.run(yt_cmd, check=True)

        generated_clips = []
        
        # 2. Slice video into requested duration and ratio
        for i in range(1, data.clip_count + 1):
            start_time = (i - 1) * data.duration
            output_filename = f"clip_{i}_{data.duration}s.mp4"
            output_filepath = os.path.join(OUTPUT_DIR, output_filename)
            
            # Aspect ratio crop filter
            if data.aspect_ratio == "9:16":
                vf_filter = "crop=ih*(9/16):ih"
            else:
                vf_filter = "scale=1920:1080"
                
            ffmpeg_cmd = [
                ffmpeg_exe, "-y",
                "-ss", str(start_time),
                "-i", raw_video_path,
                "-t", str(data.duration),
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-c:a", "aac",
                output_filepath
            ]
            subprocess.run(ffmpeg_cmd, check=True)

            # Construct public download link
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
        raise HTTPException(status_code=500, detail=str(e))
