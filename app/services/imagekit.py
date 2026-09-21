import os
import uuid
import re
from dotenv import load_dotenv
from imagekitio import ImageKit
from fastapi import UploadFile

# Load environment variables from .env file
load_dotenv()

# Initialize ImageKit with credentials from environment variables
imagekit_private_key = os.getenv('IMAGEKIT_PRIVATE_KEY', 'your_private_key')
url_endpoint = os.getenv('IMAGEKIT_URL_ENDPOINT', 'https://ik.imagekit.io/2s78gfu2x')

imagekit = None
if imagekit_private_key and imagekit_private_key != 'your_private_key':
    try:
        imagekit = ImageKit(private_key=imagekit_private_key)
    except Exception as e:
        print(f"ImageKit initialization notice: {e}")

async def upload_image_to_imagekit(file: UploadFile, folder: str = "/products") -> str:
    """
    Uploads a FastAPI UploadFile to ImageKit and returns the URL.
    Falls back gracefully to static uploads if ImageKit credentials are not active.
    """
    file_bytes = await file.read()
    filename = file.filename or f"upload_{uuid.uuid4().hex[:8]}"

    # Attempt upload to ImageKit
    if imagekit is not None:
        try:
            upload = imagekit.files.upload(
                file=file_bytes,
                file_name=filename,
                folder=folder
            )
            print(f"ImageKit upload response: {upload}")
            if hasattr(upload, "url") and upload.url:
                return upload.url
        except Exception as e:
            print(f"ImageKit upload failed, falling back to local static storage: {e}")

    # Fallback: Save file to local uploads directory
    clean_folder = folder.strip("/\\")
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    target_dir = os.path.join(backend_root, "uploads", clean_folder)
    os.makedirs(target_dir, exist_ok=True)

    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = os.path.join(target_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    base_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    return f"{base_url}/uploads/{clean_folder}/{unique_name}"
