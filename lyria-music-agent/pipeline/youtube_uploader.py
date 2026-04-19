import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
import structlog

log = structlog.get_logger()

# Scopes requeridos por YouTube Data API (subir videos)
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service():
    """
    Obtiene el servicio autenticado de YouTube.
    Lee o genera `youtube_token.json`.
    """
    creds = None
    token_file = "youtube_token.json"
    client_secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets_file):
                raise FileNotFoundError(
                    f"Falta {client_secrets_file}. No se puede iniciar OAuth de YouTube."
                )
            # ATENCIÓN: Esto abre el navegador y asume UI. No ejecutar en VPS headless.
            # Debe correrse la primera vez en localhost y copiar `youtube_token.json`.
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(token_file, "w") as token:
            token.write(creds.to_json())
            
    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(video_path: str, metadata: dict, thumb_path: str) -> str:
    """
    Sube un video de forma síncrona a YouTube (unlisted o public).
    Llamado usando asyncio.to_thread desde el orquestador principal.
    Devuelve la URL en caso de éxito.
    """
    log.info("youtube_upload_start", video=video_path, title=metadata["yt_title"])
    
    youtube = get_authenticated_service()
    
    body = {
        "snippet": {
            "title": metadata["yt_title"],
            "description": metadata.get("yt_description", ""),
            "tags": metadata.get("pond5_keywords", "").split(","),
            "categoryId": "10" # Music
        },
        "status": {
            "privacyStatus": "unlisted",  # Para testear de forma segura primero
            "selfDeclaredMadeForKids": False
        }
    }
    
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )
    
    response = None
    while response is None:
        status, response = insert_request.next_chunk()
        if status:
            log.debug("youtube_upload_progress", progress=f"{int(status.progress() * 100)}%")
            
    video_id = response.get("id")
    video_url = f"https://youtu.be/{video_id}"
    log.info("youtube_upload_complete", url=video_url)
    
    # Subir thumbnail (opcional pero deseado)
    if thumb_path and os.path.exists(thumb_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumb_path)
            ).execute()
            log.info("youtube_thumb_uploaded", video_id=video_id)
        except Exception as e:
            log.warning("youtube_thumb_failed", error=str(e))
            
    return video_url

if __name__ == "__main__":
    # Test Standalone para ejecutar en máquina local por el desarrollador
    # Esto invocará el Flow de OAuth si no existe youtube_token.json y publicará "test"
    print("Iniciando OAuth local test...")
    get_authenticated_service()
    print("Generación de token exitosa. Revisa youtube_token.json en root.")
