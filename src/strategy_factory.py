from src.compare_all_moves_strategy import CompareAllMovesSimple, \
    CompareAllMovesWeightingDistanceAndSingles, \
        CompareAllMovesWeightingDistanceAndSinglesWithEndGame, \
            CompareAllMovesWeightingDistance
from src.strategies import MoveFurthestBackStrategy, HumanStrategy, MoveRandomPiece
from src.anderson import player1_anderson,player2_anderson
from src.bcperry2 import player1_bcperry2, player2_bcperry2, AIBuilder_bcperry2



class StrategyFactory:
    @staticmethod
    def create_by_name(strategy_name):
        for strategy in StrategyFactory.get_all():
            if strategy.__name__ == strategy_name:
                return strategy()

        raise Exception("Cannot find strategy %s" % strategy_name)

    @staticmethod
    def get_all():
        strategies = [
            MoveRandomPiece,
            MoveFurthestBackStrategy,
            CompareAllMovesSimple,
            player1_anderson,
            player2_anderson,
            CompareAllMovesWeightingDistanceAndSinglesWithEndGame,
            CompareAllMovesWeightingDistanceAndSingles,
            CompareAllMovesWeightingDistance,
            HumanStrategy,
            player1_bcperry2,
            player2_bcperry2,
            AIBuilder_bcperry2,
        ]
        return strategies
