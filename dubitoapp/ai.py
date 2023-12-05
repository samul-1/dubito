import random
from dubitoapp.models import CardsInHand

from dubitoapp.types import GameState


class DubitoAI:
    def __init__(self, game_state: GameState):
        self.game_state = game_state

    def update_state(self, game_state):
        self.game_state = game_state

    # Function to start a new round and decide the rank to call
    def start_round(self):
        print("AI starting round")
        rank_to_call = self._decide_rank_to_call()
        cards_to_play = self._select_cards_to_play()
        return {"action": "play", "rank": rank_to_call, "cards": cards_to_play}

    def play_turn(self):
        print("AI playing turn")
        if self._should_doubt():
            return {"action": "doubt"}

        cards_to_play = self._select_cards_to_play()
        return {"action": "play", "cards": cards_to_play}

    # Function to decide if the AI should doubt
    def _should_doubt(self):
        probability_of_doubting = self._calculate_doubt_probability()
        return random.random() < probability_of_doubting

    # Private function to calculate the probability of doubting
    def _calculate_doubt_probability(self):
        # Basic strategy could involve counting the known cards and estimating the likelihood of a bluff
        num_cards_played = self.game_state["last_amount_played"]
        current_rank = self.game_state["current_rank"]
        cards_in_hand = self.game_state["my_hand"]

        num_same_rank_in_hand = sum(
            1
            for card in cards_in_hand
            if CardsInHand.from_card_string(card)[0] == current_rank
        )  # TODO factor in jokers

        # Simple heuristic: more cards played = higher chance of bluff
        probability_base = num_cards_played / (len(cards_in_hand) + 1)
        # Adjust based on how many cards of the current rank the AI has in its hand
        probability_adjustment = (
            num_same_rank_in_hand / 4
        )  # Assuming a standard deck with 4 suits
        probability_of_doubting = probability_base * (1 - probability_adjustment)

        # Avoid being too predictable
        randomness_factor = random.uniform(0.1, 0.3)
        probability_of_doubting += randomness_factor

        # Cap probability to avoid always or never doubting
        probability_of_doubting = min(0.9, max(0.1, probability_of_doubting))

        return probability_of_doubting

    # Private function to select cards to play
    def _select_cards_to_play(self):
        rank_to_play = self.game_state["current_rank"]
        cards_in_hand = self.game_state["my_hand"]
        valid_cards = [
            card
            for card in cards_in_hand
            if CardsInHand.from_card_string(card)[0] == rank_to_play
        ]

        # make bluffing more likely the less valid cards you have
        should_bluff = random.random() < (1 - len(valid_cards) / 4)

        if not should_bluff and valid_cards:
            # Choose a random number of cards to play that's believable
            num_to_play = random.randint(1, min(3, len(valid_cards)))
            return valid_cards[:num_to_play]

        # Decide to bluff
        if should_bluff or not valid_cards:
            # Select random cards to bluff with
            bluff_cards = [
                card
                for card in cards_in_hand
                if CardsInHand.from_card_string(card)[0] != rank_to_play
            ]
            num_to_play = random.randint(1, min(3, len(bluff_cards)))
            return random.sample(bluff_cards, num_to_play)

        # Default case, should not hit here in a well-formed state
        return []

    # Private function to decide which rank to call at the start of the round
    def _decide_rank_to_call(self):
        all_ranks = [str(n) for n in range(1, 15)]
        cards_in_hand = self.game_state["my_hand"]

        # Frequency table of ranks in hand
        rank_frequency = {rank: 0 for rank in all_ranks}
        for card in cards_in_hand:
            rank_frequency[str(CardsInHand.from_card_string(card)[0])] += 1

        # Select a rank with high frequency in hand, but add some randomness to avoid predictability
        called_rank = max(
            rank_frequency, key=lambda k: rank_frequency[k] + random.uniform(0, 0.5)
        )

        return called_rank
