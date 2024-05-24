import os
import time
import speech_recognition as sr
import keyboard
from google.cloud import speech
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  

# Load environment variables from .env file
if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
    raise EnvironmentError("The GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")

speech_client = speech.SpeechClient()  
recognizer = sr.Recognizer()
recording = False

def create_chatbot_prompt():
    with open('personality.txt', 'r') as personality_file:
        personality_prompt = personality_file.read()

    with open('exampleConvos.txt', 'r') as examples_file:
        examples = examples_file.read()

    complete_prompt = (
        f"{personality_prompt}\n\n"
        "Here are some example conversations:\n\n"
        f"{examples}\n\n"
        "Now, let's start a new conversation."
    )
    return complete_prompt

def chat_with_bot(user_input):
    prompt = create_chatbot_prompt() + f"\nUser: {user_input}\nAssistant:"
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_input}
    ]
    response = openai_client.chat.completions.create(
        messages=messages,
        model="gpt-4",
        max_tokens=150
    )
    message_content = response.choices[0].message.content
    return message_content.strip()

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
            sample_rate = 44100  # default sample rate
            if hasattr(audio, 'sample_rate'):
                sample_rate = audio.sample_rate

            # Configure the request to use the correct sample rate
            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code="en-US"
            )
            response = speech_client.recognize(config=config, audio=audio)
            for result in response.results:
                recognized_text = result.alternatives[0].transcript
                print(f"Recognized text: {recognized_text}")
                bot_response = chat_with_bot(recognized_text)
                print(f"Lord Befufftlefumpter III: {bot_response}")
                # Here you can add the text-to-speech function
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
