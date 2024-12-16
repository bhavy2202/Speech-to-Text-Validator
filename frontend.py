import streamlit as st
import requests
import sounddevice as sd
import soundfile as sf
import numpy as np
import io
from pydub import AudioSegment
import os
import sys
import traceback
import threading
import time

# Backend API URL
API_URL = "http://127.0.0.1:8000/check-speech/"

class AudioRecorder:
    def __init__(self, channels=1, rate=44100, chunk_duration=0.1):
        self.channels = channels
        self.rate = rate
        self.chunk_duration = chunk_duration
        self.frames = []
        self.is_recording = False
        self.recording_thread = None

    def _record_audio(self):
        """Internal method to record audio in a thread"""
        try:
            # Calculate chunk size based on rate and duration
            chunk_size = int(self.rate * self.chunk_duration)
            
            def audio_callback(indata, frames, time, status):
                """Callback to store audio data"""
                if status:
                    print(f"Recording status: {status}")
                self.frames.append(indata.copy())

            # Start the stream
            with sd.InputStream(
                samplerate=self.rate, 
                channels=self.channels, 
                callback=audio_callback,
                dtype='int16'
            ):
                # Continue recording while is_recording is True
                while self.is_recording:
                    time.sleep(self.chunk_duration)
        
        except Exception as e:
            print(f"Recording error: {e}")
            traceback.print_exc()

    def start_recording(self):
        """Start recording in a separate thread"""
        # Reset recording state
        self.is_recording = True
        self.frames = []

        # Start recording in a separate thread
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.recording_thread.start()
        
        st.toast("Recording started!", icon="🎤")
        return True

    def stop_recording(self):
        """Stop recording"""
        # Stop recording
        self.is_recording = False
        
        # Wait for recording thread to complete
        if self.recording_thread:
            self.recording_thread.join()
        
        return True

    def save_recording(self):
        """Save recording with extensive error checking"""
        try:
            # Check if frames were recorded
            if not self.frames:
                st.error("No audio frames were recorded. Please ensure your microphone is working.")
                return None
            
            # Ensure temp directory exists
            os.makedirs('temp', exist_ok=True)
            
            # Concatenate frames
            audio_data = np.concatenate(self.frames, axis=0)
            
            # Save to wave file
            wav_path = "temp/temp_recording.wav"
            sf.write(wav_path, audio_data, self.rate)
            
            # Verify file exists and has content
            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                # Convert to file-like object for upload
                audio_segment = AudioSegment.from_wav(wav_path)
                audio_file = io.BytesIO()
                audio_segment.export(audio_file, format="wav")
                audio_file.seek(0)
                
                st.success(f"Recording saved. File size: {os.path.getsize(wav_path)} bytes")
                return audio_file
            else:
                st.error("Failed to create audio file.")
                return None
        
        except Exception as e:
            st.error(f"Error saving recording: {e}")
            st.error(traceback.format_exc())
            return None

def convert_audio_to_wav(uploaded_file):
    """
    Convert uploaded audio file to WAV format
    Supports various audio formats
    """
    try:
        # Ensure temp directory exists
        os.makedirs('temp', exist_ok=True)
        
        # Save uploaded file
        temp_input_path = f"temp/uploaded_audio{os.path.splitext(uploaded_file.name)[1]}"
        with open(temp_input_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        
        # Convert to WAV
        wav_path = "temp/converted_audio.wav"
        audio = AudioSegment.from_file(temp_input_path)
        audio.export(wav_path, format="wav")
        
        # Open as file-like object
        with open(wav_path, 'rb') as f:
            audio_file = io.BytesIO(f.read())
        
        # Cleanup temporary files
        os.remove(temp_input_path)
        os.remove(wav_path)
        
        return audio_file
    
    except Exception as e:
        st.error(f"Error converting audio file: {e}")
        return None

def main():
    st.title("Speech-to-Text Validator")
    st.write("This app verifies if your voice matches the entered text.")

    # Initialize recorder
    if 'recorder' not in st.session_state:
        st.session_state.recorder = AudioRecorder()

    # Step 1: Input Text
    text_input = st.text_area("Enter the text (English or Hindi):", placeholder="Type the text you will speak here...")

    # Step 2: Language Selection
    language = st.radio("Select the language for transcription:", ("English", "Hindi"))

    # Audio Input Method Selection
    input_method = st.radio("Choose Audio Input Method:", 
                             ("Record Audio", "Upload Audio File"))

    # Conditional UI based on input method
    if input_method == "Record Audio":
        # Recording Controls
        st.write("Record your voice:")
        
        # Create columns for recording buttons
        col1, col2 = st.columns(2)
        
        with col1:
            # Start Recording Button
            if st.button("Start Recording"):
                if not text_input:
                    st.error("Please enter text before recording.")
                else:
                    # Clear previous recordings
                    if os.path.exists("temp/temp_recording.wav"):
                        os.remove("temp/temp_recording.wav")
                    
                    # Start recording
                    st.session_state.recorder.start_recording()
        
        with col2:
            # Stop Recording Button
            if st.button("Stop Recording"):
                # Stop the recording
                st.session_state.recorder.stop_recording()
                
                # Save the recording
                audio_file = st.session_state.recorder.save_recording()
                if audio_file:
                    st.session_state.audio_file = audio_file
                    st.success("Recording stopped and saved!")
                else:
                    st.error("Failed to save recording.")
    
    else:  # Upload Audio File
        # File uploader
        uploaded_file = st.file_uploader(
            "Upload an audio file", 
            type=['wav', 'mp3', 'ogg', 'flac', 'm4a', 'wma'],
            help="Supports various audio formats"
        )
        
        if uploaded_file is not None:
            # Convert and save uploaded file
            audio_file = convert_audio_to_wav(uploaded_file)
            if audio_file:
                st.session_state.audio_file = audio_file
                st.success(f"Uploaded file '{uploaded_file.name}' processed successfully!")
            else:
                st.error("Failed to process the uploaded audio file.")

    # Process Button
    if st.button("Check Match"):
        if not text_input:
            st.error("Please provide text input.")
            return

        if not hasattr(st.session_state, 'audio_file') or not st.session_state.audio_file:
            st.error("Please record or upload an audio file first.")
            return

        # Send request to backend
        try:
            files = {"audio": st.session_state.audio_file}
            data = {"text": text_input, "language": language}
            response = requests.post(API_URL, files=files, data=data)

            if response.status_code == 200:
                result = response.json()
                st.write(f"**Recognized Text:** {result['recognized_text']}")
                if result.get("match"):
                    st.success("✅ The speech matches the input text!")
                else:
                    st.error("❌ The speech does not match the input text.")
                if result.get("error"):
                    st.warning(f"Error: {result['error']}")
            else:
                st.error(f"Backend Error: {response.status_code}")
        except Exception as e:
            st.error(f"Failed to connect to the backend: {e}")

    st.markdown(
        """
        <div style="position: fixed; bottom: 10px; right: 10px; text-align: right;">
            <p style="font-size: 12px; color: gray;">Powered by Purple Block</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
