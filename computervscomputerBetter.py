from random import randint

from src.colour import Colour
from src.game import Game
from src.strategy_factory import StrategyFactory
from src.strategies import HumanStrategy
from src.experiment import Experiment
from src.bcperry2 import AIBuilder_bcperry2
if __name__ == '__main__':
    override = False

    print("Available Strategies:")
    strategies = [x for x in StrategyFactory.get_all() if x.__name__ != HumanStrategy.__name__]
    for i, strategy in enumerate(strategies):
        print("[%d] %s (%s)" % (i, strategy.__name__, strategy.get_difficulty()))

    if override:
        strategy_index1 = 10
    else:
        pass#strategy_index1 = int(input('Pick strategy 1:\n'))

    chosen_strategy1 = AIBuilder_bcperry2("0.48%0.30%0.50%-0.53%-1.59%0.39%0.28%-0.12%0.04%-0.15")

    if override:
        strategy_index2 = 8
    else:
        strategy_index2 = int(input('Pick strategy 2:\n'))

    chosen_strategy2 = StrategyFactory.create_by_name(strategies[strategy_index2].__name__)

    experiment = Experiment(
        100,
        white_strategy=chosen_strategy1,
        black_strategy=chosen_strategy2,
    )

    experiment.run()

    print("White Strategy: "+str(chosen_strategy1))
    print("Black Strategy: "+str(chosen_strategy2))

    experiment.print_results()
