# Actions that are implemented in the game
class CatanGame:
    def __init__(self, board, harbours, players, intersections, roads, placements):

        self.board = board
        self.harbours = harbours
        self.players = players
        self.intersections = intersections
        self.roads = roads 
        self.placements = placements
        self.COSTS = {
            "road": {"wood": 1, "brick": 1},
            "settlement": {"wood": 1, "brick": 1, "sheep": 1, "wheat": 1},
            "city": {"wheat": 2, "ore": 3},
            "devcard": {"sheep": 1, "wheat": 1, "ore": 1}
        }

        self.current_player_index = 0
        self.logs = []

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


    def move_robber(self, tile_index):
        if tile_index < 0 or tile_index >= len(self.board):
            return False, "Invalid tile"
        
        self.robber_tile = tile_index

        return True, "Robber moved"

    def distribute_resources(self, dice_number, robber_tile):
        if dice_number == 7:
            return [] 

        events = []

        for hex_index, tile in enumerate(self.board):
            if tile.get("number") == dice_number:
                res = tile.get("type")
                if res == "desert":
                    continue
                if hex_index == robber_tile:
                    continue

                for iv in self.intersections:
                    if hex_index in iv.get("adjacentHexes", []):
                        p_index = iv.get("occupiedBy")

                        if p_index is None:
                            continue

                        if isinstance(p_index, str):
                            p_str = p_index.strip()
                            if p_str == "" or p_str.lower() == "None":
                                continue
                            
                            try:
                                p_index = int(p_str)
                            except ValueError:
                                continue

                        try:
                            p_index = int(p_index)
                        except Exception:
                            continue

                    
                        if p_index < 0 or p_index >= len(self.players):
                            continue

                        player = self.players[p_index]

                        is_city = (iv.get("type") == "city") or (iv.get("building") == "city")

                        amount = 2 if is_city else 1

                        if res not in player.get("resources", {}):
                            player.setdefault("resources", {}).setdefault(res, 0)

                        player["resources"][res] += amount
                        events.append(f"{player['name']} receives {amount} {res}")
        return events


    def can_afford(self, player, item):
        cost = self.COSTS[item]
        return all(player["resources"][r] >= cost[r] for r in cost)

    def pay_cost(self, player, item):
        cost = self.COSTS[item]
        for r in cost:
            player["resources"][r] -= cost[r]


    def build_settlement(self, player_index, intersection_id):
        pl = self.players[player_index]
        iv = self.intersections[intersection_id]

        if iv["occupiedBy"] != "None":
            return False, "Intersection already taken"

        for nid in iv.get("neighbors", []):
            neighbor = self.intersections[nid]
            if neighbor["occupiedBy"] != "None":
                return False, "Too close to another settlement"

        connected = False
        for r in self.roads:
            if r["player"] == player_index and (
                r["a"] == intersection_id or r["b"] == intersection_id
            ):
                connected = True
                break

        if not connected:
            return False, "Settlement must connect to your road"


        if not self.can_afford(pl, "settlement"):
            return False, "Cannot afford settlement"

        self.pay_cost(pl, "settlement")
        pl["settlements_left"] -= 1
        pl["victory_points"] += 1
        iv["occupiedBy"] = player_index
        iv["type"] = "settlement"
        if iv["harbor"] != "None":
            pl["harbours"].append(iv["harbor"])

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
        connected = False

        for iv in self.intersections:
            if iv["occupiedBy"] == player_index:
                if iv["id"] == a or iv["id"] == b:
                    connected = True
                    break

        if not connected:
            for r in self.roads:
                if r["player"] == player_index and (
                    r["a"] == a or r["b"] == a or r["a"] == b or r["b"] == b
                ):
                    connected = True
                    break

        if not connected:
            return False, "Road must connect to your road or settlement"
        
        iva = self.intersections[a]
        ivb = self.intersections[b]

        if (iva["occupiedBy"] not in ("None", player_index) or
            ivb["occupiedBy"] not in ("None", player_index)):
            return False, "Cannot build road into opponent settlement"
        
        self.pay_cost(pl, "road")
        pl["roads_left"] -= 1
        self.roads.append({"player": player_index, "a": a, "b": b})
        return True, "Road built"


    def distribute_initial_resources(self, placements):

        events = []

        if not placements:
            return events 

        last_by_player = {}
        for rec in placements:
            p = int(rec.get("player"))
            inter = int(rec.get("intersection"))
            last_by_player[p] = inter

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

 