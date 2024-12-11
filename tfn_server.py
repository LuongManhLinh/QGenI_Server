from transformers import T5Tokenizer, T5ForConditionalGeneration
from server_utils import Utility, ResponseType
from bson import ObjectId
from database import Database, ReadingPracticeItem, ReadingQuestion
import random
from datetime import datetime

def get_prompt(passage, statement):
    return f"""Passage:
{passage}
Statement: 
{statement}

Q: 
If the statement is not relevant to the passage, say 'Not Given'.
Otherwise, if the statement is true to the passage, say 'True', and if the statement is false to the passage, say 'False'.
"""


def label_to_number(label):
    if label == "True":
        return 1
    elif label == "False":
        return -1
    else:
        return 0
    

class TfnServer():
    TOKENIZER_CHECKPOINT = "google/flan-t5-base"
    MODEL_CHECKPOINT= "model/tfn_model"

    TRUTH_OUR_PREDICTION = 0.3

    BATCH_DATA_LEN = 256

    def __init__(self):
        self.tokenizer = T5Tokenizer.from_pretrained(TfnServer.TOKENIZER_CHECKPOINT)
        self.model = T5ForConditionalGeneration.from_pretrained(TfnServer.MODEL_CHECKPOINT).to('cuda')
        self.model.eval()



    """
        1. Receive the user_id as string
        2. Receive the passage
        3. Receive the number of statements and all the statements
        4. Simultaneously receive the types as numbers and recheck each statement
        5. Refine the types
        6. Save to the database
    """
    def handle_tfn_checking(self, client_socket, addr):
        # Step 1
        print(f'{addr} step 1')
        user_id = TfnServer.__receive_long_string(client_socket)
        print(f'{addr} user id: {user_id}')

        # Step 2
        print(f'{addr} step 2')
        passage = TfnServer.__receive_long_string(client_socket)
        print(f'{addr} passage_len: {len(passage)}')

        # Step 3
        print(f'{addr} step 3')
        num_statements = TfnServer.__receive_int(client_socket)
        print(f'{addr} num_statements: {num_statements}')
        statements = []
        for _ in range(num_statements):
            statement = TfnServer.__receive_long_string(client_socket)
            statements.append(statement)

        # Step 4
        print(f'{addr} step 4')
        recv_types = []
        for _ in range(num_statements):
            recv_type = TfnServer.__receive_int(client_socket)
            recv_types.append(recv_type)

        predicted_types = []
        for statement in statements:
            prompt = get_prompt(passage, statement)
            input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids.to('cuda')
            outputs = self.model.generate(input_ids)
            predicted_label = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            predicted_types.append(label_to_number(predicted_label))

        # Step 5
        print(f'{addr} step 5')
        refined_types = []
        num_diff = 0
        for idx in range(num_statements):
            recv_type = recv_types[idx]
            predicted_type = predicted_types[idx]

            if recv_type != predicted_type:
                num_diff += 1
                prob = random.random()
                if prob < TfnServer.TRUTH_OUR_PREDICTION:
                    refined_types.append(predicted_type)
                else:
                    refined_types.append(recv_type)
            else:
                refined_types.append(recv_type)
        print(f'{addr} num_diff: {num_diff}')

        # Step 6
        print(f'{addr} step 6')
        item = TfnServer.__create_practice_item(user_id, passage, statements, refined_types)
        new_id_str = ObjectId().__str__()
        item.id = ObjectId(new_id_str)

        print('Inserting to database...')
        Database.insertReading(item)

        client_socket.sendall(
            Utility.int_to_big_endian(ResponseType.SUCCESS)
        )

        print(f'Sending {new_id_str} to client')
        
        client_socket.sendall((new_id_str + '   ').encode('utf-8'))

        print(f'{addr} done')


    @staticmethod
    def __receive_long_string(client_socket):
        data_len_bytes = client_socket.recv(4)
        
        data_len = Utility.big_endian_to_int(data_len_bytes)
        recv_len = 0

        buffer = b''
        while recv_len < data_len:
            remains = data_len - recv_len
            if remains < TfnServer.BATCH_DATA_LEN:
                batch_len = remains
            else:
                batch_len = TfnServer.BATCH_DATA_LEN

            data = client_socket.recv(batch_len)
            recv_len += len(data)
            buffer += data
        
        return buffer.decode('utf-8')
    
    @staticmethod
    def __receive_int(client_socket):
        return Utility.big_endian_to_int(client_socket.recv(4))
    
    @staticmethod
    def __create_practice_item(user_id, passage, statements, types):
        question_list = []
        for statement, type in zip(statements, types):
            question_list.append(ReadingQuestion(statement, type))
        
        return ReadingPracticeItem(
            id=None, 
            user_id=ObjectId(user_id), 
            title="Not yet named", 
            is_new=True, 
            creation_date=datetime.now(),
            passage=passage,
            question_list=question_list
        )
    