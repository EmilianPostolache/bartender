# -*- coding: utf-8 -*-
"""
Created on Thu Feb  7 11:51:16 2019
@author: lorenzo & emilian
"""

import random
import spacy
import os
import subprocess
from utils import text2int, join_with_and
import datetime
import speech_recognition as sr
import numpy as np

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
    STATES = ['new_client', 'waiting_order', 'payment', 'accept_suggestion','number_suggested']
    GREETING_QUERIES = ["hello", "hi", "greetings", "good evening", "what's up", "good morning",
                        "good afternoon", "hey", "yo"]

    def __init__(self, bar):
        self.bar = bar
        self.state = 'new_client'
        self.orders = {}
        self.suggested_drink = None

    def suggest(self,category):     
        #suggest with a probability as high as the price
        probability = []
        count = []
        i = 0
        total_price = 0
        
        for drink in self.bar.get_drinks(category):
            probability.append(drink.price)
            count.append(i)
            i += 1
            total_price = total_price + drink.price
            
        for i,t in enumerate(probability):
            probability[i] = t/total_price
            
        n = np.random.choice(count, p = probability)
        i = 0
        for drink in self.bar.get_drinks(category):
            if i == n:
                return drink
            i += 1
            
        
    def respond(self, doc):        
        if self.state == 'new_client':
            intents = ['check_sentence', 'greetings', 'specific_order', 'suggestion',  'generic_order',
                       'leave', 'not_understood']
        elif self.state == 'waiting_order':
            intents = ['check_sentence', 'specific_order', 'suggestion',  'generic_order',  'end_order',
                       'leave',  'delete_item', 'not_understood']
        elif self.state == 'accept_suggestion':
            intents = ['check_sentence', 'confirmation_suggestion',  'leave',  'not_understood']
        elif self.state == 'number_suggested':
            intents = ['check_sentence', 'get_the_number', 'leave', 'not understood']
        elif self.state == 'payment':
            intents = ['check_sentence', 'confirmation_payment', 'leave', 'not_understood']
        
        for intent in intents:
            answer = getattr(self, intent)(doc)
            if answer:
                #debug
                print(answer)
                return answer
        
        

    def check_sentence(self, doc):       
        if len(list(doc.sents)) > 1:
            if doc.sents[0].text in self.GREETING_QUERIES:
                return None
            else:
                #we want just short sentences
                return random.choice(['Please be more specific.',
                                      'I think this does not make much sense, could you be more precise?',
                                      'This goes beyond my knowledge, what did you mean?'])
                
                
        # DEBUG
        for token in doc:
            print('text: ' + token.text, 'lemma: ' + token.lemma_, 'tag: ' + token.tag_,
                  'pos: ' + token.pos_, 'head.lemma: ' + token.head.lemma_, 'dep_:' + token.dep_, sep=' ' * 4)
            print('\n')

    def greetings(self, doc):      
        now = datetime.datetime.now()
        if now.hour >= 6 and now.hour < 12:
            a = "Good morning"
        elif now.hour >= 12 and now.hour < 19:
            a = "Good afternoon"
        else:
            a = "Good evening"
        greeting_1 = ["Hello!", "Hi!", "Greetings!", a]
        greeting_2 = [". We offer some of the best Earth beers and wine, what do you want to take?",
                      ". I'Bender the bartender, what do you want to order?",
                      ". Welcome to the Life On Mars pub, what can I do for you?"]
        for sentence in doc.sents:
            if sentence.text not in self.GREETING_QUERIES: #first sentence must be a greeting
                return None
        self.state = 'waiting_order'
        return random.choice(greeting_1) + random.choice(greeting_2)

    def specific_order(self, doc):
        # spacy returns verbs at infinity form with .lemma_
        ordering_verbs = ["order", "like", "have", "take", "make", "give", "want", "get", "buy", "add"]
        answers_positive = ["Ok I will add that to the list! Would you like to add something else?",
                            "Got it! Anything else to drink?",
                            "Excellent choice! What else would you like to drink?"]
        answers_partial = ["Ok I will add [noun1] to the list. Unfortunately we don't have [noun2]"]
        answers_suggest = ["I will add [noun1] to the order. Unfortunately we don't have [noun2]. I can suggest you a fresh [noun3]. " +
                           "Would you like it?"]
        b =  ' '.join([drink.name for drink in self.bar.get_drinks(None)]) 
        answers_negative = ["I'm sorry but we don't have that, would you like something else?",
                            "Unfortunately we ran out of that, do you wish to order something else?"
                            "We don't have such a drink, we just have  " + b + "  would you like any of these?" ]
        
        
#       local_order = {}
        bad_items = set()
        ordered_items = {}
        print(list(doc.noun_chunks))
        #noun_chunks:  spacy command which divides 'noun plus the words' describing the noun

        for span in doc.noun_chunks:
            root = span.root
            # penso che il controlo sulla dipendency venga fatto qua, non solo il nsubj potrebbe essere tra
            # parole che non ci interessano
            # non ci deve essere una dipendenza dal root quindi l'ho tolta
            if root.dep_ == 'nsubj': #ex I or Mary , this noun_chunk is not relevant
                continue

            if (((root.pos_ == 'NOUN' or root.pos_ == "PROPN") and root.dep_ == 'dobj' and
                root.head.lemma_ in ordering_verbs) or
                (root.dep_ == 'conj' and (root.head.pos_ == 'NOUN' or root.head.pos_ == "PROPN")) or
                (root.dep_ == 'appos' and (root.head.pos_ == 'NOUN' or root.head.pos_ == "PROPN"))):
            

                print("I'm in!")
                if root.lemma_ in [drink.name for drink in self.bar.get_drinks()]:
                    ordered_items.setdefault(root.lemma_, 0)
                    num = 1
                    for token in span:
                        if token.pos_ == 'NUM' and token.dep_ == 'nummod' and token.head == root: #number
                            try:
                                num = int(token.lemma_)
                            except ValueError:
                                num = text2int(token.lemma_)
                            break
                    ordered_items[root.lemma_] += num #works also with unspecified number = 1
                else:
                    bad_items.add(root.lemma_) #items not in the list

        if ordered_items:
            self.state = 'waiting_order'
            for item in ordered_items:
                self.orders.setdefault(self.bar.get_drink(item), 0)
                self.orders[self.bar.get_drink(item)] += ordered_items[item]

            if not bad_items:
                return random.choice(answers_positive)

            if ordered_items:
                if len(bad_items) > 1:
                    answer_partial = random.choice(answers_partial)

                    noun1 = join_with_and([str(num) + ' ' + item for item, num in ordered_items.items()])
                    noun2 = join_with_and(bad_items)

                    answer_partial.replace('[noun1]', noun1)
                    answer_partial.replace('[noun1]', noun2)
                    return answer_partial

                elif len(bad_items) == 1:
                    self.state = 'accept_suggestion'
                    a =  self.suggest(None)
                    self.suggested_drink = a

                    answer_suggest = random.choice(answers_suggest)
                    noun1 = join_with_and([str(num) + ' ' + item for item, num in ordered_items.items()])

                    answer_suggest.replace('[noun1]', noun1)
                    answer_suggest = answer_suggest.replace("[noun2]", bad_items.pop())
                    answer_suggest = answer_suggest.replace("[noun3]", a.name)
                    return answer_suggest
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
                            a = self.suggest(None)
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

        for token in doc: #look for a suggestion of a certain category
                            
                if (token.tag_ == "NN" and token.lemma_ in Drink.CATEGORY and token.head.pos_ == "VERB"  
                    and token.head.lemma_ in suggestion_verbs):
                    a = self.suggest(token.lemma_)
                    answer_suggest = ["I recommend you a  " + a.name + "  which is an excellent " + token.lemma_ ,
                                      "I advise you a  " + a.name + "  it's really a good one",
                                      "You should try the  " + a.name + "  it's a very typical Earth " + token.lemma_ ]
                    self.state = 'accept_suggestion'
                    self.suggested_drink = a
                    return random.choice(answer_suggest)
                
        for token in doc: #look for a generic suggestion
            
            if token.pos_ == "VERB" and token.lemma_ in suggestion_verbs:

                a =  self.suggest(None)
                answers_suggest = ["In my opinion " + a.name + " is really good. Would you try it?",
                                   "You can't say you have tried the Earth taste until you drink the " + a.name ,
                                   "The " + a.name + " is renowned among terrestrial beings " ]
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
        answers = ["sorry I didn't understood, please rephrase ",
                   "I didn't get what you said, try to say that again",
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
        positive = ['yes', 'positive', 'okay', 'right', 'good', 'like', 'love', 'cool', 'course', 'ok']
        negative = ['no', 'nope', 'modify']
        for token in doc.sents:
            if token.text in positive:
                num = 0
                for j in doc:
                    if j.text == 'a':
                        num = 1
                    if j.pos_ == 'NUM':
                        try:
                            num = int(token.lemma_)
                        except ValueError:
                            num = text2int(token.lemma_)
                        break
                if num != 0:
                    self.orders[self.bar.get_drink(self.suggested_drink.name)] = num
                    self.suggested_drink = None
                    self.state = 'waiting_order'
                    return random.choice["okay, I just added it, would you like to add something?",
                                         "Perfect, anything else?",
                                         "You'll see, it's magnific, do you wish to add something else?"]
                else:
                    self.state = 'number_suggested'
                    print(self.suggested_drink.name)
                    return random.choice(["excellent, how many  " + self.suggested_drink.name + "   do you want?",
                                         "perfect, how many  " + self.suggested_drink.name + "  shoudl I prepare ?"])
            if token.text in negative:
                self.suggested_drink = None
                self.state = 'waiting order'
                return "No problem, so what else would you like?"
        return None
    
    def get_the_number(self, doc):
        num = 0
        for j in doc:
            if j.text == 'a':
                num = 1
            if j.pos_ == 'NUM' or (j.tag_ == 'LS' and j.pos_ == 'PUNCT'):
                try:
                    num = int(j.lemma_)
                except ValueError:
                    num = text2int(j.lemma_)
                break
        if num == 0:
            return "please, specify a number"
        else:
            self.orders[self.bar.get_drink(self.suggested_drink.name)] = num
            self.suggested_drink = None
            self.state = 'waiting_order'
            return random.choice(["nice, would you like to add something?",
                                 "Perfect, anything else?",
                                 "Well done, do you wish to add something else?"])

    def delete_item(self, doc):
        query_verbs = ["remove", "delete", "drop"]
        answers = ["I have removed that drink from the order. Do you want to try something different?"]

        for token in doc:
            if (token.pos_ == "NOUN" and token.lemma_ in [drink.name for drink in self.orders] and
               token.head.pos_ == "VERB" and token.head.lemma_ in query_verbs):
                self.orders.remove(self.bar.get_drink(token.lemma_))
                return random.choice(answers)
            
        return None
    
    def encourage_talk(self):
        answers = ["Don't be shy, we are the best bar on Mars, what do you want to get?",
                   "Whenever you want you can order",
                   "Anytime is a good time to Drink in the Life On Mars pub"]
        return random.choice(answers)


def get_query(bartender, nlp):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        # filtering the audio --> takes 0.5 seconds of preprocessing
        # r.adjust_for_ambient_noise(source)
        # timeout = max number of second wated for a phrase to start
        while True:
            try:
                audio = r.listen(source, timeout=3)
                text = r.recognize_google(audio)
                doc = nlp(text)
                return doc
            except sr.WaitTimeoutError:
                answer = bartender.encourage_talk()
                synthesize_speech(answer)
            except sr.RequestError:
                # API was unreachable or unreasponsive
                print("API UNAVAILABLE")
            except sr.UnknownValueError:
                # speech unintelligible
                print("speech not recognized")


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
    bar.add_drink(Drink("gotto d'oro", "wine", 1.5))
    bar.add_drink(Drink("nero d'avola", "wine", 7.))
    bar.add_drink(Drink("prosecco DOP", "wine", 10.))

    bartender = Bartender(bar)
    nlp = spacy.load('en_core_web_lg')
    # nlp = spacy.load('en')

    while True:
        doc = get_query(bartender, nlp)
        answer = bartender.respond(doc)
        synthesize_speech(answer)


def synthesize_speech(text):
    import sys
    if sys.platform == 'linux':
        from gtts import gTTS
        tts = gTTS(text=text, lang='en')
        filename = '/tmp/tmp.mp3'
        tts.save(filename)
        with open(os.devnull, 'wb') as devnull:
            subprocess.check_call(['mpg321', filename], stdout=devnull, stderr=subprocess.STDOUT)
        os.remove(filename)
    elif sys.platform == 'win32':
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('voice', 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_EN-US_ZIRA_11.0')
        engine.setProperty('rate', 125)
        engine.say(text)
        engine.runAndWait()
    else:
        raise RuntimeError("Your operating system is obsolete!")


if __name__ == '__main__':
    main_loop()

# git add / git commit / git push e pull
