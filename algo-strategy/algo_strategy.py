import gamelib
import random
from sys import maxsize


class AlgoStrategy(gamelib.AlgoCore):

    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))
        self.defences_attacked = {}

    def on_game_start(self, config):
        """
        Read in config and perform any initial setup here
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, DONOTBUILD, CORNER
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        DONOTBUILD = []
        CORNER = True
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(
            game_state.turn_number))
        # Comment or remove this line to enable warnings.
        game_state.suppress_warnings(True)

        self.strategy(game_state)

        gamelib.debug_write(self.defences_attacked)

        game_state.submit_turn()

    def detect_right_side_turrets(self, game_state):
        center = [2, 15]
        radius = 3
        locations_to_check = list(filter(lambda x: game_state.game_map.in_arena_bounds(
            x), game_state.game_map.get_locations_in_range(center, radius)))
        turrets = []
        for loc in locations_to_check:
            result_list = game_state.game_map[loc]
            if len(result_list) > 0:
                if result_list[0].unit_type == "DF":
                    turrets.append(loc)
        if any([x[1] == 14 for x in turrets]):
            return 1
        elif any([x[1] == 15 for x in turrets]):
            return 2
        elif any([x[1] == 16 for x in turrets]):
            return 3
        else:
            return -1

    def strategy(self, game_state):
        defend_locations = [[5, 8]]

        if game_state.turn_number == 5:
            if self.detect_right_side_turrets(game_state) not in [-1, 2, 3]:
                CORNER = False

        self.attack_line(game_state)
        self.main_defense(game_state)

        if self.scan1(game_state):
            DONOTBUILD.append([6, 10])
            game_state.attempt_remove(DONOTBUILD)
        elif [6, 10] in DONOTBUILD:
            DONOTBUILD.remove([6, 10])
        self.defend_line(game_state)
        if game_state.turn_number >= 10 and self.suciding(game_state):
            self.stop_suicide(game_state)
        elif game_state.turn_number >= 10 and len(self.miss_defend_line(game_state)) == 0:
            number_enemy_support = self.scan_enemy_for_units(game_state, "EF")
            divisor = max(9 - number_enemy_support, 5)
            game_state.attempt_spawn(INTERCEPTOR, defend_locations[0], int(
                game_state.get_resource(MP, 1) / divisor))

        if not self.suicide(game_state):
            self.attack(game_state)

        self.side_defense(game_state)
        self.save_me(game_state, self.miss_defend_line(game_state))

    def attack(self, game_state):
        attack_location = [14, 0]
        defend_location = [5, 8]
        row_1_spawn = [1, 12]
        row_2_spawn = [2, 11]
        closest_enemy_turret_row = self.detect_right_side_turrets(game_state)

        if self.damage_spawn_location(game_state, attack_location) == 0 and game_state.get_resource(SP, 1) <= 5:
            self.support(game_state)
            if len(self.miss_defend_line(game_state)) == 0:
                game_state.attempt_spawn(SCOUT, attack_location, 1000)
            else:
                self.save_me(game_state, self.miss_defend_line(game_state))
                game_state.attempt_spawn(SCOUT, attack_location, 1000)
        elif game_state.turn_number <= 10:
            if closest_enemy_turret_row == -1 or closest_enemy_turret_row == 3:
                if self.optimal_spawn(game_state):
                    game_state.attempt_spawn(
                        DEMOLISHER, self.optimal_spawn(game_state), 10)
                else:
                    game_state.attempt_spawn(DEMOLISHER, attack_location, 10)
            elif closest_enemy_turret_row == 2:
                if self.optimal_spawn(game_state):
                    game_state.attempt_spawn(DEMOLISHER, row_2_spawn, 10)
                else:
                    game_state.attempt_spawn(DEMOLISHER, attack_location, 10)
            else:
                game_state.attempt_spawn(DEMOLISHER, attack_location, 10)
        elif game_state.turn_number % 3 == 0 and game_state.turn_number <= 20:
            if not self.horizontal(game_state):
                self.vertical(game_state)
            if len(self.miss_defend_line(game_state)) != 0:
                self.save_me(game_state, self.miss_defend_line(game_state))

            if closest_enemy_turret_row == -1 or closest_enemy_turret_row == 3:
                if self.optimal_spawn(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(DEMOLISHER, self.optimal_spawn(
                            game_state), self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(DEMOLISHER, self.optimal_spawn(
                            game_state), self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            elif closest_enemy_turret_row == 2:
                self.support_only_row_1(game_state)
                if self.optimal_spawn(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            else:
                self.support(game_state)
                if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                    game_state.attempt_spawn(
                        DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                    game_state.attempt_spawn(SCOUT, attack_location, 1000)
                else:
                    game_state.attempt_spawn(
                        DEMOLISHER, attack_location, self.demolisher_planner(game_state))
        elif game_state.turn_number % 4 == 0 and game_state.turn_number <= 32:
            if not self.horizontal(game_state):
                self.vertical(game_state)
            if len(self.miss_defend_line(game_state)) != 0:
                self.save_me(game_state, self.miss_defend_line(game_state))
            self.support(game_state)
            if closest_enemy_turret_row == -1 or closest_enemy_turret_row == 3:
                if self.optimal_spawn(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(DEMOLISHER, self.optimal_spawn(
                            game_state), self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(DEMOLISHER, self.optimal_spawn(
                            game_state), self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            elif closest_enemy_turret_row == 2:
                if self.optimal_spawn(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            else:
                if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                    game_state.attempt_spawn(
                        DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                    game_state.attempt_spawn(SCOUT, attack_location, 1000)
                else:
                    game_state.attempt_spawn(
                        DEMOLISHER, attack_location, self.demolisher_planner(game_state))
        elif game_state.turn_number % 4 == 0:
            if not self.horizontal(game_state):
                self.vertical(game_state)
            if len(self.miss_defend_line(game_state)) != 0:
                self.save_me(game_state, self.miss_defend_line(game_state))
            self.support(game_state)
            if self.count_support(game_state) >= 5 and game_state.get_resource(MP) >= 25:
                game_state.attempt_spawn(SCOUT, attack_location, int(
                    game_state.get_resource(MP) / 2))
                game_state.attempt_spawn(SCOUT, [15, 1], 1000)
            if closest_enemy_turret_row == -1 or closest_enemy_turret_row == 3:
                if self.optimal_spawn(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(DEMOLISHER, self.optimal_spawn(
                            game_state), self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(DEMOLISHER, self.optimal_spawn(
                            game_state), self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            elif closest_enemy_turret_row == 2:
                if self.optimal_spawn(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            else:
                if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                    game_state.attempt_spawn(
                        DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                    game_state.attempt_spawn(SCOUT, attack_location, 1000)
                else:
                    game_state.attempt_spawn(
                        DEMOLISHER, attack_location, self.demolisher_planner(game_state))

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to
        estimate the path's damage risk.
        """

        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0))
            damages.append(damage)

        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def damage_spawn_location(self, game_state, location):
        path = game_state.find_path_to_edge(location)
        damage = 0
        for path_location in path:
            damage += len(game_state.get_attackers(path_location, 0))

        return damage

    def most_attacked_turret(self):
        d = self.defences_attacked

        max_loc, max_val = (0, 0)
        for key, values in d.items():
            if values > max_val and values > 0:
                max_loc = key
                max_val = values

        return max_loc

    def build(self, game_state, buildings):
        for building in buildings:
            if building[1] not in DONOTBUILD:
                game_state.attempt_spawn(building[0], building[1])

    def upgrade(self, game_state, buildings):
        for building in buildings:
            if building[2]:
                game_state.attempt_upgrade(building[1])

    def buildupgrade(self, game_state, buildings):
        for building in buildings:
            if building[1] not in DONOTBUILD:
                game_state.attempt_spawn(building[0], building[1])
                if building[2]:
                    game_state.attempt_upgrade(building[1])

    def refund(self, game_state, buildings):
        for building in buildings:
            game_state.attempt_remove([building[1]])

    def scan_enemy_for_units(self, game_state, unit_to_search):
        number_of_units = 0
        for y in range(14, 28):
            for x in range(2, 28):
                if game_state.game_map[x, y]:
                    if game_state.game_map[x, y][0].unit_type == unit_to_search:
                        number_of_units += 1
        return number_of_units

    def repair(self, game_state, buildings):
        need_repair = []
        for building in buildings:
            if game_state.game_map[building[1]]:
                if 2 * game_state.game_map[building[1]][0].health <= game_state.game_map[building[1]][0].max_health and game_state.game_map[building[1]][0].health not in [60, 75]:
                    need_repair.append(building)
        self.refund(game_state, need_repair)

    def attack_line(self, game_state):
        line = [
            [WALL, [15, 2], False],
            [WALL, [14, 2], False],
            [WALL, [13, 3], False],
            [WALL, [12, 4], False],
            [WALL, [11, 5], False],
            [WALL, [10, 6], False],
            [WALL, [9, 7], False],
            [WALL, [8, 8], False],
            [WALL, [7, 9], False],
            [WALL, [6, 10], False],
        ]
        self.build(game_state, line)
        self.repair(game_state, line)

    def defend_line(self, game_state):
        line = [
            [TURRET, [25, 12], True],
            [WALL, [27, 13], False],
            [WALL, [26, 13], False],
            [WALL, [25, 11], False],
            [WALL, [24, 10], False],
            [WALL, [23, 9], True],
            [WALL, [22, 8], True],
            [WALL, [21, 7], False],
            [WALL, [20, 6], False],
            [WALL, [19, 5], False],
            [WALL, [18, 4], False],
            [WALL, [17, 3], False],
            [WALL, [16, 2], False],
        ]
        self.build(game_state, line)
        self.buildupgrade(game_state, line)
        self.repair(game_state, line)

    def main_defense(self, game_state):
        defense = [
            [TURRET, [3, 13], True],
            [WALL, [4, 13], True],
            [TURRET, [3, 12], True],
            [WALL, [4, 12], True],
            [TURRET, [6, 9], True],
            [WALL, [7, 9], True],
            [TURRET, [6, 9], True],
            [WALL, [2, 13], True],
            [WALL, [1, 13], False],
            [WALL, [0, 13], False],
            [WALL, [6, 10], True],
            [TURRET, [7, 8], True],
            [WALL, [8, 8], True],
            [WALL, [9, 7], True],
        ]
        self.buildupgrade(game_state, defense)
        self.repair(game_state, defense)

    def side_defense(self, game_state):
        defense = [
            [TURRET, [25, 12], True],
            [WALL, [25, 13], True],
            [WALL, [24, 12], True],
        ]
        self.buildupgrade(game_state, defense)
        self.repair(game_state, defense)

    def support(self, game_state):
        if CORNER and game_state.turn_number <= 32:
            self.support_only_row_1(game_state)
        else:
            support = [
                [SUPPORT, [1, 12], True],
                [SUPPORT, [2, 12], True],
                [SUPPORT, [3, 10], True],
                [SUPPORT, [4, 10], True],
                [SUPPORT, [4, 9], True],
                [SUPPORT, [2, 11], True],
                [SUPPORT, [3, 11], True],
            ]
            self.buildupgrade(
                game_state, support[:int(game_state.turn_number / 5)])

    def support_only_row_1(self, game_state):
        support = [
            [SUPPORT, [1, 12], True],
            [SUPPORT, [2, 12], True],
            [SUPPORT, [3, 10], True],
            [SUPPORT, [4, 10], True],
            [SUPPORT, [4, 9], True],
        ]
        self.buildupgrade(
            game_state, support[:int(game_state.turn_number / 5)])

    def horizontal(self, game_state):
        x = 4
        y = 14
        data = []
        row = []
        while (len(data) < 3):
            if game_state.game_map[x, y]:
                row.append(game_state.game_map[x, y][0].unit_type)
            else:
                row.append(" ")
            if x == 14:
                y += 1
                x = 4
                data.append(row)
                row = []
            else:
                x += 1

        for i in [0, 1, 2]:
            x = 4
            y = 13
            builds = []
            attack = False
            for loc in data[i]:
                if loc == "DF":
                    y = 11 + i
                    attack = True
                    builds.append(x + 1)
                if loc == "FF" or loc == "EF":
                    if x != 4:
                        builds.append(x)
                    if i == 2:
                        attack = True
                x += 1
            if attack:
                z = 5
                for j in builds:
                    if game_state.get_resource(SP) >= j - z + 1:
                        while (z != j + 1):
                            game_state.attempt_spawn(WALL, [z, y])
                            game_state.attempt_remove([z, y])
                            z += 1
                return True
        return False

    def vertical(self, game_state):
        gamelib.debug_write('Vert')
        if game_state.game_map[3, 14]:
            if game_state.game_map[3, 14][0].unit_type == "DF":
                ver = [[WALL, [5, 12]]]
                self.build(game_state, ver)
                self.refund(game_state, ver)
                return True
        for i in [[2, 14], [3, 15]]:
            if game_state.game_map[i]:
                if game_state.game_map[i][0].unit_type == "DF":
                    ver = [
                        [WALL, [5, 13]],
                        [WALL, [7, 10]],
                        [WALL, [7, 11]],
                        [WALL, [7, 12]],
                        [WALL, [7, 13]],
                    ]
                    self.build(game_state, ver)
                    self.refund(game_state, ver)
                    return True
        for i in [[1, 14], [2, 15], [3, 16], [4, 17]]:
            if game_state.game_map[i]:
                if game_state.game_map[i][0].unit_type == "DF":
                    ver = [
                        [WALL, [6, 11]],
                        [WALL, [6, 12]],
                    ]
                    self.build(game_state, ver)
                    self.refund(game_state, ver)
                    return True
        for i in [[1, 15], [2, 16], [3, 17], [4, 18]]:
            if game_state.game_map[i]:
                if game_state.game_map[i][0].unit_type == "DF":
                    ver = [
                        [WALL, [6, 11]],
                        [WALL, [6, 12]],
                        [WALL, [6, 13]],
                    ]
                    self.build(game_state, ver)
                    self.refund(game_state, ver)
                    return True

    def horizontal(self, game_state):
        x = 4
        y = 14
        data = []
        row = []
        while (len(data) < 3):
            if game_state.game_map[x, y]:
                row.append(game_state.game_map[x, y][0].unit_type)
            else:
                row.append(" ")
            if x == 14:
                y += 1
                x = 4
                data.append(row)
                row = []
            else:
                x += 1

        for i in [0, 1, 2]:
            x = 4
            y = 13
            builds = []
            attack = False
            for loc in data[i]:
                if loc == "DF":
                    y = 11 + i
                    attack = True
                    builds.append(x + 1)
                if loc == "FF" or loc == "EF":
                    if x != 4:
                        builds.append(x)
                    if i == 2:
                        attack = True
                x += 1
            if attack:
                z = 5
                for j in builds:
                    if game_state.get_resource(SP) >= j - z + 1:
                        while (z != j + 1):
                            game_state.attempt_spawn(WALL, [z, y])
                            game_state.attempt_remove([z, y])
                            z += 1
                return True
        return False

    def vertical(self, game_state):
        gamelib.debug_write('Vert')
        if game_state.game_map[3, 14]:
            if game_state.game_map[3, 14][0].unit_type == "DF":
                ver = [[WALL, [5, 12]]]
                self.build(game_state, ver)
                self.refund(game_state, ver)
                return True
        for i in [[2, 14], [3, 15]]:
            if game_state.game_map[i]:
                if game_state.game_map[i][0].unit_type == "DF":
                    ver = [
                        [WALL, [5, 13]],
                        [WALL, [7, 10]],
                        [WALL, [7, 11]],
                        [WALL, [7, 12]],
                        [WALL, [7, 13]],
                    ]
                    self.build(game_state, ver)
                    self.refund(game_state, ver)
                    return True
        for i in [[1, 14], [2, 15], [3, 16], [4, 17]]:
            if game_state.game_map[i] and game_state.turn_number <= 32:
                if game_state.game_map[i][0].unit_type == "DF":
                    ver = [
                        [WALL, [6, 11]],
                        [WALL, [6, 12]],
                    ]
                    self.build(game_state, ver)
                    self.refund(game_state, ver)
                    return True
        ver = [
            [WALL, [6, 11]],
            [WALL, [6, 12]],
            [WALL, [6, 13]],
        ]
        self.build(game_state, ver)
        self.refund(game_state, ver)
        return True

    def scan1(self, game_state):
        x = 4
        y = 14
        while (x <= 14):
            if game_state.game_map[x, y]:
                if game_state.game_map[x, y][0].unit_type == "DF":
                    return True
            x += 1
        return False

    def miss_defend_line(self, game_state):
        x = []
        line = [
            [25, 11],
            [24, 10],
            [23, 9],
            [22, 8],
            [21, 7],
            [20, 6],
            [19, 5],
            [18, 4],
            [17, 3],
            [16, 2],
        ]
        for i in line:
            if not game_state.contains_stationary_unit(i):
                x.append(i)
        return x

    def save_me(self, game_state, list):
        preference = [
            [21, 7],
            [22, 8],
            [20, 6],
            [19, 5],
            [18, 4],
            [17, 3],
            [16, 2],
        ]
        for i in preference:
            if i in list:
                number_enemy_support = self.scan_enemy_for_units(
                    game_state, "EF")
                divisor = max(8 - number_enemy_support, 3)
                game_state.attempt_spawn(INTERCEPTOR, i, int(
                    game_state.get_resource(MP, 1) / divisor))
                break

    def optimal_spawn(self, game_state):
        row_1_spawn = [1, 12]
        row_2_spawn = [2, 11]
        if self.check_blocked(game_state, row_1_spawn):
            return [1, 12]
        elif self.check_blocked(game_state, row_2_spawn):
            return [2, 11]
        return False

    def check_blocked(self, game_state, location):
        if location == [1, 12]:
            to_check = [[1, 12], [2, 12], [2, 11], [3, 11], [4, 11], [5, 11]]
        elif location == [2, 11]:
            to_check = [[2, 11], [3, 11], [4, 11], [5, 11]]
        return all(list(map(lambda x: game_state.contains_stationary_unit(x) is False, to_check)))

    # Returns True if enemy breaking their CORNER walls
    def suicide(self, game_state):
        locations = [[0, 14], [27, 14]]
        for location in locations:
            if game_state.contains_stationary_unit(location):
                if game_state.game_map[location][0].unit_type == "FF" and game_state.game_map[location][0].pending_removal:
                    reinforce = [
                        [TURRET, [26, 12], True],
                        [WALL, [27, 13], False],
                        [WALL, [26, 13], False],
                    ]
                    self.buildupgrade(game_state, reinforce)
                    return True
        return False

    def suciding(self, game_state):
        locations = [[0, 14], [27, 14]]
        for location in locations:
            if not game_state.contains_stationary_unit(location) and game_state.get_resource(MP, 1) >= 6:
                reinforce = [
                    [TURRET, [26, 12], True],
                    [WALL, [27, 13], False],
                    [WALL, [26, 13], False],
                ]
                self.buildupgrade(game_state, reinforce)
                return True
        return False

    def stop_suicide(self, game_state):
        if game_state.get_resource(MP) >= 9:
            defend_location = [5, 8]
            row_2_spawn = [2, 11]
            if not self.horizontal(game_state):
                self.vertical(game_state)
            self.support(game_state)
            closest_enemy_turret_row = self.detect_right_side_turrets(
                game_state)
            if closest_enemy_turret_row in [-1, 2, 3]:
                if self.optimal_spawn(game_state):
                    game_state.attempt_spawn(DEMOLISHER, row_2_spawn, 1000)
                else:
                    game_state.attempt_spawn(DEMOLISHER, defend_location, 1000)
            else:
                game_state.attempt_spawn(DEMOLISHER, defend_location, 1000)

    def demolisher_planner(self, game_state):
        center = [7, 17]
        radius = 6
        locations = list(filter(lambda x: (game_state.game_map.in_arena_bounds(
            x) and x[0] <= 13), game_state.game_map.get_locations_in_range(center, radius)))
        turret_counts = 0
        for loc in locations:
            result_list = game_state.game_map[loc]
            if len(result_list) > 0:
                if result_list[0].unit_type == "DF":
                    turret_counts += 2
        if game_state.get_resource(SP, 1) >= 8:
            turret_counts += 1
        return turret_counts + 2

    def count_support(self, game_state):
        center = [10, 9]
        radius = 15
        locations_to_check = list(filter(lambda x: (game_state.game_map.in_arena_bounds(
            x) and x[1] <= 13), game_state.game_map.get_locations_in_range(center, radius)))
        support_count = 0
        for loc in locations_to_check:
            result_list = game_state.game_map[loc]
            if len(result_list) > 0:
                if result_list[0].unit_type == "EF":
                    support_count += 1
        return support_count


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
