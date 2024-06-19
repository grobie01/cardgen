import re
import os
import sys
import json
import random
import argparse
from openai import OpenAI
from elevenlabs.client import ElevenLabs
import elevenlabs

oai_client = OpenAI()
xi_client = ElevenLabs(api_key=os.getenv('XI_API_KEY'))

prompt = """Translate the following English and Chinese phrases and provide the output in JSON format with "cards" as top level field and subfields "english", "hanzi", "pinyin":
      {"cards": [{
        "english": english,
        "hanzi": simplified hanzi,
        "pinyin": pinyin
        }]
      }"""

#json reposnse to tuple
def proc_json(json_data):
    cards = json_data['cards']
    tuples = []
    for card in cards:
        english = card['english']
        hanzi = card['hanzi']
        pinyin = card['pinyin']
        card_tuple = (english, hanzi, pinyin)
        tuples.append(card_tuple)
    return tuples

#create list of tuples from file
def read_file_in_chunks(file_name, is_test=False,chunk_size=10):
    chunks = []
    with open(file_name, 'r') as file:
        while True:
            lines = []
            for _ in range(chunk_size):
                #read a line from the file, remove whitespace
                line = file.readline().strip()
                if not line:
                    break
                lines.append(line.strip())
            if not lines:
                break

            #submit list of ten lines to openai chat api
            prepared_lines = '\n'.join(lines)
            response = oai_client.chat.completions.create(
                            model="gpt-4o",
                            response_format={ "type": "json_object" },
                            messages=[
                                {"role": "system", "content": "You are a helpful assistant."},
                                {"role": "user", "content": prompt + '\n' + prepared_lines}
                            ])
            json_response = response.choices[0].message.content
            
            json_data = json.loads(json_response)
            processed_json = proc_json(json_data)
            for tup in processed_json:
                chunks.append(tup)
            print("Processed chunk...")
            if is_test:
                break
    return chunks

def gen_audio_filename(english_phrase):
    english_phrase = english_phrase.lower()
    english_phrase = re.sub(r'[^\w\s]', '', english_phrase)
    return english_phrase.replace(" ", "_") + ".mp3"

oai_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
xi_voices = xi_client.voices.get_all().voices

def gen_audio(input, filename, use_eleven):
    if use_eleven:
        v = random.choice(xi_voices)
        audio = xi_client.generate(
            text=input,
            voice=v.voice_id,
            model="eleven_multilingual_v2"
        )
        elevenlabs.save(audio, f"zhaudio/{filename}")
    else:
        response = oai_client.audio.speech.create(
            model="tts-1",
            voice=random.choice(oai_voices),
            input=input,
        )
        if not os.path.exists('zhaudio'):
            os.makedirs('zhaudio')
        response.stream_to_file(f"zhaudio/{filename}")

def gen_flashcards(tuples, skip_audio=False, filename="flashcards.txt", use_eleven=False):
    with open(filename, 'w') as f:
        chunk_size = 5
        for i in range(0, len(tuples), chunk_size):
            for english, hanzi, pinyin in tuples[i:i+chunk_size]:
                audio_filename = gen_audio_filename(english)
                if not skip_audio:
                    gen_audio(hanzi, audio_filename, use_eleven)
                    print(f"Generated audio file: {audio_filename}")
                f.write(f"{english};{hanzi} <br> {pinyin} <br> [sound:{audio_filename}]\n")

            for english, hanzi, pinyin in tuples[i:i+chunk_size]:
                audio_filename = gen_audio_filename(english)
                f.write(f"[sound:{audio_filename}];{hanzi} <br> {pinyin} <br> {english}\n")



def parse_args():
    # Create the parser
    parser = argparse.ArgumentParser(description='Generate Anki flashcards for learning Chinese.')

    # Add arguments
    parser.add_argument('--test', action='store_true', help='Run only with first ten lines from the input file.')
    parser.add_argument('--filename', type=str, default="phrases.txt", help='Name of the input file.')
    parser.add_argument('--skip_audio', action='store_true', help='Skip generating audio files.')
    parser.add_argument('--eleven', action='store_true', help='Use elevenlabs for generating audio.')

    # Parse the arguments
    return parser.parse_args()


def run(args):
    tuples = read_file_in_chunks(args.filename, args.test)
    gen_flashcards(tuples, args.skip_audio, use_eleven=args.eleven)

if __name__ == "__main__":
    args = parse_args()
    run(args)
