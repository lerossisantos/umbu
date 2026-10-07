"""Calls the image model. The Art Director agent decides WHAT to draw;
this code does the drawing call and resizes to the exact channel spec."""
import base64
import io
import os
from urllib.parse import urlparse

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()


def get_image_client() -> OpenAI:
    """Image models are called on the resource's OpenAI v1 endpoint, not the project
    endpoint (the project endpoint returns 404 for images). Same Azure sign-in, no keys."""
    host = urlparse(os.environ["FOUNDRY_PROJECT_ENDPOINT"]).netloc  # umbu-resource.services.ai.azure.com
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")
    return OpenAI(base_url=f"https://{host}/openai/v1/", api_key=token_provider)

# GPT-Image-2 needs both edges to be multiples of 16, so we generate close to
# the target ratio, then crop/resize to the exact size in channel_specs.json.
GENERATION_SIZES = {
    (1200, 628): "1536x800",   # Google Display landscape, 1.91:1
    (1200, 600): "1536x768",   # Email hero, 2:1
}


def generate_image(client, prompt: str, target_size: list[int], out_path) -> None:
    target = tuple(target_size)
    response = client.images.generate(
        model=os.environ["IMAGE_DEPLOYMENT"],
        prompt=prompt,
        size=GENERATION_SIZES.get(target, "1536x1024"),
        quality="medium",
        n=1,
    )
    image = Image.open(io.BytesIO(base64.b64decode(response.data[0].b64_json)))
    image = _cover(image, target)
    image.save(out_path, format="PNG")


def _cover(image: Image.Image, target: tuple[int, int]) -> Image.Image:
    """Scale to fill the target size, then center-crop the overflow."""
    tw, th = target
    scale = max(tw / image.width, th / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = (resized.width - tw) // 2
    top = (resized.height - th) // 2
    return resized.crop((left, top, left + tw, top + th))
