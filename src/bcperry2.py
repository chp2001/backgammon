from src.strategies import Strategy
from src.piece import Piece
from src.compare_all_moves_strategy import CompareAllMoves
from src.colour import Colour
class bcperry2_evaluator:
    @staticmethod
    def assess_board_additional(myboard, colour):
        board_stats = {}
        #clustering: increase value if pieces are close together
        board_stats["clustering"] = 0
        def distance_to(piece, other_piece):
            return abs(piece.location - other_piece.location)
        pieces = myboard.get_pieces(colour)
        for i, piece in enumerate(pieces[:-1]):
            for other_piece in pieces[i+1:]:
                num = distance_to(piece, other_piece)
                #if num > 3:
                #    continue
                if num == 0:
                    board_stats['clustering'] += 1
                    continue
                board_stats["clustering"] += 1/(num)**2
        board_stats["rquallstering"] = 0
        locations = [0 for _ in range(25)]
        for piece in pieces:
            if piece.location == 0:
                continue
            locations[piece.location-1] += 1
        for i in range(24):
            rating = 0
            if locations[i] == 0:
                continue
            if locations[i] == 1:
                rating = -1
                rating *= [24-i,i][colour==Colour.BLACK]
                rating /= 12
                board_stats['rquallstering'] += rating
                continue
            if locations[i] == 2:
                rating = 5
            if locations[i] == 3:
                rating = 4
            if locations[i] == 4:
                rating = 2
            if locations[i]>4:
                rating = 1
            if i>0 and locations[i-1] > 1:
                rating *= 1.3
            if i<23 and locations[i+1] > 1:
                rating *= 1.3
            board_stats['rquallstering'] += rating
        return board_stats

class player1_bcperry2(CompareAllMoves):

    def __init__(self):
        self.weights = "-1.59%0.05%0.37%-1.75%-0.14%0.80%0.51%0.02"
        self.consts = self.weights.split("%")
        self.consts = [float(i) for i in self.consts]

            # 'number_occupied_spaces': number_occupied_spaces,
            # 'opponents_taken_pieces': opponents_taken_pieces,
            # 'sum_distances': sum_distances,
            # 'sum_distances_opponent': sum_distances_opponent,
            # 'number_of_singles': number_of_singles,
            # 'sum_single_distance_away_from_home': sum_single_distance_away_from_home,
            # 'pieces_on_board': pieces_on_board,
            # 'sum_distances_to_endzone': sum_distances_to_endzone,

    @staticmethod
    def get_difficulty():
        return "Normal"

    def evaluate_board(self, myboard, colour):
        board_stats = self.assess_board(colour, myboard)
        keys = list(board_stats.keys())
        board_value = 0
        stry = ""
        for i in range(len(self.consts)):
            key = keys[i]
            board_value += board_stats[key] * self.consts[i]
            stry+=key+str(self.consts[i])+"*"+str(board_stats[key])
            if i!=len(self.consts)-1:
                stry+="+"
        #print(stry)
        return board_value

class player2_bcperry2(CompareAllMoves):

    def __init__(self):
        self.weights = "-1.58%0.07%0.41%-1.77%-0.12%0.86%0.47%0.18%0.00%0.00"
        self.consts = self.weights.split("%")
        self.consts = [float(i) for i in self.consts]
        
            # 'NOVEL_FEATURE': novel_feature_value,
            # 'number_occupied_spaces': number_occupied_spaces,
            # 'opponents_taken_pieces': opponents_taken_pieces,
            # 'sum_distances': sum_distances,
            # 'sum_distances_opponent': sum_distances_opponent,
            # 'number_of_singles': number_of_singles,
            # 'sum_single_distance_away_from_home': sum_single_distance_away_from_home,
            # 'pieces_on_board': pieces_on_board,
            # 'sum_distances_to_endzone': sum_distances_to_endzone,

    @staticmethod
    def get_difficulty():
        return "Normal"

    def evaluate_board(self, myboard, colour):
        board_stats = self.assess_board(colour, myboard)
        board_stats.update(bcperry2_evaluator.assess_board_additional(myboard, colour))
        keys = list(board_stats.keys())
        board_value = 0
        for i in range(len(self.consts)):
            key = keys[i]
            board_value += board_stats[key] * self.consts[i]

        return board_value


globalFeatures = [
    'number_occupied_spaces',
    'opponents_taken_pieces',
    'sum_distances',
    'sum_distances_opponent',
    'number_of_singles',
    'sum_single_distance_away_from_home',
    'pieces_on_board',
    'sum_distances_to_endzone',
    'clustering',
    'rquallstering',
]
class AIBuilder_bcperry2(bcperry2_evaluator):
    def __init__(self, name="", constants=None):
        super().__init__()
        global globalFeatures
        self.constants = constants
        if name != "":
            constArr = name.split("%")
            self.constants = {}
            for i in range(len(constArr)):
                if i >= len(globalFeatures):
                    break
                self.constants[globalFeatures[i]] = float(constArr[i])
        elif constants == None:
            constants = {
                #'number_occupied_spaces': -1,
                'opponents_taken_pieces': -1,
                #'sum_distances': 1,
                'sum_distances_opponent': -1,
                #'number_of_singles': 1,
                #'sum_single_distance_away_from_home': 1,
                #'pieces_on_board': 1,
                'sum_distances_to_endzone': 1,
                #'clustering': 0,
                'rquallstering': -1,
            }
            self.constants = constants

    def getConstants(self):
        return self.constants

    def constStrings(self):
        return [f"{v:.2f}" for k, v in self.constants.items()]
    
    @property
    def __name__(self):
        return "%".join(self.constStrings())

    def evaluate_board(self, myboard, colour):
        board_stats = self.assess_board(colour, myboard)
        board_stats.update(self.assess_board_additional(myboard, colour))
        board_value = 0
        for k, v in self.constants.items():
            board_value += v * board_stats[k]
        return board_value

    def get_id(self):
        return self.__name__