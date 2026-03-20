from fastapi import FastAPI, UploadFile, Request
from harvest_link.agent import speech_to_text, image_to_text

app = FastAPI()

@app.post("/voice")
async def voice_input(file: UploadFile):
    """Voice input processing endpoint for converting uploaded audio to text."""
    content = await file.read()
    text = speech_to_text(content)
    return {"text": text}

@app.post("/image")
async def image_input(file: UploadFile):
    """Image input processing endpoint for visual AI label detection."""
    content = await file.read()
    text = image_to_text(content)
    return {"detected": text}
