from pprint import pprint
from time import time
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


if __name__ == "__main__":
    with open("example_text.txt", encoding="utf-8") as f:
        s = time()
        propabilities = get_words_propabilities(f.read())
        print(time() - s)
    s = time()

    m = MarkovChain(MarkovState(random.choice(list(propabilities.keys()))), history=500)
    for word, prop in propabilities.items():
        state_1 = MarkovState(word)
        for word_2, value in prop.items():
            state_2 = MarkovState(word_2)
            m.add_probability(state_1, state_2, value)
    print(time() - s)

    result = "."
    for word in m:
        if result.count(".") > 5:
            break
        if result.endswith("."):
            word = word.capitalize()
        result += f" {word}"

    print(result[1:])
