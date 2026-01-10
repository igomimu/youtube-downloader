from PIL import Image
import sys

try:
    img = Image.open("/home/mimura/.gemini/antigravity/brain/7002bf77-586f-4cee-976d-7c8f99391e38/app_icon_1768019221036.png")
    # Resize to common icon sizes
    img.save("/mnt/c/Users/lucky/Desktop/TubeDownloader.ico", format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("Icon saved successfully")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
