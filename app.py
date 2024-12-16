import os
import io
import sounddevice as sd
import soundfile as sf
import numpy as np
import speech_recognition as sr
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Add this at the top of your existing code, after the other imports
@app.get("/")
def read_root():
    return {"status": "Speech-to-Text Validator API is running"}


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
    error: Optional[str] = None

@app.post("/check-speech/", response_model=TextCheckResponse)
async def check_speech(audio: UploadFile, text: str = Form(...), language: str = Form(...)):
    try:
        # Read the uploaded file
        audio_content = await audio.read()
        
        # Create a temporary file to store the audio
        temp_audio_path = "temp_audio.wav"
        
        try:
            # Write audio content to a temporary file
            with open(temp_audio_path, "wb") as f:
                f.write(audio_content)
            
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            # Load the saved file
            with sr.AudioFile(temp_audio_path) as source:
                audio_data = recognizer.record(source)
            
            # Determine language code
            language_code = "en-US" if language == "English" else "hi-IN"
            
            # Transcribe the audio
            recognized_text = recognizer.recognize_google(audio_data, language=language_code)
            
            # Compare the transcribed text with the provided text
            match = recognized_text.strip().lower() == text.strip().lower()
            
            return TextCheckResponse(match=match, recognized_text=recognized_text)
        
        except Exception as e:
            return TextCheckResponse(match=False, recognized_text="", error=str(e))
        
        finally:
            # Ensure temporary file is always deleted
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
    
    except Exception as e:
        # Handle any unexpected errors
        raise HTTPException(status_code=500, detail=str(e))
