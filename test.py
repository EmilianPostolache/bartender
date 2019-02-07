import random

import speech_recognition as sr
import spacy
import os
import subprocess
from gtts import gTTS
import enum


class Bar:
    def __init__(self):
        self.drinks = {}

    def get_drinks(self, category=None):
        if not category:
            lst = []
            for key in self.drinks:
                lst.extend(self.drinks[key])
            return lst
        else:
            return self.drinks[category]

    def get_drink(self, name):
        for drink in self.get_drinks():
            if drink.name == name:
                return drink

    def add_drink(self, drink):
        if drink.category not in self.drinks:
            self.drinks[drink.category] = [drink]
        else:
            self.drinks[drink.category].append(drink)


class Drink:
    CATEGORY = ['beer', 'wine']

    def __init__(self, name, category, price):
        self.name = name
        self.category = category
        self.price = price


class Bartender:
    STATES = ['new_client', 'waiting_order', 'payment', 'accept_suggestion']
    # INTENTS : 'check_sentence' 'greetings', 'specific_order', 'generic_order', 'suggestion',
    #           'exit', 'end_order', 'delete_order', 'confirmation_suggestion'
    #           'confirmation_payment', 'reorder', 'retry_payment', 'not_understood'

    GREETING_QUERIES = ["hello", "hi", "greetings", "good evening", "what's up", "good morning",
                        "good afternoon", "hey", "yo"]

    def __init__(self, bar):
        self.bar = bar
        self.state = 'new_client'
        self.orders = []
        self.suggested_drink = None

    def respond(self, doc):

        if self.state == 'new_client':
            intents = ['check_sentence', 'greetings', 'specific_order', 'suggestion',  'generic_order',
                       'leave', 'not_understood']
        elif self.state == 'waiting_order':
            intents = ['check_sentence', 'specific_order', 'suggestion',  'generic_order',  'end_order',
                       'leave',  'delete_item', 'not_understood']
        elif self.state == 'accept_suggestion':
            intents = ['check_sentence', 'confirmation_suggestion',  'leave',  'not_understood']
        elif self.state == 'payment':
            intents = ['check_sentence', 'confirmation_payment', 'leave', 'not_understood']
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
        a = random.choice(self.bar.get_drinks())

        answers_suggest = ["Unfortunately we ran out of that drink. I can suggest you a fresh "
                           + a.name + ". Would you like it?"]

        # DEBUG
        for token in doc:
            print('text: ' + token.text, 'lemma: ' + token.lemma_, 'tag: ' + token.tag_, 'pos: ' + token.pos_,
                  'head.lemma: ' + token.head.lemma_, sep=' '*10)
            print('\n')

        for token in doc:
            # dobbiamo pensare al controllo sul complemento oggeto e piu in la
            # un meccanismo che fa capire se quella parola sia una birra/ un vino (in modo semantico)
            # print(token.tag_, token.head.text, token.lemma_)
            if token.tag_ == "NNP" and token.head.lemma_ in ordering_verbs:
                if token.lemma_ in [drink.name for drink in self.bar.get_drinks()]:
                    self.state = 'waiting_order'
                    self.orders.append(self.bar.get_drink(token.lemma_))
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
        answers_list = ["We have the following [noun]s: ", "Our selection of [noun] is the following: "]
        answers_negative = ["I'm sorry but we don't have that, would you like something else?"]
        answers_suggest = ["I can suggest you a nice [noun]. Would you like it?"]

        for token in doc:
            # dobbiamo pensare al controllo sul complemento oggeto e piu in la
            # un meccanismo che fa capire se quella parola sia una birra/ un vino (in modo semantico)
            # print(token.tag_, token.head.text, token.lemma_)
            if token.tag_ == "NN" and token.head.text in ordering_verbs:
                for category in Drink.CATEGORY:
                    if token.lemma_ == category:
                        if random.random() < 0.8:
                            self.state = 'waiting_order'
                            answer = random.choice(answers_list)
                            answer = answer.replace("[noun]", category)
                            answer = answer + ' '.join([drink.name for drink in self.bar.get_drinks(category)])
                            return answer
                        else:
                            a = random.choice(self.bar.get_drinks(category))
                            self.state = 'accept_suggestion'
                            answer = random.choice(answers_suggest)
                            answer = answer.replace("[noun]", a.name)
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
        suggestion_verbs = ["advice", "recommend", "suggest", "think"]

        for token in doc:
            # dobbiamo pensare al controllo sul complemento oggeto e piu in la
            # un meccanismo che fa capire se quella parola sia una birra/ un vino (in modo semantico)
            # print(token.tag_, token.head.text, token.lemma_)
            if token.pos_ == "VERB" and token.lemma_ in suggestion_verbs:
                a = random.choice(self.bar.get_drinks())
                answers_suggest = ["In my opinion " + a.name + " is really good. Would you try it?"]
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
        payment_answers = [" You have to pay [noun] euros. Proceed with the payment?", " It's [noun] euros. "
                                                                                      " Shall we proceed?"]
        for token in doc:
            if token.lemma_ in positive:
                self.state = 'waiting_order'
                return random.choice(continue_answers)
            if (token.pos_ == "NOUN" and token.lemma_ == 'payment') or (token.pos_ == "VERB" and token.lemma_ == 'pay'):
                self.state = 'payment'
                recap_answer = random.choice(recap_answers) + ' '.join([drink.name for drink in self.orders])
                payment_answer = random.choice(payment_answers)
                payment_answer = payment_answer.replace('[noun]', sum([drink.price for drink in self.orders]))
                return recap_answer + payment_answer

        for phrase in negative:
            if phrase in doc.text:
                self.state = 'payment'
                recap_answer = random.choice(recap_answers) + ' '.join([drink.name for drink in self.orders])
                payment_answer = random.choice(payment_answers)
                pay = sum([drink.price for drink in self.orders])
                if pay % 1 == 0:
                    pay = int(pay)
                payment_answer = payment_answer.replace('[noun]', str(pay))
                return recap_answer + payment_answer
        return None

    def confirmation_payment(self, doc):
        # vedere come aggiungere "that's it", "I'm done", "That's all"
        positive = ['yes', 'positive', 'okay', 'ok', 'right', 'good', 'yeah', 'yep', 'certainly', 'fine']
        negative = ['no', 'nope', 'modify']
        # aggiungere plurale quando viene modellato
        finish_answers = ["Here is your drink!", "Enjoy your drink!"]
        negative_answers = ["Ok you can modify your order as you wish.",
                            "You can add or delete any drink from your order.",
                            "Tell me if you wish to remove or add something."]

        for phrase in positive:
            if phrase in doc.text:
                self.state = 'new_client'
                return random.choice(finish_answers)
        for phrase in negative:
            if phrase in doc.text:
                self.state = 'waiting_order'
                # dobbiamo aggiungere prezzi e pezzi
                return random.choice(negative_answers)
        return None


    def not_understood(self, doc):
        answers = ["sorry I didn't understood, could you repeat please?",
                   "I didn't get what you said, can you rephrase it?",
                   "what did you mean with that?"]
        return random.choice(answers)

    def leave(self, doc):
        queries = ["don't want to order", "forget it", "nevermind", "changed my mind", "have to go", "leave", "go", "away", "outside"]
        answers = ["I hope we will see you soon!", "Well, goodbye!", "See you next time!"]

        for phrase in queries:
            if phrase in doc.text:
                self.state = "new_client"
                return random.choice(answers)
        return None

    def confirmation_suggestion(self, doc):
        positive = ['yes', 'positive', 'okay', 'right', 'good', 'like', 'love', 'cool', 'course']
        negative = ['no', 'nope', 'modify']
        for j in doc.text:
            if j in positive:
                self.orders.append(self.suggested_drink)
                self.suggested_drink = None
                self.state = 'waiting_order'
                return "okay, I just added it, would you like to add something?"
            if j in negative:
                self.suggested_drink = None
                self.state = 'waiting order'
                return "No problem, so what else would you like?"
        return None

    def delete_item(self, doc):
        query_verbs = ["remove", "delete", "drop"]
        answers = ["I have removed that drink from the order. Do you want to try something different?"]

        for token in doc:
            if (token.tag_ == "NNP" and token.lemma_ in [drink.name for drink in self.orders] and
               token.head.pos_ == "VERB" and token.head.lemma_ in query_verbs):
                self.orders.remove(self.bar.get_drink(token.lemma_))
                return random.choice(answers)

        return None


def get_query():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source)
    text = r.recognize_google(audio)
    #nlp = spacy.load('en_core_web_lg')
    nlp = spacy.load('en')

    doc = nlp(text)
    return doc


def main_loop():
    bar = Bar()
    bar.add_drink(Drink("ichnusa", "beer", 3.))
    bar.add_drink(Drink("ipa", "beer", 5.))
    bar.add_drink(Drink("blanche", "beer", 5.))
    bar.add_drink(Drink("heineken", "beer", 3.))
    bar.add_drink(Drink("moretti", "beer", 3.))
    bar.add_drink(Drink("peroni", "beer", 2.5))
    bar.add_drink(Drink("budweiser", "beer", 3.))
    bar.add_drink(Drink("tuborg", "beer", 2.5))
    bar.add_drink(Drink("bavaria", "beer", 1.))
    bar.add_drink(Drink("franziskaner", "beer", 3.5))
    bar.add_drink(Drink("leffe", "beer", 4.))
    bar.add_drink(Drink("ceres", "beer", 5.))
    bar.add_drink(Drink("ceres", "beer", 5.))

    bar.add_drink(Drink("ichnusa", "beer", 3.))
    bar.add_drink(Drink("ipa", "beer", 5.))
    bar.add_drink(Drink("blanche", "beer", 5.))
    bar.add_drink(Drink("heineken", "beer", 3.))
    bar.add_drink(Drink("moretti", "beer", 3.))
    bar.add_drink(Drink("peroni", "beer", 2.5))
    bar.add_drink(Drink("budweiser", "beer", 3.))
    bar.add_drink(Drink("tuborg", "beer", 2.5))
    bar.add_drink(Drink("bavaria", "beer", 1.))
    bar.add_drink(Drink("franziskaner", "beer", 3.5))
    bar.add_drink(Drink("leffe", "beer", 4.))
    bar.add_drink(Drink("ceres", "beer", 5.))
    bar.add_drink(Drink("ceres", "beer", 5.))

    bar.add_drink(Drink("gotto d'oro", "wine", 1.5))
    bar.add_drink(Drink("nero d'avola", "wine", 7.))
    bar.add_drink(Drink("prosecco DOP", "wine", 10.))

    bartender = Bartender(bar)

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
