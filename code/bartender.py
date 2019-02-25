# -*- coding: utf-8 -*-
"""
Created on Thu Feb  7 11:51:16 2019
@author: lorenzo & emilian
"""

import random

from bar import Drink
from utils import text2int, join_with_and, debug
import datetime
import numpy as np
from enum import Enum


class Bartender:

    class States(Enum):
        NEW_CLIENT = 1
        WAITING_ORDER = 2
        PAYMENT = 3
        ACCEPT_SUGGESTION = 4
        NUMBER_SUGGESTED = 5
        DELETE_NUMBER = 6

    def __init__(self, bar):
        self.bar = bar
        self.state = self.States.NEW_CLIENT
        self.orders = {}
        self.suggested_drink = None
        self.known_drinks = {}

        for category in Drink.CATEGORY:
            with open("../res/" + category + "_list.txt", "r") as file:
                a = file.readlines()
                self.known_drinks[category] = [line.strip().lower() for line in a]

    def get_drink_list(self, category):
        return self.known_drinks[category]

    def suggest(self, ordered_items=None, category=None):
        # suggest with a probability as high as the price

        if ordered_items:
            drinks = list(set(self.bar.get_drinks(category)) - ordered_items.keys())
        else:
            drinks = self.bar.get_drinks(category)

        prices = np.array([drink.price for drink in drinks])
        probability = 1. / np.sum(prices)*prices
        return np.random.choice(drinks, p=probability)

    def respond(self, doc):
        debug(doc)
        intents = []  # [self.check_sentence]
        if self.state is self.States.NEW_CLIENT:
            intents.extend([self.greetings, self.specific_order, self.generic_order, self.suggestion])
        elif self.state is self.States.WAITING_ORDER:
            intents.extend([self.specific_order, self.generic_order, self.suggestion, self.delete_item, self.end_order])
        elif self.state is self.States.PAYMENT:
            intents.extend([self.confirmation_payment, self.delete_item])
        elif self.state is self.States.ACCEPT_SUGGESTION:
            intents.append(self.confirmation_suggestion)
        elif self.state is self.States.NUMBER_SUGGESTED:
            intents.append(self.get_the_number)
        elif self.state is self.States.DELETE_NUMBER:
            intents.append(self.removal_number)

        intents.append(self.leave)
        intents.append(self.not_understood)

        for intent in intents:
            answer = intent(doc)
            if answer:
                return answer

    def greetings(self, doc):
        greeting_queries = ["hello", "hi", "greetings", "good evening", "what's up", "good morning",
                            "good afternoon", "hey", "yo"]

        now = datetime.datetime.now()
        if 6 <= now.hour < 12:
            a = "Good morning"
        elif 12 <= now.hour < 19:
            a = "Good afternoon"
        else:
            a = "Good evening"
        greeting_1 = ["Hello!", "Hi!", "Greetings!", a]
        greeting_2 = [". We offer some of the best Earth beers and wine, what do you want to take?",
                      ". I'm Bender the bartender, what do you want to order?",
                      ". Welcome to the Life On Mars pub, what can I do for you?"]

        for token in doc:
            if token.pos_ == 'VERB':
                return None

        for greeting in greeting_queries:
            if greeting in doc.text:
                self.state = self.States.WAITING_ORDER
                return random.choice(greeting_1) + random.choice(greeting_2)

    def specific_order(self, doc):
        # spacy returns verbs at infinity form with .lemma_
        ordering_verbs = ["order", "like", "have", "take", "make", "give", "want", "get", "buy", "add"]
        answers_positive = ["Ok I will add that to the list! Would you like to add something else?",
                            "Got it! Anything else to drink?",
                            "Excellent choice! What else would you like to drink?"]
        answers_partial = ["Ok I will add [noun1] to the list. Unfortunately we don't have [noun2]"]
        answers_suggest = ["I will add [noun1] to the order. Unfortunately we don't have [noun2]." +
                           " I can suggest you a fresh [noun3]." +
                           " Would you like it?"]
        answers_negative = ["I'm sorry but we don't have [noun1], would you like something else?",
                            "Unfortunately we ran out of [noun1], do you wish to order something else?",
                            "We don't have [noun1]! [noun2]! Would you like any of these?",
                            "Sorry but we are out of [noun1],  [noun2]."]

        bad_items = {}  # set()
        ordered_items = {}

        print(list(doc.noun_chunks))
        # noun_chunks:  spacy command which divides 'noun plus the words' describing the noun
        for span in doc.noun_chunks:
            root = span.root
            if root.dep_ == 'nsubj':  # ex I or Mary , this noun_chunk is not relevant
                continue

            if (((root.pos_ == 'NOUN' or root.pos_ == "PROPN") and root.dep_ == 'dobj' and
               root.head.lemma_ in ordering_verbs) or
               (root.dep_ == 'conj' and (root.head.pos_ == 'NOUN' or root.head.pos_ == "PROPN")) or
               (root.dep_ == 'appos' and (root.head.pos_ == 'NOUN' or root.head.pos_ == "PROPN"))):

                long_name = []
                num = 1
                for child in root.children:
                    if child.dep_ == 'compound':
                        long_name.append(child.text)
                    if child.pos_ == 'NUM' and child.dep_ == 'nummod':
                        try:
                            num = int(child.lemma_)
                        except ValueError:
                            num = text2int(child.lemma_)
                        break

                long_name.append(root.lemma_)
                composed_name = ''
                for n, i in enumerate(long_name):
                    if n == len(long_name) - 1:
                        composed_name = composed_name + i
                    else:
                        composed_name = composed_name + i + ' '

                composed_name = composed_name.lower()

                if composed_name in [drink.name for drink in self.bar.get_drinks()]:
                    ordered_items.setdefault(composed_name, 0)
                    ordered_items[composed_name] += num  # works also with unspecified number = 1

                else:
                    for category in Drink.CATEGORY:
                        if composed_name in self.get_drink_list(category):
                            bad_items[composed_name] = category  # add(composed_name)  # items not in the list
                # ASSICURARSI CHE VA BENE CON CASI IN CUI NON FA IL MATCH...

        if ordered_items:
            self.state = self.States.WAITING_ORDER
            for item in ordered_items:
                self.orders.setdefault(self.bar.get_drink(item), 0)
                self.orders[self.bar.get_drink(item)] += ordered_items[item]

            if not bad_items:
                return random.choice(answers_positive)

            if len(bad_items) > 1:
                answer_partial = random.choice(answers_partial)

                noun1 = join_with_and([str(num) + ' ' + item for item, num in ordered_items.items()])
                noun2 = join_with_and(bad_items.keys())

                answer_partial = answer_partial.replace('[noun1]', noun1)
                answer_partial = answer_partial.replace('[noun2]', noun2)
                return answer_partial

            elif len(bad_items) == 1:
                self.state = self.States.ACCEPT_SUGGESTION
                bad_item = list(bad_items.keys())[0]
                a = self.suggest(ordered_items, category=bad_items[bad_item])
                self.suggested_drink = a

                answer_suggest = random.choice(answers_suggest)
                noun1 = join_with_and([str(num) + ' ' + item for item, num in ordered_items.items()])

                answer_suggest = answer_suggest.replace('[noun1]', noun1)
                answer_suggest = answer_suggest.replace("[noun2]", bad_item)
                answer_suggest = answer_suggest.replace("[noun3]", a.name)
                return answer_suggest

        elif len(bad_items) > 1:
            self.state = self.States.WAITING_ORDER
            answer_negative = random.choice(answers_negative)
            noun2 = join_with_and(bad_items.keys())
            answer_negative = answer_negative.replace("[noun1]", noun2)
            ordered_categories = list(bad_items.values())
            drink_list = ''
            for cat in ordered_categories:
                intro = 'Our list of  ' + cat + 's is the following: '
                drink_list = drink_list + intro + join_with_and([drink.name for drink in self.bar.get_drinks(cat)])
            answer_negative = answer_negative.replace("[noun2]", drink_list)
            return answer_negative

    def generic_order(self, doc):
        ordering_verbs = ["order", "can", "like", "have", "take", "make", "give", "want", "get", "buy", "add"]
        answers_list = ["We have the following [noun]s: ", "Our selection of [noun] is the following: "]
        answers_suggest = ["I can suggest you a nice [noun]. Would you like it?"]
        probability = 0.8

        enter = False
        for token in doc:
            if token.lemma_ in ordering_verbs:
                enter = True
            if enter and token.lemma_ in Drink.CATEGORY:

                if random.random() < probability:
                    self.state = self.States.WAITING_ORDER
                    answer = random.choice(answers_list)
                    answer = answer.replace("[noun]", token.lemma_)
                    answer = answer + join_with_and([drink.name for drink in self.bar.get_drinks(token.lemma_)])
                    return answer
                else:
                    a = self.suggest(category=token.lemma_)
                    self.state = self.States.ACCEPT_SUGGESTION
                    answer = random.choice(answers_suggest)
                    answer = answer.replace("[noun]", a.name)
                    self.suggested_drink = a
                    return answer

    def suggestion(self, doc):
        suggestion_verbs = ["advice", "recommend", "suggest", "think"]
        support_verbs = ["give", "be"]
        support_nouns = ["advice", "idea", "suggestion", "choice", "recommendation"]
        answer_suggest_cat = ["I recommend you a [noun1] which is an excellent [noun2]. Would you try it?",
                              "You should try the [noun1] it's a very typical Earth [noun2]. Will you get a taste?"]
        answers_suggest = ["In my opinion [noun1] is a really good [noun2]. Do you want it??",
                           "You can't say you have tried the Earth taste until you drink the [noun1]. " +
                           "Would you try it?",
                           "The [noun1] is renowned among terrestrial beings to be a terrific [noun2]. " +
                           "Shall I add it?"]
        enter = False
        for token in doc:  # look for a suggestion of a certain category
            if token.lemma_ in suggestion_verbs:
                enter = True
            if token.lemma_ in support_verbs:
                for child in token.children:
                    if (child.dep_ == 'dobj' or child.dep_ == 'attr') and child.lemma_ in support_nouns:
                        enter = True
        if enter:
            for token in doc:
                if token.lemma_ in Drink.CATEGORY:
                    enter2 = True
                    a = self.suggest(token.lemma_)
                    self.state = self.States.ACCEPT_SUGGESTION
                    self.suggested_drink = a
                    answer = random.choice(answer_suggest_cat)
                    answer = answer.replace('[noun1]', a.name)
                    answer = answer.replace('[noun2]', token.lemma_)
                    return answer

            # entra quando non e' stata trovata una categoria (consiglio generico)
            a = self.suggest()
            self.state = self.States.ACCEPT_SUGGESTION
            self.suggested_drink = a
            answer = random.choice(answers_suggest)
            answer = answer.replace('[noun1]', a.name)
            answer = answer.replace('[noun2]', a.category)
            return answer

    def end_order(self, doc):
        positive = ['yes', 'positive', 'okay', 'right', 'good', 'yeah', 'yep', 'certainly', 'sure']
        negative = ['no', "that's it", "it's enough", "that's all", "nothing else", "no more", "nope", "enough"]
        continue_answers = ["what can I do for you?", ". What would you like?"]
        recap_answers = ["So, you have ordered   [noun1] ", "A quick recap of what you've ordered:   [noun1] "]
        payment_answers = [" which amounts to [noun] euros. Proceed with the payment?",
                           " that makes a total of [noun] euros. Shall we proceed?"]
        nothing_ordered = ["Well that's not gonna cost anything since your order is empty..."+
                           " do you intend to actually order something?",
                           "your order is empty, do you intend to actually order something?",
                           "are you gonna order for real?"]
        for token in doc:
            if token.lemma_ in positive:
                self.state = self.States.WAITING_ORDER
                return random.choice(continue_answers)
            if (token.pos_ == "NOUN" and token.lemma_ == 'payment') or (token.pos_ == "VERB" and token.lemma_ == 'pay'):
                self.state = self.States.PAYMENT
                recap_answer = random.choice(recap_answers)
                noun1 = join_with_and([str(num) + ' ' + drink.name for drink,num in self.orders.items()])
                recap_answer = recap_answer.replace("[noun1]", noun1)
                payment_answer = random.choice(payment_answers)
                pay = sum([n*drink.price for drink,n in self.orders.items()])
                if pay % 1 == 0:
                    pay = int(pay)
                if pay == 0:
                    self.state = self.States.WAITING_ORDER
                    return random.choice(nothing_ordered)
                payment_answer = payment_answer.replace('[noun]', str(pay))
                return recap_answer + payment_answer

        for phrase in negative:
            if phrase in doc.text:
                self.state = self.States.PAYMENT
                recap_answer = random.choice(recap_answers)
                noun1 = join_with_and([str(num) + ' ' + drink.name for drink,num in self.orders.items()])
                recap_answer = recap_answer.replace("[noun1]", noun1)
                payment_answer = random.choice(payment_answers)
                pay = sum([n*drink.price for drink,n in self.orders.items()])
                if pay % 1 == 0:
                    pay = int(pay)
                if pay == 0:
                    self.state = self.States.WAITING_ORDER
                    return random.choice(nothing_ordered)
                payment_answer = payment_answer.replace('[noun]', str(pay))
                return recap_answer + payment_answer
            
        return None

    def confirmation_payment(self, doc):
        # vedere come aggiungere "that's it", "I'm done", "That's all"
        positive = ['yes', 'positive', 'okay', 'ok', 'right', 'good', 'yeah', 'yep', 'certainly', 'fine', 'sure']
        negative = ['no', 'nope', 'modify']
        # aggiungere plurale quando viene modellato
        finish_answers = ["Here is your drink!", "Enjoy your drink!"]
        negative_answers = ["Ok you can modify your order as you wish.",
                            "You can add or delete any drink from your order.",
                            "Tell me if you wish to remove or add something."]

        for phrase in positive:
            if phrase in doc.text:
                self.state = self.States.NEW_CLIENT
                return random.choice(finish_answers)
        for phrase in negative:
            if phrase in doc.text:
                self.state = self.States.WAITING_ORDER
                # dobbiamo aggiungere prezzi e pezzi
                return random.choice(negative_answers)
        return None

    def not_understood(self, doc):
        answers = ["sorry I didn't understood, please rephrase ",
                   "I didn't get what you said, try to say that again",
                   "what did you mean with that?"]
        return random.choice(answers)

    def leave(self, doc):
        queries = ["don't want to order", "forget it", "nevermind", "changed my mind", "have to go", "leave", "go",
                   "away", "outside"]
        answers = ["I hope we will see you soon!", "Well, goodbye!", "See you next time!"]

        for phrase in queries:
            if phrase in doc.text:
                self.state = self.States.NEW_CLIENT
                return random.choice(answers)
        return None

    def confirmation_suggestion(self, doc):
        positive = ['yes', 'positive', 'okay', 'right', 'good', 'like', 'love', 'cool', 'course', 'ok', 'sure']
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
                    self.state = self.States.WAITING_ORDER
                    return random.choice["okay, I just added it, would you like to add something?",
                                         "Perfect, anything else?",
                                         "You'll see, it's magnific, do you wish to add something else?"]
                else:
                    self.state = self.States.NUMBER_SUGGESTED
                    print(self.suggested_drink.name)
                    return random.choice(["excellent, how many  " + self.suggested_drink.name + "   do you want?",
                                         "perfect, how many  " + self.suggested_drink.name + "  shoudl I prepare ?"])
            if token.text in negative:
                self.suggested_drink = None
                self.state = self.States.WAITING_ORDER
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
            self.state = self.States.WAITING_ORDER
            return random.choice(["nice, would you like to add something?",
                                  "Perfect, anything else?",
                                  "Well done, do you wish to add something else?"])
                        
    def removal_number(self, doc):
        answers = ["I have removed [noun1] .",
                   "As you wish, so i deleted [noun1], ",
                   "No problem  [noun1] have been succesfully removed, "]
        not_ans = ["please, specify the number of [noun1] to be removed"]
        recap = [" so far you have ordered [noun2],  do you wish to add or remove something?"]
        invalid_delete = ["This is not a valid cancellation, how many [noun] do you want to cancel?",
                          "can't do it, you have taken less than that, how many [noun] do you want to remove?"]

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
            not_an = random.choice(not_ans)
            not_an = not_an.replace("[noun1]", self.remove_item)
            return 
        else:
            old_n = self.orders[self.bar.get_drink(self.remove_item)]
            if (old_n - num) < 0:
                inv_delete = random.choice(invalid_delete)
                return inv_delete.replace("[noun]", self.remove_item )
            self.orders[self.bar.get_drink(self.remove_item)] = old_n - num
            self.state = self.States.WAITING_ORDER
            noun1 = str(num) + ' ' + self.remove_item
            answer1 = random.choice(answers)
            answer1 = answer1.replace('[noun1]', noun1) 
            answer2 = random.choice(recap)
            noun2 = join_with_and([str(num) + ' ' + drink.name for drink,num in self.orders.items()])
            answer2 = answer2.replace("[noun2]", noun2)
            answer = answer1 + answer2
            self.remove_item = None
            return answer
            

    def delete_item(self, doc):
        # don't want, change, switch
        query_verbs = ["remove", "delete", "drop"]
        answers = ["I have removed [noun1] .",
                   "As you wish, so i deleted [noun1], ",
                   "No problem  [noun1] have been succesfully removed, "]
        not_ordered_sen1 = ["I'm confused, you didn't order any [noun1] , "]
        recap = [" so far you have ordered [noun2],  do you wish to add or remove something?"]
        incomplete_sents = ["Okay, but please, tell me how many ",
                            "Yes I can do that, how many shall I remove ?"]
        invalid_delete = ["This is not a valid cancellation, you have not taken so many, will you delete or add something properly?",
                          "can't do it, you have taken less than that, are you going to add or delete something propery?"]

        removed_items = {}
        enter = False

        for token in doc:
            if ((token.pos_ == "NOUN" or token.pos_ == "PROPN") and token.lemma_ in [drink.name for drink in self.orders] and
                token.head.pos_ == "VERB" and token.head.lemma_ in query_verbs):
                enter = True

                for span in doc.noun_chunks:
                    root = span.root

                    if root.dep_ == 'nsubj':  # ex I or Mary , this noun_chunk is not relevant
                        continue
                    
                    if root.lemma_ == token.lemma_:
                        num = 0
                        remove_item = token.lemma_
                        for token in span:
                            if token.pos_ == 'NUM' and token.dep_ == 'nummod' and token.head == root:  # number
                                try:
                                    num = int(token.lemma_)
                                except ValueError:
                                    num = text2int(token.lemma_)
                                break
                            elif token.lemma_ == 'a':
                                num = 1
                        old_n = self.orders[self.bar.get_drink(root.lemma_)]
                        if (old_n - num > 0):
                            self.orders[self.bar.get_drink(root.lemma_)] = old_n - num
                            removed_items[root.lemma_] = num
                        else:
                            return random.choice(invalid_delete)
                    
                
            elif ((token.pos_ == "NOUN" or token.pos_ == "PROPN") and token.lemma_ in [drink.name for drink in self.bar.get_drinks()] and
                token.head.pos_ == "VERB" and token.head.lemma_ in query_verbs):
                not_ordered1 = random.choice(not_ordered_sen1)
                not_ordered1 = not_ordered1.replace("[noun1]", token.lemma_) #stops at first item not ordered
                not_ordered2 = random.choice(recap)
                noun2 = join_with_and([str(num) + ' ' + drink.name for drink,num in self.orders.items()])
                not_ordered2 = not_ordered2.replace("[noun2]", noun2)
                not_ordered = not_ordered1 + not_ordered2
                return not_ordered

        if enter:
            if num == 0: 
            #the number of items to be deleted is not specified, works only for one item
                self.remove_item = remove_item
                self.state = self.States.DELETE_NUMBER
                return random.choice(incomplete_sents)
            else:
                noun1 = join_with_and([str(num) + ' ' + item for item, num in removed_items.items()])
                answer1 = random.choice(answers)
                answer1 = answer1.replace('[noun1]', noun1) #should do a recap of the order
                answer2 = random.choice(recap)
                noun2 = join_with_and([str(num) + ' ' + drink.name for drink,num in self.orders.items()])
                answer2 = answer2.replace("[noun2]", noun2)
                answer = answer1 + answer2
                return answer
        return None
    
    def encourage_talk(self):
        answers = ["Don't be shy, we are the best bar on Mars, what do you want to get?",
                   "Whenever you want you can order",
                   "Anytime is a good time to Drink in the Life On Mars pub"]
        return random.choice(answers)
