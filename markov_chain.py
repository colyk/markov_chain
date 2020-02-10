import random
from numbers import Number
from typing import Dict, Iterator, Tuple, Union


class MarkovState:
    def __init__(self, data):
        self.data = data

    def __eq__(self, other):
        return self.data == other.data

    def __hash__(self):
        return hash(self.data)

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return f"MarkovState({self.data})"


class MarkovChain:
    def __init__(
        self,
        begin_state,
        probabilities: Dict[
            Tuple[MarkovState, MarkovState], Union[Dict, Number]
        ] = None,
        history=1,
    ):
        self._begin_state = begin_state
        self._probabilities = probabilities or {}
        self._states = {state1 for state1, _ in self._probabilities} | {
            state2 for _, state2 in self._probabilities
        }
        self._n_history = history
        self._nothing_state = MarkovState(None)
        self._history = self._initial_history()

    @staticmethod
    def get_words_propabilities(text: str) -> Dict:
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
    @property
    def current_state(self):
        return self._history[-1]

    @current_state.setter
    def current_state(self, value):
        self._history = self._history[1:] + [value]

    def reset(self):
        self.current_state = self._begin_state

    def add_probability(
        self, state_1, state_2, probability: Union[Dict, Number], last_states=None
    ):
        if last_states is None:
            self._probabilities[(state_1, state_2)] = probability
        else:
            if (state_1, state_2) not in self._probabilities.keys():
                self._probabilities[(state_1, state_2)] = dict()

            root = self._probabilities[(state_1, state_2)]
            for state in last_states[:-1]:
                root[state] = {}
                root = root[state]

            root[last_states[-1]] = probability

    def __iter__(self):
        return self

    def __next__(self):
        try:
            next_possible_states, next_possible_probabilities = zip(
                *self._next_possible_states_and_probabilities()
            )
        except ValueError:
            self.reset()
            return self._begin_state

        next_state = self._get_next_possible_state(
            next_possible_states, next_possible_probabilities
        )
        self.current_state = next_state
        return next_state.data

    def _next_possible_states_and_probabilities(self):
        return [
            (state2, probability)
            for (state1, state2), probability in self._probabilities.items()
            if self.current_state == state1
        ]

    def _initial_history(self):
        return [self._nothing_state] * (self._n_history - 1) + [self._begin_state]

    def _get_probabilities_for_current_history(self, probabilities, history=None):
        if history is None:
            history = self._history

        if not isinstance(probabilities, dict):
            return probabilities

        if len(history) == 0:
            raise ValueError(
                "empty history (too long probability data): " + str(probabilities)
            )

        for last_state, probability in probabilities.items():
            if history[0] == last_state:
                if isinstance(probability, Number):
                    return probability

                return self._get_probabilities_for_current_history(
                    probability, history[1:]
                )
            elif history[0] == self._nothing_state:
                return 0

        return 0

    def _get_next_possible_state(
        self, next_possible_states, next_possible_probabilities
    ) -> MarkovState:
        next_possible_probabilities: Iterator[Number] = map(
            self._get_probabilities_for_current_history, next_possible_probabilities
        )
        return random.choices(
            next_possible_states, weights=next_possible_probabilities
        )[0]

if __name__ == "__main__":
    with open("example_text.txt", encoding="utf-8") as f:
        propabilities = MarkovChain.get_words_propabilities(f.read())

    init_word = random.choice(list(propabilities.keys()))
    mc = MarkovChain(MarkovState(init_word), history=5000)
    for word, prop in propabilities.items():
        state_1 = MarkovState(word)
        for word_2, value in prop.items():
            state_2 = MarkovState(word_2)
            mc.add_probability(state_1, state_2, value)

    sentence_count = 3
    words_treshold = sentence_count * 25
    result = "."
    for word in mc:
        if result.count(".") > sentence_count:
            break
        if result.endswith("."):
            word = word.capitalize()
        result += f" {word}"

    print(f"Started from word: {init_word}\n{result[1:]}")