from server_utils import ResponseType, Utility
from PIL import Image
from PIL import Image
from transformers import AutoFeatureExtractor, SwinForImageClassification
from transformers import DetrImageProcessor, DetrForObjectDetection
import random
import torch
import os
from concurrent.futures import ThreadPoolExecutor
from api import SearchAPI, GeminiAPI, Text2SpeechAPI
from database import ListeningQuestion, ListeningPracticeItem, Database
from bson import ObjectId
from datetime import datetime
from io import BytesIO
from server_thread_controller import is_thread_stopped


class IdsServer:
    CHECK_POINT_SWIN = "microsoft/swin-base-patch4-window12-384"
    CHECK_POINT_DETR = "facebook/detr-resnet-101"

    IMAGE_REPO_PATH = "E:/Image Repository/"

    BATCH_DATA_LEN = 1024

    NUM_CLASS_FROM_CLASSIFIER = 3
    
    DETECT_THRESHOLD = 0.9
    NUM_DETECT_OBJ = 2

    IMG_PER_TOPIC = 15

    QUESTION_PER_TOPIC = 4
    IMG_PER_QUESTION = 4

    def __init__(self) -> None:

        self.feature_extractor = AutoFeatureExtractor.from_pretrained(IdsServer.CHECK_POINT_SWIN)
        self.classifier = SwinForImageClassification.from_pretrained(IdsServer.CHECK_POINT_SWIN).to('cuda')
        self.classifier.eval()

        self.obj_detector_processor = DetrImageProcessor.from_pretrained(IdsServer.CHECK_POINT_DETR, revision="no_timm")
        self.obj_detector = DetrForObjectDetection.from_pretrained(IdsServer.CHECK_POINT_DETR, revision="no_timm").to('cuda')
        self.obj_detector.eval()
 

    """
        Only find similar images from the image sent by the client
        1. Receive the user id as string
        2. Receive the number of topic images
        3. Receive the topic images
        4. Find similar images, 15 for each topic image
        5. Save to database and report to the client
    """
    def handle_find_similar(self, client_socket, addr):
        # Step 1
        print(f'{addr} step 1')
        if is_thread_stopped(addr):
            print(f'Thread for {addr} stopped in IdsServer')
            return
        user_id_len_bytes = client_socket.recv(4)
        user_id_len = Utility.big_endian_to_int(user_id_len_bytes)
        user_id = client_socket.recv(user_id_len).decode('utf-8')
        print(f'{addr} user id: {user_id}')

        # Step 2
        print(f'{addr} step 2')
        if is_thread_stopped(addr):
            print(f'Thread for {addr} stopped in IdsServer')
            return
        num_img_bytes = client_socket.recv(4)
        num_img = Utility.big_endian_to_int(num_img_bytes)
        print(f'{addr} wants {num_img} topic -> Need {num_img * IdsServer.IMG_PER_TOPIC} images')

        # Step 3
        print(f'{addr} step 3')
        if is_thread_stopped(addr):
            print(f'Thread for {addr} stopped in IdsServer')
            return
        topic_images = IdsServer.__save_many_images(client_socket, addr, num_img)

        # Step 4
        print(f'{addr} step 4')
        if is_thread_stopped(addr):
            print(f'Thread for {addr} stopped in IdsServer')
            return
        img_byte_array = []

        def process_image(image):
            return self.__find_similar(image, IdsServer.IMG_PER_TOPIC, get_bytes=True, addr=addr)

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(process_image, topic_images))

        for result in results:
            if result is None:
                return
            
        if is_thread_stopped(addr):
            print(f'Thread for {addr} stopped in IdsServer')
            return
        for result in results:
            img_byte_array += result

        # Step 5
        print(f'{addr} step 5')
        if is_thread_stopped(addr):
            print(f'Thread for {addr} stopped in IdsServer')
            return
        print('Creating practice item...')
        item = IdsServer.__create_practice_item(user_id, topic_images, img_byte_array)
        new_id_str = ObjectId().__str__()
        item.id = ObjectId(new_id_str)

        print('Inserting to database...')
        if is_thread_stopped(addr):
            print(f'Thread for {addr} stopped in IdsServer')
            return
        Database.insertListening(item)

        if is_thread_stopped(addr):
            print(f'Thread for {addr} stopped in IdsServer')
            return
        client_socket.sendall(
            Utility.int_to_big_endian(ResponseType.SUCCESS)
        )

        print(f'Sending {new_id_str} to client')
        
        client_socket.sendall((new_id_str + '   ').encode('utf-8'))

        print(f'{addr} done')

    
    """
        Find similar images from the image sent by the client
        1. Get the classes and objects from the image
        2. Search for images with the same classes and objects
        3. If not enough, get images from the repository
    """
    def __find_similar(self, image, num_img, get_bytes, addr):
        def host_query_searching():
            print('Classifying...')
            classes = self.__classify(image, IdsServer.NUM_CLASS_FROM_CLASSIFIER)
            if is_thread_stopped(addr):
                print(f'Thread for {addr} stopped in IdsServer')
                return None
            objs = self.__detect_object(image, threshold=IdsServer.DETECT_THRESHOLD, max_num_obj=IdsServer.NUM_DETECT_OBJ)
            if is_thread_stopped(addr):
                print(f'Thread for {addr} stopped in IdsServer')
                return None
            search_query = ' and '.join(objs) + f' and {classes[0]}'
            img_links = SearchAPI.search_image(search_query)

            return classes, img_links
        
        def gemini_query_searching():
            gemini_objs = GeminiAPI.detect(image)
            img_links = SearchAPI.search_image(gemini_objs)
            return img_links
        
        with ThreadPoolExecutor() as executor:
            future1 = executor.submit(host_query_searching)
            future2 = executor.submit(gemini_query_searching)

            f1_result = future1.result()
            if f1_result is None:
                return None
            classes, img_links_1 = f1_result

            img_links = list(set(img_links_1 + future2.result()))
        
        if is_thread_stopped(addr):
                print(f'Thread for {addr} stopped in IdsServer')
                return None
        img_array_from_link = Utility.get_image_from_links(img_links, num_img, get_bytes=get_bytes)

        if len(img_array_from_link) >= num_img:
            random.shuffle(img_array_from_link)
            img_array_from_link = img_array_from_link[:num_img]

        if is_thread_stopped(addr):
                print(f'Thread for {addr} stopped in IdsServer')
                return None
        img_array_from_repo = IdsServer.__get_image_from_repo(
            classes=classes[1:],
            num_img=num_img - len(img_array_from_link),
            get_bytes=get_bytes
        )

        img_array = img_array_from_link + img_array_from_repo

        return img_array
    
        
    """
        Get the num_class with the highest probabilites
    """
    def __classify(self, image, num_class):
        inputs = self.feature_extractor(images=image, return_tensors="pt").to('cuda')
        outputs = self.classifier(**inputs)
        logits = outputs.logits

        predicted_class_ids = torch.topk(logits[0], num_class)[1].tolist()

        return [self.classifier.config.id2label[idx] for idx in predicted_class_ids]
    


    """
        Get the max_num_obj object with 'scrore' higher than threshold
        The return array may have len smaller than the max_num_obj
    """
    def __detect_object(self, image, threshold, max_num_obj):
        inputs = self.obj_detector_processor(images=image, return_tensors="pt").to('cuda')
        outputs = self.obj_detector(**inputs)
  
        target_sizes = torch.tensor([image.size[::-1]])
        results = self.obj_detector_processor.post_process_object_detection(
            outputs, target_sizes=target_sizes, threshold=threshold
        )[0]

        labels = results['labels']
        probabilities = results['scores']
        sorted_indices = torch.argsort(probabilities, descending=True)

        selected_labels = []
        for idx in sorted_indices:
            label = labels[idx].item()
            if label not in selected_labels:
                selected_labels.append(label)
            if len(selected_labels) == max_num_obj:
                break
        
        return [self.obj_detector.config.id2label[label] for label in selected_labels]
    

    @staticmethod
    def __save_many_images(client_socket, addr, num_img):
        img_list = []
        for i in range(num_img):
            temp_img_path = f'img/client/temp_img_{addr}_{i}.JPEG'
            IdsServer.__save_client_image(client_socket, temp_img_path)
            img_list.append(Image.open(temp_img_path))
        
        return img_list


    @staticmethod
    def __save_client_image(client_socket, temp_img_path):
        data_len_bytes = client_socket.recv(4)
        
        data_len = Utility.big_endian_to_int(data_len_bytes)
        recv_len = 0

        with open(temp_img_path, 'wb') as file:
            while recv_len < data_len:
                remains = data_len - recv_len
                if remains < IdsServer.BATCH_DATA_LEN:
                    batch_len = remains
                else:
                    batch_len = IdsServer.BATCH_DATA_LEN

                data = client_socket.recv(batch_len)
                recv_len += len(data)
                file.write(data)
    
    

    @staticmethod
    def __get_image_from_repo(classes, num_img, get_bytes=False):
        if num_img <= 0:
            return []
        
        num_classes = len(classes)
        num_of_each_class = []

        cls_idx = 0
        for _ in range(num_img):
            if cls_idx >= num_classes:
                cls_idx = 0

            if cls_idx == len(num_of_each_class):
                num_of_each_class.append(1)
            else:
                num_of_each_class[cls_idx] += 1
            
            cls_idx += 1
            

        img_list = []
        for idx, n in enumerate(num_of_each_class):
            cls = classes[idx]
            father_dir = IdsServer.IMAGE_REPO_PATH + cls
            img_files = os.listdir(father_dir)

            selected_img = random.sample(img_files, n)
            
            for img_name in selected_img:
                img_path = father_dir + '/' + img_name
                if get_bytes:
                    img_list.append(Utility.get_image_bytes_from_path(img_path))
                else:
                    img_list.append(Image.open(img_path))
        
        return img_list
    

    @staticmethod
    def __create_practice_item(user_id_str, topic_image_list, similar_image_list):
        question_list = []
        num_add_per_topic = IdsServer.QUESTION_PER_TOPIC * IdsServer.IMG_PER_QUESTION - 1

        for i in range(len(topic_image_list)):
            print(f'Creating question for topic at {i}')
            topic_img = [Utility.image_to_bytes(topic_image_list[i])]
            similar_imgs = similar_image_list[i * num_add_per_topic:(i + 1) * num_add_per_topic]
            all_topic_images = topic_img + similar_imgs 
            random.shuffle(all_topic_images)

            def process_question(j):
                images_for_question = all_topic_images[j * IdsServer.IMG_PER_QUESTION:(j + 1) * IdsServer.IMG_PER_QUESTION]
                answer_index = random.randint(0, IdsServer.IMG_PER_QUESTION - 1)
                description = GeminiAPI.describe(
                    Image.open(
                        BytesIO(images_for_question[answer_index])
                    )
                )
                mp3_bytes = Text2SpeechAPI.text_to_mp3_bytes(description)
                return ListeningQuestion(
                    image_byte_arrays=images_for_question,
                    description=description,
                    answer_index=answer_index,
                    mp3_byte_array=mp3_bytes
                )

            with ThreadPoolExecutor() as executor:
                question_list.extend(list(executor.map(process_question, range(IdsServer.QUESTION_PER_TOPIC))))

        print(f'Done creating {len(question_list)} questions')
        return ListeningPracticeItem(
            id=None,
            user_id=ObjectId(user_id_str),
            title='Chưa được đặt tên',
            creation_date=datetime.now(),
            is_new=True,
            question_list=question_list
        )

    
