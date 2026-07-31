import os
from dotenv import load_dotenv
from imagekitio import ImageKit
from fastapi import UploadFile

# Load environment variables from .env file
load_dotenv()

# Initialize ImageKit with credentials from environment variables
# You must set these in your .env file or environment
imagekit = ImageKit(
    private_key=os.getenv('IMAGEKIT_PRIVATE_KEY', 'your_private_key'),
)

url_endpoint = os.getenv('IMAGEKIT_URL_ENDPOINT', 'your_url_endpoint')

async def upload_image_to_imagekit(file: UploadFile, folder: str = "/products") -> str:
    """
    Uploads a FastAPI UploadFile to ImageKit and returns the URL.
    """
    # Read the file bytes
    file_bytes = await file.read()
    
    # Upload to ImageKit
    upload = imagekit.files.upload(
        file=file_bytes,
        file_name=file.filename,
        folder=folder
    )
    
    print(f"ImageKit upload response: {upload}")  # Debugging line
        
    # Return the URL of the uploaded image
    return upload.url
