from collections import defaultdict, deque
from queue import Queue
import random
from typing import List

import numpy as np

from gupb import controller
from gupb.controller.lord_icon.distance import Point2d, dist, find_path
from gupb.controller.lord_icon.knowledge import WEAPON_MAPPER, Knowledge
from gupb.controller.lord_icon.move import MoveController
from gupb.controller.lord_icon.strategy import StrategyController
from gupb.model import arenas, characters, coordinates
from gupb.model.arenas import Arena
from gupb.model.weapons import WeaponDescription

mapper = defaultdict(lambda: 1)
mapper["land"] = 0
mapper["menhir"] = 0

POSSIBLE_ACTIONS = [
    characters.Action.TURN_LEFT,
    characters.Action.TURN_RIGHT,
    characters.Action.STEP_FORWARD,
    characters.Action.ATTACK,
]


class LordIcon(controller.Controller):
    def __init__(self, first_name: str) -> None:
        self.first_name: str = first_name

        # Movement
        self.current_direction = None

        # Knowledge
        self.knowledge = Knowledge()

        # Memory
        self.memory = deque(maxlen=10000)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LordIcon):
            return self.first_name == other.first_name
        return False

    def __hash__(self) -> int:
        return hash(self.first_name)

    def decide(
        self, knowledge: characters.ChampionKnowledge
    ) -> characters.Action:
        self.knowledge.update(knowledge)

        # action = StrategyController.decide(self.knowledge)
        # if action:
        #     return action
        self.create_state()

        return characters.Action.TURN_LEFT
        return random.choice(POSSIBLE_ACTIONS)

    def create_state(self):
        features = [
            self.knowledge.map / 255,
            (
                self.knowledge.dynamic_map[0]
                - self.knowledge.dynamic_map[1]
                + 50.0
            )
            / 255,
            self.knowledge.dmg_map,
            self.knowledge.possible_moves,
            self.knowledge.possible_dmg,
            self.knowledge.items / 5,
        ]
        features = np.expand_dims(features, axis=-1)
        conv = np.concatenate(features, axis=-1)
        stats = np.array(
            [
                self.knowledge.character.health,
                self.knowledge.character.position[0] * 1.0 / self.knowledge.map.shape[0],
                self.knowledge.character.position[1] * 1.0 / self.knowledge.map.shape[1],
                self.knowledge.character.facing.value[0] + 1,
                self.knowledge.character.facing.value[1] + 1,
                WEAPON_MAPPER[self.knowledge.character.weapon] / 5.0,
                self.knowledge.time / 100.0,
                self.knowledge.alive_enemies * 0.1,
            ]
        )
        return {
            "conv": conv,
            "stats": stats
        }

    def praise(self, score: int) -> None:
        pass

    def reset(self, arena_description: arenas.ArenaDescription) -> None:
        self.knowledge.reset(arena_description.name)

    @property
    def name(self) -> str:
        return f"Marek łowca wiertarek {self.first_name}"

    @property
    def preferred_tabard(self) -> characters.Tabard:
        return characters.Tabard.YELLOW
