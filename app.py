import os
import time
import speech_recognition as sr
import keyboard
from google.cloud import speech
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if the environment variable is set
if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
    raise EnvironmentError("The GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")

client = speech.SpeechClient()

recognizer = sr.Recognizer()
recording = False

def start_recording():
    global recording
    if not recording and keyboard.is_pressed("ctrl"):
        print("Listening...")
        recording = True
        with sr.Microphone() as source:
            audio = recognizer.listen(source)
            stop_recording(audio)

def stop_recording(audio):
    global recording
    if recording:
        print("Stopping recording...")
        recording = False
        try:
            audio_data = audio.get_wav_data()
            audio_content = audio_data

            # Use the sample rate from the recorded audio
            sample_rate = audio.sample_rate if hasattr(audio, 'sample_rate') else 44100

            # Configure the request to use the correct sample rate
            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code="en-US"
            )
            response = client.recognize(config=config, audio=audio)
            for result in response.results:
                print(f"Recognized text: {result.alternatives[0].transcript}")
        except Exception as e:
            print(f"Error: {e}")
        print("Waiting...")

# Set up event handlers using lambda functions
keyboard.on_press_key("ctrl", lambda _: start_recording())
keyboard.on_release_key("ctrl", lambda _: stop_recording(None))

print("Waiting... Press and hold 'Ctrl' to record, release to stop.")

# Loop to keep the script running and check for the 'Esc' key
try:
    while True:
        time.sleep(0.1)
        if keyboard.is_pressed("esc"):
            print("Exiting...")
            break
except KeyboardInterrupt:
    print("Exiting...")
