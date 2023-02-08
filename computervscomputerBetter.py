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
    curBest = "-1.59%0.05%0.37%-1.75%-0.14%0.80%0.51%0.02"
    chosen_strategy1 = AIBuilder_bcperry2(curBest)
    rqualVal = [-6.4,-11.5,6.3,0.2,2.1,0.3,7.2,2.7]
    chosen_strategy2 = AIBuilder_bcperry2("%".join([f"{x:.2f}" for x in rqualVal]))

    if override:
        strategy_index2 = 8
    else:
        pass#strategy_index2 = int(input('Pick strategy 2:\n'))

    #chosen_strategy2 = StrategyFactory.create_by_name(strategies[strategy_index2].__name__)

    experiment = Experiment(
        300,
        white_strategy=chosen_strategy1,
        black_strategy=chosen_strategy2,
    )

    experiment.run()

    print("White Strategy: "+str(chosen_strategy1))
    print("Black Strategy: "+str(chosen_strategy2))

    experiment.print_results()
