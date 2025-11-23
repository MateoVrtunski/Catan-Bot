# action.py — Core Catan game logic
import random

# ====================================================================
#  Catan Game State
# ====================================================================
class CatanGame:
    def __init__(self, board, harbours, players, intersections, roads, placements):
        """
        board: list of 19 hex tiles {type, number}
        harbours: list of 9 harbour objects
        players: list of player dicts created with CatanGame.create_player()
        intersections: list of intersection dicts:
            {id, adjacentHexes, neighbors, occupiedBy, type}
        """
        self.board = board
        self.harbours = harbours
        self.players = players
        self.intersections = intersections
        self.roads = roads  # {player, a, b}
        self.placements = placements
        self.COSTS = {
            "road": {"wood": 1, "brick": 1},
            "settlement": {"wood": 1, "brick": 1, "sheep": 1, "wheat": 1},
            "city": {"wheat": 2, "ore": 3},
            "devcard": {"sheep": 1, "wheat": 1, "ore": 1}
        }

        self.dev_card_deck = self.generate_dev_deck()
        self.current_player_index = 0
        self.logs = []

    # ----------------------------------------------------------------
    # Player Factory
    # ----------------------------------------------------------------
    @staticmethod
    def create_player(name, color):
        return {
            "name": name,
            "color": color,
            "resources": {
                "wood": 0,
                "brick": 0,
                "sheep": 0,
                "wheat": 0,
                "ore": 0
            },
            "settlements_left": 3,
            "cities_left": 4,
            "roads_left": 13,
            "victory_points": 2,
            "dev_cards": [],
            "harbours": []
        }

    # ====================================================================
    #  Development Cards
    # ====================================================================
    def generate_dev_deck(self):
        deck = (
            ["knight"] * 14 +
            ["victory"] * 5 +
            ["road_building"] * 2 +
            ["monopoly"] * 2 +
            ["year_of_plenty"] * 2
        )
        random.shuffle(deck)
        return deck

    # ====================================================================
    #  Dice & Resource Distribution
    # ====================================================================
    def distribute_resources(self, dice_number):
        """Distribute resources to all players based on dice number"""
        if dice_number == 7:
            return []  # robber logic not implemented yet

        events = []

        for hex_index, tile in enumerate(self.board):
            if tile.get("number") == dice_number:
                res = tile.get("type")
                if res == "desert":
                    continue

                for iv in self.intersections:
                    if hex_index in iv.get("adjacentHexes", []):
                        p_index = iv.get("occupiedBy")
                        if p_index is not None:
                            player = self.players[p_index]
                            amount = 2 if iv.get("type") == "city" else 1
                            player["resources"][res] += amount
                            events.append(f"{player['name']} receives {amount} {res}")
        return events

    def roll_dice(self):
        d = random.randint(1, 6) + random.randint(1, 6)
        self.logs.append(f"Dice rolled: {d}")
        events = [] if d == 7 else self.distribute_resources(d)
        self.logs.extend(events)
        return {"dice": d, "events": events}

    # ====================================================================
    #  Resource & Cost Helpers
    # ====================================================================
    def can_afford(self, player, item):
        cost = self.COSTS[item]
        return all(player["resources"][r] >= cost[r] for r in cost)

    def pay_cost(self, player, item):
        cost = self.COSTS[item]
        for r in cost:
            player["resources"][r] -= cost[r]

    # ====================================================================
    #  Building Methods
    # ====================================================================
    def build_settlement(self, player_index, intersection_id):
        pl = self.players[player_index]
        iv = self.intersections[intersection_id]

        if iv["occupiedBy"] is not None:
            return False, "Intersection already taken"

        # check spacing (no adjacent settlements)
        for nid in iv.get("neighbors", []):
            neighbor = self.intersections[nid]
            if neighbor["occupiedBy"] is not None:
                return False, "Too close to another settlement"

        if not self.can_afford(pl, "settlement"):
            return False, "Cannot afford settlement"

        self.pay_cost(pl, "settlement")
        pl["settlements_left"] -= 1
        pl["victory_points"] += 1
        iv["occupiedBy"] = player_index
        iv["type"] = "settlement"
        return True, "Settlement built"

    def build_city(self, player_index, intersection_id):
        pl = self.players[player_index]
        iv = self.intersections[intersection_id]

        if iv["occupiedBy"] != player_index:
            return False, "You do not own this settlement"
        if iv["type"] != "settlement":
            return False, "Must upgrade a settlement"

        if not self.can_afford(pl, "city"):
            return False, "Cannot afford city"

        self.pay_cost(pl, "city")
        pl["cities_left"] -= 1
        pl["settlements_left"] += 1
        pl["victory_points"] += 1
        iv["type"] = "city"
        return True, "City built"

    def build_road(self, player_index, a, b):
        pl = self.players[player_index]

        if not self.can_afford(pl, "road"):
            return False, "Cannot afford road"

        self.pay_cost(pl, "road")
        pl["roads_left"] -= 1
        self.roads.append({"player": player_index, "a": a, "b": b})
        return True, "Road built"

    # ====================================================================
    #  Trading
    # ====================================================================
    def bank_trade(self, player_index, give, receive):
        pl = self.players[player_index]
        rate = 4
        if "3:1" in pl["harbours"]:
            rate = 3
        if give in pl["harbours"]:
            rate = 2

        if pl["resources"][give] < rate:
            return False, f"Need {rate} {give}"

        pl["resources"][give] -= rate
        pl["resources"][receive] += 1
        return True, f"Traded {rate} {give} for 1 {receive}"

    def player_trade(self, A, B, offer, request):
        pA = self.players[A]
        pB = self.players[B]

        # verify offer/request
        for r, amt in offer.items():
            if pA["resources"][r] < amt:
                return False, "Player A cannot afford trade"
        for r, amt in request.items():
            if pB["resources"][r] < amt:
                return False, "Player B cannot afford trade"

        # execute trade
        for r, amt in offer.items():
            pA["resources"][r] -= amt
            pB["resources"][r] += amt
        for r, amt in request.items():
            pB["resources"][r] -= amt
            pA["resources"][r] += amt

        return True, "Trade complete"

    # ====================================================================
    #  Initial Resource Distribution
    # ====================================================================
    def distribute_initial_resources(self, placements):
        """
        Give starting resources ONLY from each player's second settlement.
        placements = [{player:int, intersection:int}, ...] in chronological order
        """

        events = []

        if not placements:
            return events  # do nothing if somehow empty

        # Determine the last (2nd) settlement for each player
        last_by_player = {}
        for rec in placements:
            p = int(rec.get("player"))
            inter = int(rec.get("intersection"))
            last_by_player[p] = inter

        # Give resources from the last settlement only
        for p_index, inter_id in last_by_player.items():
            if inter_id < 0 or inter_id >= len(self.intersections):
                continue

            iv = self.intersections[inter_id]

            for hi in iv.get("adjacentHexes", []):
                tile = self.board[hi]
                res = tile.get("type")
                if res != "desert":
                    self.players[p_index]["resources"][res] += 1
                    events.append(f"{self.players[p_index]['name']} receives 1 {res}")
        return events

 