# Play backgammon
from src.compare_all_moves_strategy import *
from src.strategies import *
from src.experiment import Experiment
from src.bcperry2 import player1_bcperry2, player2_bcperry2

experiment = Experiment(
    games_to_play=300,
    white_strategy=player2_bcperry2(),
    black_strategy=CompareAllMovesWeightingDistance()
)
experiment2 = Experiment(
    games_to_play=300,
    white_strategy=player2_bcperry2(),
    black_strategy=MoveFurthestBackStrategy()
)
if __name__ == '__main__':
    experiment.run()
    experiment.print_results()
    experiment2.run()
    experiment2.print_results()


# Null hypothesis is that the strategies equally good
# Define a joint event of a random coin toss to determine who starts followed by a game,
# Under the null hypothesis, for a single event, p(win) = 0.5
# Assuming the strategies are equal (null hypothesis): P(n_wins) = binom(n_wins, n_games, 0.5)
