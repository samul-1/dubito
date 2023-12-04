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
