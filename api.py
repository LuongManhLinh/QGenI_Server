import requests
import google.generativeai as genai
from gtts import gTTS
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
from concurrent.futures import ThreadPoolExecutor


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
    

class EmailAPI:
    __MY_EMAIL = open('keys/MY_EMAIL').read().strip()
    __PASSWORD = open('keys/PASSWORD').read().strip()
    

    @staticmethod
    def send_random_otp(to_email):
        otp = [random.randint(0, 9) for _ in range(4)]
        subject = "OTP Verification for your QGenI account"
        body = f"Your OTP is: {''.join(map(str, otp))}"
        with ThreadPoolExecutor() as executor:
            executor.submit(EmailAPI.__send_mail, to_email, subject, body)
        return otp
        

    @staticmethod
    def __send_mail(to_email, subject, body):
        print(f"Sending email to {to_email}...")
        try:
            smtp_server = "smtp.gmail.com"
            smtp_port = 587

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(EmailAPI.__MY_EMAIL, EmailAPI.__PASSWORD)

            msg = MIMEMultipart()

            msg['From'] = EmailAPI.__MY_EMAIL
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            server.sendmail(EmailAPI.__MY_EMAIL, to_email, msg.as_string())

            print(f"Email sent successfully to {to_email}!")
        except smtplib.SMTPAuthenticationError as e:
            print(f"SMTP Authentication Error: {e.smtp_code} - {e.smtp_error.decode()}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            server.quit()


if __name__ == '__main__':
    a = [1, 2, 3]
    print(''.join(a))

