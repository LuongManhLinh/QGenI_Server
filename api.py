import requests
import google.generativeai as genai
from gtts import gTTS
from io import BytesIO


class SearchAPI:
    __SEARCH_API_KEY = open('keys/SEARCH_API_KEY').read()
    __SEARCH_ENGINE_ID = open('keys/SEARCH_ENGINE_ID').read()
    __SEARCH_URL = 'https://www.googleapis.com/customsearch/v1'

    @staticmethod
    def search_image(search_query):
        try:
            img_links = []
            params = {
                'q': search_query,
                'key': SearchAPI.__SEARCH_API_KEY,
                'cx': SearchAPI.__SEARCH_ENGINE_ID,
                'searchType': 'image'
            }

            response = requests.get(SearchAPI.__SEARCH_URL, params=params)
            results = response.json()['items']
            
            for item in results:
                link = item['link']
                img_links.append(link)
            
            return img_links
        
        except Exception:
            return []


class GeminiAPI:
    __MODEL = genai.GenerativeModel(model_name="gemini-1.5-flash")
    __DETECT_PROMT = "In 5 words, what are inside the image?"
    __DESCRIBE_PROMPT = "Describe the given picture with IELTS vocabulary within 20 words."
    
    __API_KEY = open('keys/GEMINI_API_KEY').read()
    genai.configure(api_key = __API_KEY)

    @staticmethod
    def detect(image):
        response =  GeminiAPI.__MODEL.generate_content(
            [
                GeminiAPI.__DETECT_PROMT,
                image
            ]
        )
        return response.text
    
    @staticmethod
    def describe(image):
        response =  GeminiAPI.__MODEL.generate_content(
            [
                GeminiAPI.__DESCRIBE_PROMPT,
                image
            ]
        )
        text = response.text
        return text.split(":", 1)[-1] if ":" in text else text
    
    @staticmethod
    def generate_content(prompt):
        response =  GeminiAPI.__MODEL.generate_content(prompt)
        return response.text



class Text2SpeechAPI:
    @staticmethod
    def text_to_mp3_bytes(text):
        tts = gTTS(text, lang="en")
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        return mp3_fp.getvalue()
