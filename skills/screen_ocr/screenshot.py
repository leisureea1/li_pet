import mss
from PIL import Image

def capture_screen(
        output_path="screen.png"
):
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        image.save(output_path)
    return output_path