import re
import os
import sys
import json
import random
from openai import OpenAI

client = OpenAI()

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
def read_file_in_chunks(file_name, chunk_size=10):
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
            response = client.chat.completions.create(
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
    return chunks

def gen_audio_filename(english_phrase):
    english_phrase = english_phrase.lower()
    english_phrase = re.sub(r'[^\w\s]', '', english_phrase)
    return english_phrase.replace(" ", "_") + ".mp3"

voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

def gen_audio(input, filename):
    response = client.audio.speech.create(
        model="tts-1",
        voice=random.choice(voices),
        input=input,
    )
    if not os.path.exists('zhaudio'):
        os.makedirs('zhaudio')
    response.stream_to_file(f"zhaudio/{filename}")

def gen_flashcards(tuples, filename="flashcards.txt"):
    with open(filename, 'w') as f:
        for english, hanzi, pinyin in tuples:
            audio_filename = gen_audio_filename(english)
            gen_audio(hanzi, audio_filename)
            print(f"Generated audio file: {audio_filename}")
            f.write(f"{english};{hanzi} <br> {pinyin} <br> [sound:{audio_filename}]\n")

        for english, hanzi, pinyin in tuples:
            audio_filename = gen_audio_filename(english)
            f.write(f"[sound:{audio_filename}];{hanzi} <br> {pinyin} <br> {english}\n")


def run(filename="phrases.txt"):
    tuples = read_file_in_chunks(filename)
    gen_flashcards(tuples)

if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else "phrases.txt"
    run(filename)