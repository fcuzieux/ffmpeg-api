import asyncio
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

app = FastAPI(title="ffmpeg-api")

MEDIA_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
    "flac": "audio/flac",
}

CODECS = {
    "wav": ["-c:a", "pcm_s16le"],
    "mp3": ["-c:a", "libmp3lame", "-q:a", "4"],
    "ogg": ["-c:a", "libvorbis", "-q:a", "4"],
    "m4a": ["-c:a", "aac", "-b:a", "128k"],
    "flac": ["-c:a", "flac"],
}

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
_semaphore = asyncio.Semaphore(4)


@app.get("/health")
async def health():
    return {"status": "ok", "ffmpeg": FFMPEG}


@app.post("/convert")
async def convert(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    format: str = Query("wav"),
    sample_rate: int = Query(16000, ge=8000, le=192000),
    channels: int = Query(1, ge=1, le=8),
):
    if format not in MEDIA_TYPES:
        raise HTTPException(400, f"format non supporté: {format} (attendu: {sorted(MEDIA_TYPES)})")

    suffix = Path(file.filename or "input").suffix or ".bin"
    job_id = uuid.uuid4().hex
    workdir = Path(tempfile.gettempdir()) / job_id
    workdir.mkdir()
    input_path = workdir / f"input{suffix}"
    output_path = workdir / f"output.{format}"

    data = await file.read()
    if not data:
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(400, "fichier vide")
    input_path.write_bytes(data)

    async with _semaphore:
        proc = await asyncio.create_subprocess_exec(
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            *CODECS[format],
            str(output_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

    if proc.returncode != 0 or not output_path.exists():
        detail = stderr.decode(errors="replace").strip() or "ffmpeg a échoué"
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(422, f"conversion échouée: {detail}")

    background_tasks.add_task(shutil.rmtree, workdir, True)
    return FileResponse(
        output_path,
        media_type=MEDIA_TYPES[format],
        filename=f"{Path(file.filename or 'output').stem}.{format}",
    )
