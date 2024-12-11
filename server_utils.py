import struct
import requests
import random
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor


class RequestType:
    TFN_CHECK = 1
    IMG_DESC_ONLY = 2
    IMG_FIND_SIMILAR_ONLY = 3
    IMG_FIND_AND_DESC = 4


class ResponseType:
    ACCEPTED = 0
    SUCCESS = 1
    INVALID_REQUEST = 2
    SERVER_ERROR = 3
    CLIENT_ERROR = 4
    SERVER_BUSY = 5


class Utility:

    @staticmethod
    def big_endian_to_int(data_4_bytes):
        return struct.unpack('!I', data_4_bytes)[0]
    
    @staticmethod
    def int_to_big_endian(number):
        return struct.pack('>I', number)
    

    @staticmethod
    def get_image_from_links(links, max_num_img=10, get_bytes=False, timeout=1):
        def fetch_image(link):
            try:
                response = requests.get(link, stream=True, timeout=timeout)
                if response.status_code == 200:
                    image = Image.open(BytesIO(response.content)).convert('RGB')
                    image = Utility.resize_image(image, 512)
                    image_bytes = Utility.image_to_bytes(image, quality=80)

                    if get_bytes:
                        return image_bytes
                    else:
                        return Image.open(BytesIO(image_bytes))
                else:
                    print('Downloading image not accepted')
            except Exception as e:
                if isinstance(e, requests.exceptions.Timeout):
                    print('Skipped downloading image from link')
                else:
                    print('Error downloading image from link:', e)
            return None

        images = []
        num_link = len(links)
        if max_num_img > num_link:
            max_num_img = num_link

        print(f'Getting {max_num_img} from link')
        links_to_get = random.sample(links, max_num_img)

        with ThreadPoolExecutor() as executor:
            results = executor.map(fetch_image, links_to_get)

        for result in results:
            if result is not None:
                images.append(result)
        print(f'Done getting {len(images)} images from links')
        return images
    

    @staticmethod
    def get_image_bytes_from_path(image_path):
        image = Image.open(image_path)
        return Utility.image_to_bytes(image)
    

    @staticmethod
    def image_to_bytes(image, quality=80):
        with BytesIO() as img_byte_array:
            image.save(img_byte_array, format='JPEG', quality=quality)
            return img_byte_array.getvalue()
        

    @staticmethod
    def list_image_to_bytes(images):
        bytes_images = []
        for image in images:
            bytes_images.append( Utility.image_to_bytes(image) )
        
        return bytes_images
    
    
    @staticmethod
    def resize_image(image, max_size):
        width, height = image.size
        if max(width, height) > max_size:
            scaling_factor = max_size / float(max(width, height))
            new_size = (int(width * scaling_factor), int(height * scaling_factor))
            return image.resize(new_size)
        return image
        
    
