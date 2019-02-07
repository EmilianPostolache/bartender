import random

import speech_recognition as sr
import spacy
import os
import subprocess

from gtts import gTTS

import pyttsx3


class Bartender:
    STATES = ['new_client', 'waiting_order', 'payment', 'accept_suggestion']
    # INTENTS : 'check_sentence' 'greetings', 'specific_order', 'generic_order', 'suggestion',
    #           'exit', 'end_order', 'delete_order',
    #           'confirmation_payment', 'reorder', 'retry_payment', 'not_understood'

    BEER_LIST = ["ichnusa", "ipa", "blanche", "heineken", "moretti", "peroni",
                 "budweiser", "tuborg", "bavaria", "weiss", "lager", "leffe", "ceres", "corona"]

    WINE_LIST = ["merlot", "pinot"]

    GREETING_QUERIES = ["hello", "hi", "greetings", "good evening", "what's up", "good morning",
                        "good afternoon", "hey", "yo"]

    def __init__(self):
        self.state = 'new_client'
        self.orders = []
        self.suggested_drink = None

    def respond(self, doc):

        if self.state == 'new_client':
            intents = ['check_sentence', 'greetings', 'specific_order', 'suggestion',  'generic_order',
                       'not_understood']
        elif self.state == 'waiting_order':
            intents = ['check_sentence', 'specific_order', 'suggestion',  'generic_order',  'end_order'
                       #'delete_item', 'exit',
                       'not_understood']
        elif self.state == 'accept_suggestion':
            intents = ['check_sentence', 'positive_suggestion']
        elif self.state == 'payment':
            intents = ['check_sentence', 'confirmation_payment', 'exit', 'not_understood']
        for intent in intents:
            answer = getattr(self, intent)(doc)
            if answer:
                return answer

    def check_sentence(self, doc):
        if len(list(doc.sents)) > 1:
            if doc.sents[0].text in self.GREETING_QUERIES:
                return None
            else:
                return 'Please be more specific.'

    def greetings(self, doc):
        # usare l'ora per rispondere
        greeting_1 = ["Hello!", "Hi!", "Greetings!"] # "Good evening!", "Good morning!",
                            #"Good afternoon!"]
        greeting_2 = [". what can I do for you?", ". What would you like?"]
        for sentence in doc.sents:
            if sentence.text not in self.GREETING_QUERIES:
                return None
        self.state = 'waiting_order'
        return random.choice(greeting_1) + random.choice(greeting_2)

    def specific_order(self, doc):
        # spacy returns verbs at ininity form with .lemma_
        ordering_verbs = ["order", "can", "like", "have", "take", "make", "give", "want", "get", "buy", "add"]
        answers_positive = ["would you like to add something else?", "anything else to drink?"]
        answers_negative = ["I'm sorry but we don't have that, would you like something else?"]
        a = random.choice(self.BEER_LIST)
        answers_suggest = ["Unfortunately we ran out of that drink. I can suggest you a fresh "
                           + a + ". Would you like it?"]

        for token in doc:
            # dobbiamo pensare al controllo sul complemento oggeto e piu in la
            # un meccanismo che fa capire se quella parola sia una birra/ un vino (in modo semantico)
            # print(token.tag_, token.head.text, token.lemma_)
            if token.tag_ == "NNP" and token.head.text in ordering_verbs:
                if token.lemma_ in self.BEER_LIST:
                    self.state = 'waiting_order'
                    self.orders.append(token.lemma_)
                    return random.choice(answers_positive)
                else:
                    if random.random() < 0.5:
                        self.state = 'waiting_order'
                        return random.choice(answers_negative)
                    else:
                        self.state = 'accept_suggestion'
                        self.suggested_drink = a
                        return random.choice(answers_suggest)
        return None

    def generic_order(self, doc):
        # spacy returns verbs at ininity form with .lemma_
        ordering_verbs = ["order", "can", "like", "have", "take", "make", "give", "want", "get", "buy", "add"]
        containers = ["drink", "glass",  "pint"]
        generic_drinks = ["wine",  "beer"]
        answers_list = ["We have the following [noun]s: ", "Our selection of [noun] is the following: "]
        answers_negative = ["I'm sorry but we don't have that, would you like something else?"]
        answers_suggest = ["I can suggest you a nice [noun]. Would you like it?"]

        for token in doc:
            # dobbiamo pensare al controllo sul complemento oggeto e piu in la
            # un meccanismo che fa capire se quella parola sia una birra/ un vino (in modo semantico)
            # print(token.tag_, token.head.text, token.lemma_)
            if token.tag_ == "NN" and token.head.text in ordering_verbs:
                if token.lemma_ == "beer":
                    if random.random() < 0.8:
                        self.state = 'waiting_order'
                        answer = random.choice(answers_list)
                        answer = answer.replace("[noun]", "beer")
                        answer = answer + ' '.join(self.BEER_LIST)
                        return answer
                    else:
                        a = random.choice(self.BEER_LIST)
                        self.state = 'accept_suggestion'
                        answer = random.choice(answers_suggest)
                        answer = answer.replace("[noun]", a)
                        self.suggested_drink = a
                        return answer
                if token.lemma_ == "wine":
                    if random.random() < 0.8:
                        self.state = 'waiting_order'
                        answer = random.choice(answers_list)
                        answer = answer.replace("[noun]", "wine")
                        answer = answer + ' '.join(self.WINE_LIST)
                        return answer
                    else:
                        a = random.choice(self.WINE_LIST)
                        self.state = 'accept_suggestion'
                        answer = random.choice(answers_suggest)
                        answer = answer.replace("[noun]", a)
                        self.suggested_drink = a
                        return answer
        return None

    def suggestion(self, doc):
        # aggiungere BE per chiedere cose del tipo "is a good choice",
        # is a [ADJ] idea
        # is a [ADJ] choice
        # is a [ADJ] uggestion
        # give an [ADJ] idea
        # give an [ADJ] choice
        suggestion_verbs = ["advice", "recommend", "suggest", "think", "like"]

        for token in doc:
            # dobbiamo pensare al controllo sul complemento oggeto e piu in la
            # un meccanismo che fa capire se quella parola sia una birra/ un vino (in modo semantico)
            # print(token.tag_, token.head.text, token.lemma_)
            if token.pos_ == "VERB" and token.lemma_ in suggestion_verbs:
                a = random.choice(self.BEER_LIST)
                answers_suggest = ["In my opinion" + a + "is really good. Would you try it?"]
                self.state = 'accept_suggestion'
                self.suggested_drink = a
                return random.choice(answers_suggest)
        return None

    def end_order(self, doc):
        # vedere come aggiungere "that's it", "I'm done", "That's all"
        positive = ['yes', 'positive', 'okay', 'right', 'good', 'yeah', 'yep', 'certainly']
        negative = ['no', "that's it", "it's enough", "that's all", "nothing else", "no more", "nope", "enough"]
        continue_answers = ["what can I do for you?", ". What would you like?"]
        recap_answers = ["So, you have ordered the following: ", "A quick recap of what you've ordered: "]
        payment_answers = ["You have to pay [noun] euros. Proceed with the payment?", "It's [noun] euros. "
                                                                                      "Shall we proceed?"]
        for j in doc:
            if j.text in positive:
                self.state = 'waiting_order'
                return random.choice(continue_answers)
            if (j.text in negative or (j.pos_ == "NOUN" and j.lemma_ == 'payment')
                    or (j.pos_ == "VERB" and j.lemma_ == 'pay')):
                self.state = 'payment'
                # dobbiamo aggiungere prezzi e pezzi
                return random.choice(recap_answers) + ' '.join(self.orders) + random.choice(payment_answers)
        return None

    def confirmation_payment(self, doc):
        # vedere come aggiungere "that's it", "I'm done", "That's all"
        positive = ['yes', 'positive', 'okay', 'right', 'good', 'yeah', 'yep', 'certainly', 'fine']
        negative = ['no', 'nope', 'modify' ]
        # aggiungere plurale quando viene modellato
        finish_answers = ["Here is your drink!", "Enjoy your drink!"]
        negative_answers = ["Ok you can modify your order as you wish.",
                            "You can add or delete any drink from your order.",
                            "Tell me if you wish to remove or add something."]

        for j in doc:
            if j.text in positive:
                self.state = 'new_client'
                return random.choice(finish_answers)
            if j.text in negative:
                self.state = 'waiting_order'
                # dobbiamo aggiungere prezzi e pezzi
                return random.choice(negative_answers)
        return None

    def not_understood(self, doc):
        answers = ["sorry I didn't understood, could you repeat please?",
                   "I didn't get what you said, can you rephrase it?",
                   "what did you mean with that?"]
        return random.choice(answers)

    def positive_suggestion(self, doc):
        positive = ['yes', 'positive', 'okay', 'right', 'good', 'like', 'love', 'cool', 'course']
        for j in doc.text:
            if j in positive:
                self.orders.append(self.suggested_drink)
                self.suggested_drink = None
                self.state = 'waiting_order'
                return "okay, I just added it, would you like to add something?"
        self.suggested_drink = None
        self.state = 'waiting order'
        return "No problem, so what else would you like?"


def get_query():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source)
    text = r.recognize_google(audio)
    nlp = spacy.load('en')
    doc = nlp(text)
    return doc


def main_loop():
    bartender = Bartender()
    while True:
        doc = get_query()
        answer = bartender.respond(doc)
        synthetize_speech(answer)


def synthetize_speech(text):
    tts = gTTS(text=text, lang='en')
    filename = '/tmp/temp.mp3'
    tts.save(filename)
    with open(os.devnull, 'wb') as devnull:
        p = subprocess.check_call(['mpg321', filename], stdout=devnull, stderr=subprocess.STDOUT)
    os.remove(filename)  # remove temperory file


if __name__ == '__main__':
    main_loop()
