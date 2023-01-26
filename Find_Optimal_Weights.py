import time
times = []
def split():
    global times
    times.append(time.time())
split()
from random import randint

from src.colour import Colour
from src.game import Game
from src.strategy_factory import StrategyFactory
from src.strategies import HumanStrategy
from src.experiment import Experiment
from src.strategies import Strategy
from src.bcperry2 import AIBuilder_bcperry2
import trueskill
import json
ratings = {}
gameResults = [] # list of tuples (white, black, result)
def loadRatings():
    try:
        ratings = json.load(open("ratings.json"))
        for i, rating in ratings.items():
            ratings[i] = trueskill.Rating(rating[0], rating[1])
    except:
        pass
loadRatings()
def getRating(name):
    if name in ratings:
        return ratings[name]
    else:
        return trueskill.Rating()
def result(name1, name2, save=True):
    global ratings
    rating1 = getRating(name1)
    rating2 = getRating(name2)
    ratings[name1], ratings[name2] = trueskill.rate_1vs1(rating1, rating2)
    if save:
        saveRatings()
def saveRatings():
    global ratings
    temp = {}
    for i, rating in ratings.items():
        temp[i] = [rating.mu, rating.sigma]
    json.dump(temp, open("ratings.json", "w"))
def getLeaderboard():
    global ratings
    return sorted(ratings, key=ratings.get, reverse=True)
def printLeaderboard():
    global ratings
    print("Leaderboard:")
    for i, name in enumerate(getLeaderboard()):
        print("%d. %s: %s" % (i+1, name, ratings[name]))
def doScores(white:str, black:str, res:list[tuple]):
    for i in range(len(res)):
        if res[i][1] == Colour.BLACK:
            result(black, white)
        else:
            result(white, black)
        gameResults.append((white, black, res[i][1]==Colour.WHITE))
split()
def privateAttr(obj, attr):
    classPrefix = obj.__class__.__name__
    return getattr(obj, '_'+classPrefix+'__'+attr)
def handleMatch(white:Strategy, black:Strategy, games:int):
    chosen_strategy1 = white
    chosen_strategy2 = black
    experiment = Experiment(
        games,
        white_strategy=chosen_strategy1,
        black_strategy=chosen_strategy2,
    )
    experiment.run()
    doScores(chosen_strategy1.__name__, chosen_strategy2.__name__, privateAttr(experiment, "results"))
    return
def roundRobin(ainames:list[str], games:int):
    amt = 0
    for i in range(len(ainames)):
        ainames[i] = StrategyFactory.create_by_name(ainames[i])
    for i in range(len(ainames)):
        for j in range(i+1, len(ainames)):
            handleMatch(ainames[i], ainames[j], games)
            amt += 1
        print("Played %d matches" % amt)
    return
def roundRobinBuilders(builders:list[AIBuilder_bcperry2], games:int):
    amt = 0
    for i in range(len(builders)):
        for j in range(i+1, len(builders)):
            handleMatch(builders[i], builders[j], games)
            amt += 1
        print("Played %d matches" % amt)
    return
if __name__ == '__main__':
    allStrategyNames = [x.__name__ for x in StrategyFactory.get_all() if x.__name__ != HumanStrategy.__name__]
    valid_board_info = ["number_occupied_spaces", 
    "opponents_taken_pieces", "sum_distances",
    "sum_distances_opponent", "number_of_singles",
    "sum_single_distance_away_from_home", "pieces_on_board",
    "sum_distances_to_endzone"
    ]
    def getAIBuilderConfigs(valid_board_info):
        def recurs_options(list, options):
            temp = []
            for i in range(len(list)):
                for j in range(len(options)):
                    temp.append(list[i]+[options[j]])
            return temp
        configs = []
        #config is a dict with keys from valid_board_info
        numVals = len(valid_board_info)
        options = [-1, 0, 1]
        tempConfigs = []
        for i in range(3):
            tempConfigs.append([options[i]])
        for i in range(numVals-1):
            tempConfigs = recurs_options(tempConfigs, options)
        for i in range(len(tempConfigs)):
            configs.append({})
            for j in range(len(tempConfigs[i])):
                configs[i][valid_board_info[j]] = tempConfigs[i][j]
        return configs
    def getAIBuilders(configs:list[dict]):
        builders = []
        for i in range(len(configs)):
            builders.append(AIBuilder_bcperry2(configs[i]))
        return builders
        
    configs = getAIBuilderConfigs(valid_board_info)
    builders = getAIBuilders(configs)
    roundRobinBuilders(builders, 1)
    
    #roundRobin(allStrategyNames, 2)
    printLeaderboard()


elif __name__ == '__main__' and False:
    split()
    override = True

    print("Available Strategies:")
    strategies = [x for x in StrategyFactory.get_all() if x.__name__ != HumanStrategy.__name__]
    for i, strategy in enumerate(strategies):
        print("[%d] %s (%s)" % (i, strategy.__name__, strategy.get_difficulty()))

    if override:
        strategy_index1 = 10
    else:
        strategy_index1 = int(input('Pick strategy 1:\n'))

    chosen_strategy1 = StrategyFactory.create_by_name(strategies[strategy_index1].__name__)

    if override:
        strategy_index2 = 8
    else:
        strategy_index2 = int(input('Pick strategy 2:\n'))

    chosen_strategy2 = StrategyFactory.create_by_name(strategies[strategy_index2].__name__)

    experiment = Experiment(
        20,
        white_strategy=chosen_strategy1,
        black_strategy=chosen_strategy2,
    )
    split()
    experiment.run()
    split()
    print("White Strategy: "+str(chosen_strategy1)+", wins: "+str(experiment.get_white_wins()))
    print("Black Strategy: "+str(chosen_strategy2)+", wins: "+str(privateAttr(experiment, "games_to_play") - experiment.get_white_wins()))

    experiment.print_results()
    doScores(str(chosen_strategy1), str(chosen_strategy2), privateAttr(experiment, "results"))
    split()
    for i in range(1, len(times)):
        print(format(times[i] - times[0],".2f") + " - " + format(times[i] - times[i-1],".2f"))