import os
from pipeline.video_creator import create_thumbnail, create_video_with_visualizer

def test_video_creation():
    title = "Test Music Title"
    mood = "epic"
    thumb_path = "output_test_thumb.jpg"
    video_path = "output_test_video.mp4"
    mp3_path = "dummy.mp3"

    print("Creando thumbnail...")
    create_thumbnail(title, mood, thumb_path)
    assert os.path.exists(thumb_path), "Thumbnail no creada"
    
    print("Creando video (puede tardar unos segundos)...")
    create_video_with_visualizer(mp3_path, thumb_path, video_path)
    assert os.path.exists(video_path), "Video no creado"
    
    print("Prueba exitosa. Thumbnail y Video creados.")

if __name__ == "__main__":
    test_video_creation()
