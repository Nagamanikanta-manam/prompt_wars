import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Google Cloud
from google.cloud import firestore, storage, speech, vision
import googlemaps

from google.adk.agents import Agent

load_dotenv()

# ==============================
# CONFIG
# ==============================
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")
GMAPS_API_KEY = os.getenv("GMAPS_API_KEY")

db = firestore.Client()
storage_client = storage.Client()
gmaps = googlemaps.Client(key=GMAPS_API_KEY)

# ==============================
# INPUT PROCESSING (Accessibility)
# ==============================

def speech_to_text(audio_file: str) -> str:
    client = speech.SpeechClient()

    with open(audio_file, "rb") as f:
        content = f.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(language_code="en-US")

    response = client.recognize(config=config, audio=audio)

    return " ".join([r.alternatives[0].transcript for r in response.results])


def image_to_text(image_file: str) -> str:
    client = vision.ImageAnnotatorClient()

    with open(image_file, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)
    response = client.label_detection(image=image)

    labels = [label.description for label in response.label_annotations]
    return "Detected: " + ", ".join(labels)


# ==============================
# VALIDATION (Security)
# ==============================

def validate_food_items(items):
    if not isinstance(items, list):
        raise ValueError("Invalid food_items format")

    for i in items:
        if "name" not in i or "amount" not in i:
            raise ValueError("Invalid item structure")

    return True


# ==============================
# FIRESTORE (Real-time DB)
# ==============================

def store_request(data: dict):
    db.collection("donations").add(data)


# ==============================
# MAPS (Efficiency + Real-world)
# ==============================

def get_distance(origin_zip, dest_zip):
    result = gmaps.distance_matrix(origin_zip, dest_zip)
    return result["rows"][0]["elements"][0]["distance"]["value"]


# ==============================
# STORAGE (Docs)
# ==============================

def upload_to_storage(filename, content):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(content)


# ==============================
# TOOLS
# ==============================

async def find_best_charity(category: str) -> str:
    charities = db.collection("charities").stream()

    best = None
    best_score = 999999

    for c in charities:
        data = c.to_dict()

        if category.lower() in data["needs"] or "any" in data["needs"]:
            dist = get_distance("90210", data["zip"])

            if dist < best_score:
                best = data
                best_score = dist

    return json.dumps(best)


async def dispatch_driver(charity_name: str):
    await asyncio.sleep(0.1)  # simulate async job
    return f"Driver dispatched to {charity_name}"


async def generate_docs(donor, charity, items):
    validate_food_items(items)

    text = f"{donor} → {charity}\nItems: {items}"

    filename = f"docs/{datetime.now().timestamp()}.txt"
    upload_to_storage(filename, text)

    return "Docs stored in GCS"


async def process_donation(input_text: str):
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

async def main():
    user_input = "We have vegetables expiring in 24 hours"

    result = await process_donation(user_input)
    charity = await find_best_charity("vegetables")
    dispatch = await dispatch_driver("Best Charity")
    docs = await generate_docs("Donor A", "Best Charity", [{"name": "vegetables", "amount": 60}])

    print(result, charity, dispatch, docs)


if __name__ == "__main__":
    asyncio.run(main())