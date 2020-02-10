from markov_chain import MarkovChain, MarkovState
import random


def get_words_propabilities(text: str):
    propabilities = {}
    text = text.split()
    for first_word, second_word in zip(text, text[1:]):
        if first_word in propabilities:
            if second_word in propabilities[first_word]:
                propabilities[first_word][second_word] += 1
            else:
                propabilities[first_word][second_word] = 1
        else:
            propabilities[first_word] = {second_word: 1}

    for key, choices in propabilities.items():
        events = sum(choices.values())
        for k, e in choices.items():
            propabilities[key][k] = e / events
    return propabilities
