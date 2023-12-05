from typing import TypedDict


class Player(TypedDict):
    number: int
    is_online: bool
    hand_length: int
    name: str


class GameState(TypedDict):
    stack_length: int
    my_hand: list[str]
    my_player_number: int
    players: list[Player]
    last_turn_player_number: int
    current_rank: str
    last_rank: str
    last_amount_played: int
    winner_player_number: int
    current_turn_player_number: int


def consumer_game_state_to_game_state(consumer_game_state: dict) -> GameState:
    return {
        "stack_length": consumer_game_state.get("number_of_stacked_cards", 0),
        "my_hand": consumer_game_state["my_cards"],
        "my_player_number": consumer_game_state["my_player_number"],
        "last_turn_player_number": consumer_game_state["last_turn"],
        "current_rank": consumer_game_state["current_card"],
        "last_rank": consumer_game_state["last_card"],
        "last_amount_played": consumer_game_state["last_amount_played"],
        "winner_player_number": consumer_game_state.get("won_by", -1),
        "current_turn_player_number": consumer_game_state.get("current_turn", -1),
        "players": [
            {
                "number": player["number"],
                "is_online": player["is_online"],
                "hand_length": player["number_of_cards"],
                "name": player["name"],
            }
            for player in consumer_game_state["other_players_data"]
        ],
    }
