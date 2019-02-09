# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 13:23:03 2019

@author: lorenzo
"""

def text2int(textnum, numwords={}):
    if not numwords:
      units = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
      ]

      tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

      scales = ["hundred", "thousand", "million", "billion", "trillion"]

      numwords["and"] = (1, 0)
      for idx, word in enumerate(units):    numwords[word] = (1, idx)
      for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
      for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
          raise Exception("Illegal word: " + word)

        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current


def join_with_and(collection):
    i = 0
    string = ''
    for x in collection:
        if i != 0 and i != len(collection) - 2:
            string += ','
        elif i != 0 and i == len(collection) - 1:
            string += 'and'
        string += x
    return string


def get_beer_list():
    
    file = open("beer_list.txt", "r")
    a = file.readlines()
    file.close()
    return a


