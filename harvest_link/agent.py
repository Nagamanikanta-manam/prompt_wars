import os
import json
import asyncio
import logging
from datetime import datetime
from functools import lru_cache
from typing import List, Dict, Any, Union
from dotenv import load_dotenv

# Google Cloud
from google.cloud import firestore, storage, speech, vision
import googlemaps

from google.adk.agents import Agent

load_dotenv()
logging.basicConfig(level=logging.INFO)

# ==============================
# CONFIG
# ==============================
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")
GMAPS_API_KEY = os.getenv("GMAPS_API_KEY")

try:
    db = firestore.Client()
except Exception as e:
    logging.warning(f"Firestore not initialized: {e}")
    db = None

try:
    storage_client = storage.Client()
except Exception as e:
    logging.warning(f"Storage not initialized: {e}")
    storage_client = None

if GMAPS_API_KEY:
    gmaps = googlemaps.Client(key=GMAPS_API_KEY)
else:
    gmaps = None

# ==============================
# INPUT PROCESSING (Accessibility)
# ==============================

def speech_to_text(audio_source: Union[str, bytes]) -> str:
    """Converts a speech audio source to text using Google Cloud Speech API."""
    client = speech.SpeechClient()

    if isinstance(audio_source, str):
        with open(audio_source, "rb") as f:
            content = f.read()
    else:
        content = audio_source

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(language_code="en-US")

    response = client.recognize(config=config, audio=audio)
    return " ".join([r.alternatives[0].transcript for r in response.results])


def image_to_text(image_source: Union[str, bytes]) -> str:
    """Extracts labels and text from an image using Google Cloud Vision API."""
    client = vision.ImageAnnotatorClient()

    if isinstance(image_source, str):
        with open(image_source, "rb") as f:
            content = f.read()
    else:
        content = image_source

    image = vision.Image(content=content)
    response = client.label_detection(image=image)

    labels = [label.description for label in response.label_annotations]
    return "Detected: " + ", ".join(labels)


def process_input(data: Dict[str, Any]) -> str:
    """Multi-input handler that aligns incoming processing depending on type."""
    if data.get("type") == "voice":
        return speech_to_text(data["file"])
    elif data.get("type") == "image":
        return image_to_text(data["file"])
    else:
        return data.get("text", "")


# ==============================
# VALIDATION (Security)
# ==============================

def validate_food_items(items: Any) -> bool:
    """Strictly validates the structure and properties of food item lists."""
    if not isinstance(items, list):
        raise ValueError("Must be list")

    for i in items:
        if "name" not in i or "amount" not in i:
            raise ValueError("Invalid item structure")
            
        if not isinstance(i.get("amount"), (int, float)):
            raise ValueError("Amount must be number")

        if i["amount"] <= 0:
            raise ValueError("Invalid amount")

    return True


# ==============================
# FIRESTORE (Real-time DB)
# ==============================

def store_request(data: dict) -> None:
    """Stores the structured donation request data payload in Firestore."""
    if db:
        db.collection("donations").add(data)


# ==============================
# MAPS (Efficiency + Real-world)
# ==============================

@lru_cache(maxsize=100)
def get_distance_cached(origin: str, dest: str) -> int:
    """Fetches distance using Google Maps Matrix API with lru_cache for efficiency."""
    if not gmaps:
        return 0
    result = gmaps.distance_matrix(origin, dest)
    return result["rows"][0]["elements"][0]["distance"]["value"]


# ==============================
# STORAGE (Docs)
# ==============================

def upload_to_storage(filename: str, content: str) -> None:
    """Uploads string document content directly to Google Cloud Storage."""
    if not storage_client:
        return
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(content)


# ==============================
# TOOLS
# ==============================

async def find_best_charity(category: str) -> str:
    """Matches the given food category to the optimal charity utilizing parallel processes."""
    if not db:
        return json.dumps({"error": "No DB initialized"})

    try:
        charities = db.collection("charities").stream()
        
        valid_charities = []
        tasks = []
        for c in charities:
            data = c.to_dict()

            if category.lower() in data.get("needs", []) or "any" in data.get("needs", []):
                valid_charities.append(data)
                tasks.append(asyncio.to_thread(
                    get_distance_cached, "90210", data.get("zip", "90210")
                ))

        distances = await asyncio.gather(*tasks)
        
        best = None
        best_score = 999999
        for charity, dist in zip(valid_charities, distances):
            if dist < best_score:
                best = charity
                best_score = dist

        return json.dumps(best)
    except Exception as e:
        logging.error(f"Error finding best charity: {e}")
        return json.dumps({"error": str(e)})


async def dispatch_driver(charity_name: str) -> str:
    """Dispatches a fleet driver to a specified charity endpoint."""
    await asyncio.sleep(0.1)  # simulate async job
    return f"Driver dispatched to {charity_name}"


async def generate_docs(donor: str, charity: str, items: list) -> str:
    """Generate and natively store necessary donation documents in GCS."""
    validate_food_items(items)

    text = f"{donor} → {charity}\nItems: {items}"
    filename = f"docs/{datetime.now().timestamp()}.txt"
    upload_to_storage(filename, text)

    return "Docs stored in GCS"


async def process_donation(input_text: str) -> str:
    """Persists natural language textual input into the donation record db."""
    structured = {
        "raw": input_text,
        "timestamp": str(datetime.now())
    }
    store_request(structured)
    return "Stored"


# ==============================
# AGENT
# ==============================

tools = [
    find_best_charity,
    dispatch_driver,
    generate_docs,
    process_donation
]

agent = Agent(
    name="HarvestLink Pro",
    instruction=(
        "Handle messy input (voice/image/text). "
        "Extract structured food donation info. "
        "Call tools in order:\n"
        "1. process_donation\n"
        "2. find_best_charity\n"
        "3. dispatch_driver\n"
        "4. generate_docs"
    ),
    tools=tools,
    model="gemini-2.5-flash"
)

# ==============================
# ENTRY
# ==============================

async def process_all(input_text: str) -> tuple:
    """Parallel processing handler combining primary input execution blocks."""
    task1 = process_donation(input_text)
    task2 = find_best_charity("vegetables")

    result1, result2 = await asyncio.gather(task1, task2)
    return result1, result2

async def main() -> None:
    try:
        user_input = "We have vegetables expiring in 24 hours"
        
        result1, result2 = await process_all(user_input)
        
        dispatch = await dispatch_driver("Best Charity")
        docs = await generate_docs("Donor A", "Best Charity", [{"name": "vegetables", "amount": 60}])

        logging.info(f"Process: {result1}, Charity Distances: {result2}, Dispatch: {dispatch}, Docs: {docs}")

    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())