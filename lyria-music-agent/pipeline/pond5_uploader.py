"""
Pond5 uploader oficial vía FTP.
Bypassea cualquier bloqueo de Cloudflare enviando el wav por la tubería directa de Data.
Requiere POND5_USERNAME (no el email) y POND5_PASSWORD en .env.
"""
import asyncio
import os
import ftplib
import structlog
from core.retry import pond5_retry

log = structlog.get_logger()

class Pond5Uploader:
    def __init__(self):
        # Pond5 FTP requiere el Username (el apodo), no el correo electrónico.
        self.username = os.getenv("POND5_USERNAME")
        self.password = os.getenv("POND5_PASSWORD")
        if not self.username or not self.password:
            log.warning("POND5_USERNAME o POND5_PASSWORD faltantes en .env, la subida por FTP fallará")

    @pond5_retry
    async def upload(self, audio_path: str, metadata: dict) -> bool:
        if not self.username or not self.password:
            raise ValueError("Credenciales Pond5 no disponibles para FTP")

        log.info(
            "pond5_ftp_upload_start",
            title=metadata["pond5_title"],
            file=audio_path
        )
        
        # El protocolo FTP es síncrono, lo encapsulamos en to_thread para no bloquear async
        await asyncio.to_thread(self._upload_ftp_sync, audio_path)
        
        log.info("pond5_ftp_upload_ok", title=metadata["pond5_title"], msg="Recuerda publicar la pista manualmente en el dashboard web.")
        return True

    def _upload_ftp_sync(self, audio_path: str):
        filename = os.path.basename(audio_path)
        ftp = ftplib.FTP('ftp.pond5.com')
        try:
            ftp.login(user=self.username, passwd=self.password)
            with open(audio_path, 'rb') as f:
                # El comando STOR guarda el archivo en el servidor remoto
                ftp.storbinary(f'STOR {filename}', f)
        finally:
            ftp.quit()
