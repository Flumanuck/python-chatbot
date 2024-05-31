import os
import time
import requests
import speech_recognition as sr
import keyboard
from google.cloud import speech
from dotenv import load_dotenv
from openai import OpenAI
from pydub import AudioSegment
from pydub.playback import play
from pydub import playback
from resemble import Resemble

# Load environment variables
load_dotenv()
Resemble.api_key(os.getenv('RESEMBLE_API_KEY'))
character_name = os.getenv('CHARACTER_NAME')

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
    raise EnvironmentError("The GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")

speech_client = speech.SpeechClient()
recognizer = sr.Recognizer()
recording = False

# Initialize conversation history
conversation_history = []

def create_chatbot_prompt():
    with open('personality.txt', 'r') as personality_file:
        personality_prompt = personality_file.read()

    with open('exampleConvos.txt', 'r') as examples_file:
        examples = examples_file.read()

    complete_prompt = (
        f"{personality_prompt}\n\n"
        "Here are some example conversations to guide the assistant's behavior, but do not include them in your responses.\n\n"
        f"{examples}\n\n"
        "Now, let's start a new conversation."
    )
    return complete_prompt

def chat_with_bot(user_input):
    # Update conversation history with the new user input
    conversation_history.append({"role": "user", "content": user_input})
    
    # Include conversation history in the messages
    messages = [{"role": "system", "content": create_chatbot_prompt()}] + conversation_history
    
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=400 
    )
    message_content = response.choices[0].message.content.strip()
    
    # Update conversation history with the ai's response
    conversation_history.append({"role": "assistant", "content": message_content})
    
    # Convert the chatbot response to speech
    audio_file = text_to_speech(message_content)
    return message_content, audio_file

def text_to_speech(text, output_file='output.wav'):
    project_uuid = os.getenv('RESEMBLE_PROJECT_UUID')
    voice_uuid = os.getenv('RESEMBLE_VOICE_UUID')

    response = Resemble.v2.clips.create_sync(
        project_uuid=project_uuid,
        voice_uuid=voice_uuid,
        body=text,
        title=None,
        sample_rate=44100,
        output_format='wav',
        precision=None,
        include_timestamps=None,
        is_public=None,
        is_archived=None,
        raw=None
    )

    if 'item' in response:
        audio_src = response['item']['audio_src']
        audio_response = requests.get(audio_src, stream=True)

        if audio_response.status_code == 200:
            with open(output_file, 'wb') as f:
                for chunk in audio_response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
            audio = AudioSegment.from_file(output_file)
            audio = audio.speedup(playback_speed=1.3)  # Determine speed of the audio respone
            audio.export(output_file, format="wav")
            return output_file
        else:
            print(f"Failed to download audio file, status code: {audio_response.status_code}")
            return None
    else:
        print(f"Error: {response}")
        return None

def play_audio(file_path):
    try:
        # Load the audio file
        audio = AudioSegment.from_file(file_path, format="wav")
        # Convert to 16-bit if necessary
        if audio.sample_width != 2:
            audio = audio.set_sample_width(2)
        # Play the audio file through virtual audio cable
        playback.play(audio)
    except Exception as e:
        print(f"Error playing audio file: {e}")

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
            #Get the recorded audio data
            audio_data = audio.get_wav_data()
            audio_content = audio_data
            
            #predefine audio sample rate at 44100 to work with most microphones
            sample_rate = 44100
            if hasattr(audio, 'sample_rate'):
                sample_rate = audio.sample_rate

            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code="en-US",
                model="default"
            )
            response = speech_client.recognize(config=config, audio=audio)
            for result in response.results:
                recognized_text = result.alternatives[0].transcript
                print(f"Recognized text: {recognized_text}")
                bot_response, audio_file = chat_with_bot(recognized_text)
                print(f"{character_name}: {bot_response}")
                
                # Play the audio response
                play_audio(audio_file)
        except Exception as e:
            print(f"Error: {e}")
        print("Waiting...")

keyboard.on_press_key("ctrl", lambda _: start_recording())
keyboard.on_release_key("ctrl", lambda _: stop_recording(None))

print("Waiting... Press and hold 'Ctrl' to record, release to stop.")

try:
    while True:
        time.sleep(0.1)
        if keyboard.is_pressed("esc"):
            print("Exiting...")
            break
except KeyboardInterrupt:
    print("Exiting...")
