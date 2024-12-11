from pymongo import MongoClient
from bson import ObjectId


class ListeningQuestion:
    def __init__(self, image_byte_arrays, description, answer_index, mp3_byte_array):
        self.image_byte_arrays = image_byte_arrays
        self.description = description
        self.answer_index = answer_index
        self.mp3_byte_array = mp3_byte_array


class ReadingQuestion:
    def __init__(self, statement, answer):
        self.statement = statement
        self.answer = answer


class ListeningPracticeItem:
    def __init__(self, id: ObjectId, user_id: ObjectId, title, creation_date, is_new, question_list):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.creation_date = creation_date
        self.is_new = is_new
        self.question_list = question_list

class ReadingPracticeItem:
    def __init__(self, id: ObjectId, user_id: ObjectId, title, creation_date, is_new, passage, question_list):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.creation_date = creation_date
        self.is_new = is_new
        self.passage = passage
        self.question_list = question_list

class Database:

    client = MongoClient("mongodb://localhost:27017/")
    DB_NAME = 'qgeni'
    
    ID = '_id'
    USER_ID = 'userId'
    TITLE = 'title'
    CREATION_DATE = 'creationDate'
    QUESTIONS = 'questions'
    IS_NEW = 'isNew'

    Q_IMAGE_BYTE_ARRAYS = 'imageByteArrays'
    Q_DESCRIPTION = 'description'
    Q_ANSWER_INDEX = 'answerIndex'
    Q_MP3_BYTE_ARRAY = "mp3ByteArray"
    
    PASSAGE = 'passage'
    Q_STATEMENT = "statement"
    Q_ANSWER = "answer"

    @staticmethod
    def get_collection(collection_name):
        return Database.client[Database.DB_NAME][collection_name]
    

    @staticmethod
    def insertListening(item):
        document = {
            Database.ID: item.id,
            Database.USER_ID: item.user_id,
            Database.TITLE: item.title,
            Database.CREATION_DATE: item.creation_date,
            Database.QUESTIONS: [
                {
                    Database.Q_IMAGE_BYTE_ARRAYS: [img_byte_array for img_byte_array in question.image_byte_arrays],
                    Database.Q_DESCRIPTION: question.description,
                    Database.Q_ANSWER_INDEX: question.answer_index,
                    Database.Q_MP3_BYTE_ARRAY: question.mp3_byte_array
                } for question in item.question_list
            ],
            Database.IS_NEW: item.is_new
        }

        collection = Database.get_collection('listening')
        collection.insert_one(document)

    
    @staticmethod
    def insertReading(item):
        document = {
            Database.ID: item.id,
            Database.USER_ID: item.user_id,
            Database.TITLE: item.title,
            Database.CREATION_DATE: item.creation_date,
            Database.PASSAGE: item.passage,
            Database.QUESTIONS: [
                {
                    Database.Q_STATEMENT: question.statement,
                    Database.Q_ANSWER: question.answer
                } for question in item.question_list
            ],
            Database.IS_NEW: item.is_new
        }

        collection = Database.get_collection('reading')
        collection.insert_one(document)

        
    
