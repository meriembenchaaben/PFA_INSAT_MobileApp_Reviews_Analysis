# -*- coding: utf-8 -*-


# Commented out IPython magic to ensure Python compatibility.
# %tensorflow_version 2.x 
import tensorflow as tf

print(tf.__version__)

from flask import Flask, jsonify, request
from flask_restplus import Api, Resource, fields
import numpy as np
import pandas as pd
from flask_swagger_ui import get_swaggerui_blueprint
import re
import nltk
import string

pd.options.mode.chained_assignment = None
from sklearn.preprocessing import LabelBinarizer, LabelEncoder
from sklearn.metrics import confusion_matrix
from tensorflow import keras
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from keras import backend as K
from flask_swagger import swagger
import pickle

# from google.colab import drive
# drive.mount('/content/gdrive')


exclude = set(string.punctuation)
import re

# creating the flask app
flask_app = Flask(__name__)
app = Api(app=flask_app)

name_space = app.namespace('main', description='Main APIs')
modelReview = app.model('Review',
                        {'subject': fields.String(required=True,
                                                  description="review title"
                                                  ),
                         'body': fields.String(required=True,
                                               description="review body"
                                               ),
                         })


def remove_punctuation(x):
    """ Helper function to remove punctuation from a string x: any string """
    try:
        x = re.sub(r"[-+]?[0-9]+(\.[0-9]+)?", "", x)
        y = ''.join(ch for ch in x if ch not in exclude)
    except:
        pass
    return y


from nltk.stem.porter import PorterStemmer

stemmer = PorterStemmer()


def stem_words(text):
    return " ".join([stemmer.stem(word) for word in text.split()])


# Reference : https://gist.github.com/slowkow/7a7f61f495e3dbb7e3d767f97bd7304b
def remove_emoji(string):
    string = str(string)
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


#import emoji
from nltk.corpus import stopwords


# STOPWORDS = set({'an', "you'll", "it's", 'each', 'at', 'ain', "mustn't", 'we', 'mightn', 'here', 'from', 'he', 'between', 'no', "haven't", 'to', 'how', "aren't", 'wouldn', 'didn', 'same', 'won', "should've", 'isn', 'both', 'did', 'weren', 'a', "wouldn't", 'ourselves', "you've", 'i', 'such', 'is', 'don', 'them', 'this', 'mustn', 'your', 'further', 'which', 'should', 'himself', 'over', 'most', 'out', 'does', 'am', 'those', 'by', "shouldn't", 'do', 'shouldn', 'be', 'there', "that'll", "won't", "shan't", 'own', "doesn't", 'ma', "isn't", 'all', 'then', 'she', 'hers', 'until', 'after', 'but', 've', 'our', 'if', 'about', 'can', 'her', 'these', 'again', "hasn't", 'nor', 'him', "you'd", 'where', 'with', "she's", 'on', 'of', 'other', 'very', 'ours', 'during', 't', 'had', 'because', "weren't", 'yourselves', 'than', "hadn't", 'me', 'doing', 'against', 'now', 'doesn', 'wasn', 'too', 'you', 'what', 'd', 're', "didn't", 'myself', 'his', "needn't", 'are', 'under', 'off', 'herself', 'up', 'some', 'itself', 'been', 'were', 'through', 'when', 'as', 'for', 'who', 'theirs', 'so', 'below', 'll', 'hadn', 'shan', 'any', 'its', 'and', 'in', "mightn't", 'before', 'while', 'that', 'has', 'yours', 'it', 'down', 'my', 'whom', 'their', 'few', "couldn't", 'hasn', 'why', "you're", 'or', 'haven', 'needn', 's', "don't", 'couldn', 'above', 'm', 'being', 'only', 'y', 'will', 'the', 'once', 'into', 'having', 'aren', 'more', 'themselves', 'have', 'just', 'o', 'was', "wasn't", 'they', 'not', 'yourself'})
# print(STOPWORDS)
# def remove_stopwords(text):
#    """custom function to remove the stopwords"""
#    return " ".join([word for word in str(text).split() if word not in STOPWORDS])

def preprocessing(review):
    review = review.lower()
    review = remove_emoji(review)
    review = remove_punctuation(review)
    # review = remove_stopwords(review)
    review = stem_words(review)
    return review


def f1(y_true, y_pred):
    def recall(y_true, y_pred):
        """Recall metric.

        Only computes a batch-wise average of recall.

        Computes the recall, a metric for multi-label classification of
        how many relevant items are selected.
        """
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
        recall = true_positives / (possible_positives + K.epsilon())
        return recall

    def precision(y_true, y_pred):
        """Precision metric.

        Only computes a batch-wise average of precision.

        Computes the precision, a metric for multi-label classification of
        how many selected items are relevant.
        """
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
        precision = true_positives / (predicted_positives + K.epsilon())
        return precision

    precision = precision(y_true, y_pred)
    recall = recall(y_true, y_pred)
    return 2 * ((precision * recall) / (precision + recall + K.epsilon()))


def recall(y_true, y_pred):
    """Recall metric.

        Only computes a batch-wise average of recall.

        Computes the recall, a metric for multi-label classification of
        how many relevant items are selected.
        """
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    recall = true_positives / (possible_positives + K.epsilon())
    return recall


def precision(y_true, y_pred):
    """Precision metric.

        Only computes a batch-wise average of precision.

        Computes the precision, a metric for multi-label classification of
        how many selected items are relevant.
        """
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    return precision


def f1_loss(y_true, y_pred):
    tp = K.sum(K.cast(y_true * y_pred, 'float'), axis=0)
    tn = K.sum(K.cast((1 - y_true) * (1 - y_pred), 'float'), axis=0)
    fp = K.sum(K.cast((1 - y_true) * y_pred, 'float'), axis=0)
    fn = K.sum(K.cast(y_true * (1 - y_pred), 'float'), axis=0)

    p = tp / (tp + fp + K.epsilon())
    r = tp / (tp + fn + K.epsilon())

    f1 = 2 * p * r / (p + r + K.epsilon())
    f1 = tf.where(tf.is_nan(f1), tf.zeros_like(f1), f1)
    return 1 - K.mean(f1)


model = keras.models.load_model("models/ModelNoBugsFinal.h5",
                                custom_objects={'f1': f1, 'precision': precision, 'recall': recall})

classes = ['Advertising', 'Battery', 'Camera & Photos', 'Complexity',
           'Connectivity & HDMI', 'Customer Support', 'Design & UX', 'Devices',
           'Feature Requests', 'Frequency', 'Gaming', 'Import Export',
           'Internationalization', 'Location Services', 'Notifications & Alerts',
           'Operating System', 'Performance', 'Pricing & Payment', 'Privacy',
           'Security & Accounts', 'Sign Up & Login', 'Social & Collaboration',
           'Streaming & Video & Audio', 'Update']

# subject = input("Subject = ")
# body= input ("Body = ")
# review = preprocessing(subject=subject,body=body)

# print (review)

transformer = TfidfTransformer()
loaded_vec = CountVectorizer(decode_error="replace", vocabulary=pickle.load(open("models/feature.pkl", "rb")))


# tfidfReview = transformer.fit_transform(loaded_vec.fit_transform(np.array([review])))
def reviewPrediction(review) :
    review = review.lower()
    reviews = re.split(',|and|\.|&', review)
    review = preprocessing(review)
    topics = set()
    for item in predict(model, review):
        topics.add(item)
    for r in reviews:
        smalltopics = predict(model, r)
        for item in smalltopics:
            topics.add(item)
    return topics
def predict(model, review):
    tfidfReview = transformer.fit_transform(loaded_vec.fit_transform(np.array([review])))
    mask = model.predict(tfidfReview.toarray()) > 0.3
    x = np.array(classes)[mask[0]]
    if len(x) == 0:
        if np.max(np.array(model.predict(tfidfReview.toarray()))) > 0.2:
            return [classes[np.argmax(np.array(model.predict(tfidfReview.toarray())))]]
        else:
            return []
    return x


# print(predict(model,tfidfReview))

# print(model.predict(tfidfReview.toarray()))
@name_space.route("/")
class PredictionController(Resource):

    # corresponds to the GET request.
    # this function is called whenever there
    # is a GET request for this resource
    @app.doc(responses={200: 'OK'})
    def get(self):
        return jsonify({'message': 'Prediction test working'})

        # Corresponds to POST request

    @app.doc(responses={200: 'OK'})
    @app.expect(modelReview)
    def post(self):
        # status code

        review = request.json["subject"] + " " + request.json["body"]
        Topics = reviewPrediction(review)
        return {
            "topics": Topics
        }


# driver function
if __name__ == '__main__':
    flask_app.run(debug=True)
