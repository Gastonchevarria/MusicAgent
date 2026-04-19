import subprocess
import os
import structlog

log = structlog.get_logger()

def convert_wav_to_mp3(wav_path: str) -> str:
    """
    Convierte un archivo WAV a MP3 320kbps usando ffmpeg local.
    Devuelve la ruta absoluta al MP3 generado.
    """
    if not wav_path.endswith(".wav"):
        raise ValueError("El archivo de entrada debe terminar en .wav")
        
    mp3_path = wav_path[:-4] + ".mp3"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", wav_path,
        "-codec:a", "libmp3lame",
        "-b:a", "320k",
        mp3_path
    ]
    
    log.info("converting_wav_to_mp3", source=wav_path, dest=mp3_path)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"FFmpeg falló silenciosamente al crear {mp3_path}")
        
    return mp3_path

