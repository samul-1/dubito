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
        cards_to_play = self._select_cards_to_play(start_round=True)
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
        stack_length = self.game_state["stack_length"]

        # TODO factor in stack length and how many cards of the called rank the player has already played

        num_same_rank_in_hand = sum(
            1
            for card in cards_in_hand
            if CardsInHand.from_card_string(card)[0] == current_rank
        )  # TODO factor in jokers

        # Simple heuristic: more cards played = higher chance of bluff
        probability_base = (
            num_cards_played / 8
        )  # TODO make dependent on how many decks are used

        # Adjust based on how many cards of the current rank the AI has in its hand
        probability_adjustment = (
            num_same_rank_in_hand / 8
        )  # TODO make dependent on how many decks are used

        probability_of_doubting = (
            (0.55 * probability_base)
            + (0.3 * probability_adjustment)
            + (0.1 * sum(0.05 for _ in range(stack_length)))
        )

        # Avoid being too predictable
        randomness_factor = random.uniform(-0.15, 0.15)
        probability_of_doubting += randomness_factor

        # Cap probability to avoid always or never doubting
        probability_of_doubting = min(0.9, max(0.1, probability_of_doubting))

        return probability_of_doubting

    # Private function to select cards to play
    def _select_cards_to_play(self, start_round=False):
        rank_to_play = self.game_state["current_rank"]
        cards_in_hand = self.game_state["my_hand"]

        jokers_in_hand = [card for card in cards_in_hand if CardsInHand.is_joker(card)]

        my_hand_rank_frequency = {
            rank: len(
                [
                    card
                    for card in cards_in_hand
                    if CardsInHand.from_card_string(card)[0] == rank
                ]
            )
            for rank in range(1, 15)
        }

        valid_cards = [
            card
            for card in cards_in_hand
            if CardsInHand.from_card_string(card)[0] == rank_to_play
        ]

        should_play_joker_if_no_valid_cards = (
            len(jokers_in_hand) and random.random() < 0.5
        )

        can_win = all(
            [
                CardsInHand.from_card_string(card)[0] == rank_to_play
                or CardsInHand.is_joker(card)
                for card in cards_in_hand
            ]
        )

        # if player can win, never bluff
        if can_win:
            should_bluff = False

        else:
            bluff_probability = min(
                0.1,
                abs(
                    1
                    - (
                        # the more valid cards you have, the less likely you are to bluff
                        len(valid_cards)
                        / 8  # TODO make dependent on how many decks are used
                        # the higher the number of ranks with low frequency in hand, the more likely you are to bluff
                        + sum(
                            0.005
                            for rank in my_hand_rank_frequency
                            if my_hand_rank_frequency[rank] > 2
                        )
                    )
                    + random.uniform(0, 0.15)
                ),
            )
            should_bluff = random.random() < bluff_probability

        if not should_bluff and (valid_cards or should_play_joker_if_no_valid_cards):
            if valid_cards:
                # Choose a random number of cards to play that's believable
                num_to_play = (
                    random.randint(1, min(4, len(valid_cards)))
                    if not can_win
                    else len(cards_in_hand)
                )
                playable_cards = valid_cards if not can_win else cards_in_hand
                return playable_cards[:num_to_play]

            # play a joker if no valid cards
            return jokers_in_hand[:1]

        # Decide to bluff
        else:
            # Select random cards to bluff with
            bluff_cards = [
                card
                for card in cards_in_hand
                if CardsInHand.from_card_string(card)[0] != rank_to_play
            ]
            num_to_play = random.randint(1, min(4, len(bluff_cards)))
            return random.sample(bluff_cards, num_to_play)

    # Private function to decide which rank to call at the start of the round
    def _decide_rank_to_call(self):
        current_rank = self.game_state["current_rank"]
        all_ranks = [str(n) for n in range(1, 15)]
        cards_in_hand = self.game_state["my_hand"]

        # Frequency table of ranks in hand
        rank_frequency = {rank: 0 for rank in all_ranks}
        for card in cards_in_hand:
            rank_frequency[str(CardsInHand.from_card_string(card)[0])] += 1

        # Select a rank with high frequency in hand, but add some randomness to avoid predictability
        called_rank = max(
            [r for r in rank_frequency if r != current_rank],
            key=lambda k: rank_frequency[k] + random.uniform(0, 0.5),
        )

        return called_rank
