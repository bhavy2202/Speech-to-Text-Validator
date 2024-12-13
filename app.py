from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import speech_recognition as sr

app = FastAPI()

# Enable CORS for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextCheckResponse(BaseModel):
    match: bool
    recognized_text: str
    error: str = None

@app.post("/check-speech/", response_model=TextCheckResponse)
async def check_speech(audio: UploadFile, text: str = Form(...), language: str = Form(...)):
    try:
        recognizer = sr.Recognizer()
        
        # Save uploaded file temporarily
        with open("temp_audio.wav", "wb") as f:
            f.write(await audio.read())

        # Load the saved file
        with sr.AudioFile("temp_audio.wav") as source:
            audio_data = recognizer.record(source)

        # Transcribe the audio
        language_code = "en-US" if language == "English" else "hi-IN"
        recognized_text = recognizer.recognize_google(audio_data, language=language_code)

        # Compare the transcribed text with the provided text
        match = recognized_text.strip().lower() == text.strip().lower()
        return TextCheckResponse(match=match, recognized_text=recognized_text)

    except Exception as e:
        return TextCheckResponse(match=False, recognized_text="", error=str(e))
