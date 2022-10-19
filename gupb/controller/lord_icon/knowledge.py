import numpy as np
from gupb.controller.lord_icon.distance import Point2d, heuristic
from gupb.controller.lord_icon.weapons import ALL_WEAPONS

from gupb.model.arenas import Arena
from gupb.model import arenas, characters, coordinates

from typing import NamedTuple
from collections import defaultdict


LAND_MAPPER = defaultdict(
    lambda: 1, {"land": 20, "sea": 5, "wall": 10, "menhir": 100, "self": 100}
)

FACING_MAPPER = {
    characters.Facing.UP: 10,
    characters.Facing.LEFT: 20,
    characters.Facing.RIGHT: 30,
    characters.Facing.DOWN: 40,
}

WEAPON_MAPPER = defaultdict(
    lambda: 0,
    {
        "knife": 1,
        "axe": 2,
        "bow": 5,
        "sword": 3,
    },
)


class CharacterInfo(NamedTuple):
    health: int
    weapon: str
    position: Point2d
    facing: characters.Facing

    @staticmethod
    def from_tile(tile, position):
        return CharacterInfo(
            health=tile.character.health,
            # weapon=tile.character.weapon.name,
            weapon="bow",
            position=position,
            facing=tile.character.facing,
        )

    def distance(self, other):
        return heuristic(self.position, other.position)

    def get_attack_range(self, map):
        if self.weapon in ALL_WEAPONS:
            return ALL_WEAPONS[self.weapon].get_attack_range(
                map, self.facing, self.position
            )
        return []

    def can_attack(self, map, position):
        return position in self.get_attack_range(map)

    def predict_move(self, map):
        face_x, face_y = self.facing.value
        x, y = self.position
        predicted_moves = [self.position]
        if map[x + face_x, y + face_y] == LAND_MAPPER["land"]:
            predicted_moves.append((x + face_x, y + face_y))

        return predicted_moves

    def predict_attack_range(self, map):
        points = []
        for position in self.predict_move(map):
            points += CharacterInfo(
                health=self.health,
                weapon=self.weapon,
                position=position,
                facing=self.facing,
            ).get_attack_range(map)

        for facing in [self.facing.turn_left(), self.facing.turn_right()]:
            points += CharacterInfo(
                health=self.health,
                weapon=self.weapon,
                position=self.position,
                facing=facing,
            ).get_attack_range(map)
        return points


def parse_coords(coord):
    return (
        (coord.x, coord.y)
        if isinstance(coord, coordinates.Coords)
        else (coord[0], coord[1])
    )


class Knowledge:
    def __init__(self):
        self.arena = None

        self.character = None
        self.enemies = []

        self.dynamic_map = None
        self.dmg_map = None
        self.map = None
        self.possible_moves = None
        self.possible_dmg = None
        self.items = None

        self.time = 0

    def update(self, knowledge: characters.ChampionKnowledge) -> None:
        self.dynamic_map = np.roll(self.dynamic_map, 1, axis=0)
        self.dynamic_map[0] = 0
        self.possible_moves[:] = 0
        self.possible_dmg[:] = 0
        self.items[:] = 0
        self.enemies = []
        self.dmg_map = np.where(self.dmg_map > 0, self.dmg_map - 0.5, 0)

        self.position = knowledge.position.x, knowledge.position.y
        self.alive_enemies = knowledge.no_of_champions_alive - 1

        for coord, tile in knowledge.visible_tiles.items():
            x, y = parse_coords(coord)

            if self.position == (x, y):
                self.character = CharacterInfo.from_tile(tile, (x, y))
            else:
                if tile.character:
                    self.enemies.append(CharacterInfo.from_tile(tile, (x, y)))

            if tile.type == "menhir":
                self.map[x, y] = LAND_MAPPER["menhir"]

            if "mist" in [t.type for t in tile.effects]:
                self.dmg_map[x, y] = 1

            if tile.loot:
                self.items[x, y] = WEAPON_MAPPER[tile.loot.name]

        for enemy in self.enemies:
            x, y = enemy.position

            self.dynamic_map[0, x, y] = FACING_MAPPER[enemy.facing]

            self.possible_moves[x, y] = 1
            for (x, y) in enemy.predict_move(self.map):
                self.possible_moves[x, y] = 1

            for (x, y) in enemy.predict_attack_range(self.map):
                self.dmg_map[x, y] = 1

        for (x, y) in self.character.get_attack_range(self.map):
            self.possible_dmg[x, y] = 1

        self.time += 1

        # import matplotlib.pyplot as plt
        # plt.imshow(self.map, cmap="gray")
        # plt.show()
        # plt.imshow(self.possible_moves, cmap="gray")
        # plt.show()
        # plt.imshow(self.dmg_map, cmap="gray")
        # plt.show()
        # plt.imshow(self.dynamic_map[0] - self.dynamic_map[1] + 50.0, cmap="gray")
        # plt.show()
        # plt.imshow(self.dmg_map.T, cmap="gray")
        # plt.show()
        # import time
        # time.sleep(1)

    def reset(self, arena_name):
        self.arena = Arena.load(arena_name)
        n, m = self.arena.size
        self.map = np.ones((n, m))
        self.dynamic_map = np.zeros((2, n, m))
        self.dmg_map = np.zeros((n, m))
        self.possible_moves = np.zeros((n, m))
        self.possible_dmg = np.zeros((n, m))
        self.items = np.zeros((n, m))

        for position, tile in self.arena.terrain.items():
            self.map[position.x, position.y] = LAND_MAPPER[
                tile.description().type
            ]

        self.time = 0
