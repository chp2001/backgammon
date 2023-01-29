import time
import datetime
import random
from src.colour import Colour
from src.game import Game
from src.strategy_factory import StrategyFactory
from src.strategies import HumanStrategy
from src.experiment import Experiment
from src.strategies import Strategy
from src.bcperry2 import *
from scipy.stats import binom
import multiprocessing as mp
import signal
import trueskill
import json
from Find_Optimal_Weights import loadRatings, saveRatings, getRating, \
result, getLeaderboard, printLeaderboard, doScores, privateAttr
import math
globalResults = []
obituary = []
def loadObituary():
    global obituary
    try:
        with open("obituary.json", "r") as f:
            obituary = json.load(f)
    except:
        pass
def saveObituary():
    global obituary
    with open("obituary.json", "w") as f:
        json.dump(obituary, f, indent=4)
def firstIndex(iterable, condition=bool):
    for i, item in enumerate(iterable):
        if condition(item):
            return i
    return None
def first(iterable, condition=bool):
    for i, item in enumerate(iterable):
        if condition(item):
            return item
    return None
def get_id(strategy):
    strats:list = StrategyFactory.get_all()
    if type(strategy) == str:
        return firstIndex(strats, lambda x: x.__name__ == strategy)
    elif type(strategy)==AIBuilder_bcperry2:
        return strategy.get_id()
    return firstIndex(strats, lambda x: x.__name__ == strategy.__name__)
class Result:
    def __init__(self, white, black, res:bool, _time:float=None):
        if type(white) != str:
            white = white.__name__
        if type(black) != str:
            black = black.__name__
        self.white = white
        self.black = black
        self.res = res
        self.winner = black if res else white
        self.loser = white if res else black
        self.time = _time if _time is not None else time.time()
    def __str__(self):#we want to be able to use this to load from a string
        return "%s,%s,%s,%s" % (self.white, self.black, self.res, self.time)
    def __repr__(self):
        return str(self)
    def __eq__(self, other):
        if type(other) != Result:
            return False
        return self.white == other.white and self.black == other.black and \
            self.res == other.res and self.time == other.time
    @staticmethod
    def fromStr(string:str):
        white, black, res, time = string.split(",")
        return Result(white, black, bool(res), float(time))
def loadResult(res:str):
    white, black, result, time = res.split(",")
    return Result(white, black, bool(result), float(time))
def loadResults(filename:str):
    try:
        return [loadResult(i) for i in open(filename).read().split("\n") if i]
    except:
        return []
def enforceNameFormat(name:str):
    if not '%' in name:
        return name
    else:
        constants = name.split('%')
        for i in range(len(constants)):
            constants[i] = float(constants[i])
            constants[i] = f"{constants[i]:.2f}"
        return "%".join(constants)
def saveResults(results:list[Result], filename:str):
    temp = []
    for i in results:
        datum = Result(enforceNameFormat(i.white), enforceNameFormat(i.black), i.res, i.time)
        temp.append(datum)
    with open(filename, "w") as f:
        f.write("\n".join([str(i) for i in temp]))
def addResult(result:Result):
    global globalResults
    if not result in globalResults:
        globalResults.append(result)
def addResults(results:list[Result]):
    global globalResults
    for i in results:
        addResult(i)
def getResults():
    global globalResults
    return globalResults
def saveGlobalResults():
    saveResults(globalResults, "results.txt")
def loadGlobalResults():
    global globalResults
    globalResults = loadResults("results.txt")
def getBuilderGames():
    global globalResults
    return [i for i in globalResults if '%' in i.white or '%' in i.black]
def saveBuilderGames():
    saveResults(getBuilderGames(), "builderGames.txt")
def loadBuilderGames():
    global globalResults
    globalResults = loadResults("builderGames.txt")
builderRatings = {}
def getBuilderRating(builder):
    global builderRatings
    if not builder in builderRatings:
        builderRatings[builder] = trueskill.Rating()
    return builderRatings[builder]
def getBuilderRatings():
    global builderRatings
    return builderRatings
def saveBuilderRatings():
    global builderRatings
    temp = []
    for i in builderRatings:
        if not '%' in i:
            continue
        temp.append([i, builderRatings[i].mu, builderRatings[i].sigma])
    temp.sort(key=lambda x: x[1], reverse=True)
    with open("builderRatings.json", "w") as f:
        json.dump(temp, f, indent=4)
def loadBuilderRatings():
    global builderRatings
    with open("builderRatings.json", "r") as f:
        builderRatings = json.load(f)
def configStartRating(percentile:float):
    new = trueskill.Rating()
    mu = new.mu
    sigma = new.sigma
    #assuming percentile is between 0 and 1, average is at 0.5
    mu = mu + (percentile - 0.5) * sigma
    return trueskill.Rating(mu, sigma)
    '''strategies = [
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
        ]'''
AIStartRatings = {
    "MoveRandomPiece": configStartRating(0.1),
    "MoveFurthestBackStrategy": configStartRating(0.6),
    "CompareAllMovesSimple": configStartRating(0.3),
    "player1_anderson": configStartRating(0.5),
    "player2_anderson": configStartRating(0.5),
    "CompareAllMovesWeightingDistanceAndSinglesWithEndGame": configStartRating(0.7),
    "CompareAllMovesWeightingDistanceAndSingles": configStartRating(0.6),
    "CompareAllMovesWeightingDistance": configStartRating(0.5),
    "player1_bcperry2": configStartRating(0.6),
    "player2_bcperry2": configStartRating(0.5),
}
def ratingCopy(rating):
    return trueskill.Rating(rating.mu, rating.sigma)
def getAIRating(strategy):
    if type(strategy) == str:
        if strategy in AIStartRatings:
            return ratingCopy(AIStartRatings[strategy])
        else:
            return trueskill.Rating()
    else:
        return getAIRating(strategy.__name__)
def builderResult(i:Result):
    global builderRatings
    if not i.white in builderRatings and '%' in i.white:
        builderRatings[i.white] = trueskill.Rating()
    elif not '%' in i.white:
        builderRatings[i.white] = getAIRating(i.white)
    if not i.black in builderRatings and '%' in i.black:
        builderRatings[i.black] = trueskill.Rating()
    elif not '%' in i.black:
        builderRatings[i.black] = getAIRating(i.black)
    if not i.res:
        builderRatings[i.white], builderRatings[i.black] = \
            trueskill.rate_1vs1(builderRatings[i.white], builderRatings[i.black])
    else:
        builderRatings[i.black], builderRatings[i.white] = \
            trueskill.rate_1vs1(builderRatings[i.black], builderRatings[i.white])
def recalculateBuilderRatings():
    global builderRatings
    builderRatings = {}
    for i in getBuilderGames():
        builderResult(i)
def createBaseBuilder():
    return AIBuilder_bcperry2()
def createBuilder(nameStr:str):
    return AIBuilder_bcperry2(name=nameStr)
def getBuilderNames():
    return [i for i in builderRatings if '%' in i]
class BuilderGameStats:
    def __init__(self, name:str):
        self.name = name
        self.rating = None
        self.wins = 0
        self.losses = 0
        self.played = 0
        self.playedAgainst = {}
        self.winsAgainst = {}
        self.lossesAgainst = {}
        self.scoreAgainst = {}
        self.oldestGame = None
    def calcScore(self, against:str):
        self.scoreAgainst[against] = self.winsAgainst.get(against, 0) / self.playedAgainst.get(against, 1)
    def registerWin(self, against:str):
        self.wins += 1
        self.played += 1
        self.playedAgainst[against] = self.playedAgainst.get(against, 0) + 1
        self.winsAgainst[against] = self.winsAgainst.get(against, 0) + 1
        self.calcScore(against)
    def registerLoss(self, against:str):
        self.losses += 1
        self.played += 1
        self.playedAgainst[against] = self.playedAgainst.get(against, 0) + 1
        self.lossesAgainst[against] = self.lossesAgainst.get(against, 0) + 1
        self.calcScore(against)
    def registerGame(self, result:Result):
        if result.black == self.name:
            if result.res:
                self.registerWin(result.white)
            else:
                self.registerLoss(result.white)
        else:
            if result.res:
                self.registerLoss(result.black)
            else:
                self.registerWin(result.black)
        if self.oldestGame is None or self.oldestGame.time > result.time:
            self.oldestGame = result
    def __str__(self):
        return f"{self.name}: {self.rating} ({self.wins} / {self.losses})"
newObituaries = 0
def push_obituary(builder:BuilderGameStats):
    temp = {
        "name": builder.name,
        "mu": builder.rating.mu,
        "sigma": builder.rating.sigma,
        "wins": builder.wins,
        "losses": builder.losses,
        "played": builder.played,
        "oldestGame": builder.oldestGame.time,
        "deathTime": time.time(),
    }
    global obituary
    obituary.append(temp)
    global newObituaries
    newObituaries += 1
    if newObituaries > 10:
        saveObituary()
        newObituaries = 0
loadObituary()
        
builderGameStats = {}
def getAllBuilderGameStats():
    global builderGameStats
    builderGameStats = {}
    for i in getBuilderGames():
        if not i.white in builderGameStats and '%' in i.white:
            builderGameStats[i.white] = BuilderGameStats(i.white)
        if not i.black in builderGameStats and '%' in i.black:
            builderGameStats[i.black] = BuilderGameStats(i.black)

        if '%' in i.white:
            builderGameStats[i.white].registerGame(i)
        if '%' in i.black:
            builderGameStats[i.black].registerGame(i)
    for i in builderGameStats:
        builderGameStats[i].rating = builderRatings[i]
    return builderGameStats
def getBuilderGameStats(name:str):
    if not name in builderGameStats:
        builderGameStats[name] = BuilderGameStats(name)
    return builderGameStats[name]
        
from src.bcperry2 import globalFeatures
from src.experiment import GamePlayer
def createRandomBuilder(scale:float = 1) -> str:
    features = []
    for i in globalFeatures:
        if random.random() > 0.5:
            features.append(random.gauss(0, scale))
        else:
            features.append(0)
        #features.append(random.gauss(0, scale))
    string = "%".join([f"{i:.2f}" for i in features])
    return string
def getConstantsFromBuilder(name:str):
    return [float(i) for i in name.split("%")]
def loadAll():
    loadBuilderGames()
    recalculateBuilderRatings()
    getAllBuilderGameStats()
def saveAll():
    saveBuilderGames()
    recalculateBuilderRatings()
    saveBuilderRatings()

class ExperimentalOptimizer:
    def __init__(self, games_to_play:int = 3):
        self.__parallelise = True
        loadAll()
        self.games_to_play = games_to_play
        self.names = getBuilderNames()
        self.minBuilders = 5
        if len(self.names) < self.minBuilders:
            self.names.extend([createRandomBuilder() for i in range(self.minBuilders - len(self.names))])
        self.builders = [createBuilder(i) for i in self.names]
        self.builderStats = [getBuilderGameStats(i) for i in self.names]
    
    def leastTested(self) -> list:
        return sorted(self.builderStats, key=lambda x: x.played)
    
    def bestBuilders(self) -> list:
        return sorted(self.builderStats, key=lambda x: x.rating.mu, reverse=True)

    def leastPlayedAgainst(self, builder:BuilderGameStats) -> list[str]:
        playTargets = [i for i in AIStartRatings.keys()]
        random.shuffle(playTargets)
        playTargets = sorted(playTargets, key=lambda x: builder.playedAgainst.get(x, 0))
        if builder.playedAgainst.get(playTargets[0], 0) == 0:
            #return all targets that have not been played against
            return [i for i in playTargets if builder.playedAgainst.get(i, 0) == 0]
        return [playTargets[0]]

    def matchMaker(self) -> list:
        least = self.leastTested()
        amtAIs = len(AIStartRatings.items())
        matchMaked = []
        queued = {}
        allqueued = 0
        cycle = 0
        while allqueued < mp.cpu_count() and cycle < 5:
            cycle += 1
            for i in range(len(least)):
                target:BuilderGameStats = least[i]
                leastPlayed = self.leastPlayedAgainst(target)
                for j in leastPlayed:
                    if target.playedAgainst.get(j, 0) >= self.games_to_play:
                        continue
                    if queued.get(target.name, 0) >= cycle:
                        continue
                    matchMaked.append((target.name, j))
                    queued[target.name] = queued.get(target.name, 0) + 1
                    allqueued += 1
                    if len(matchMaked) >= mp.cpu_count():
                        return matchMaked
        return matchMaked

    def matchMakerWrapper(self) -> list:
        return list(self.matchMaker())

    def getMyBuilder(self, name:str) -> Strategy:
        for i in range(len(self.names)):
            if self.names[i] == name:
                return self.builders[i]
        if name in AIStartRatings.keys():
            return StrategyFactory.get_all()[get_id(name)]()
        return None

    def playGames(self):
        gamePlayers = []
        matchmakergames = self.matchMaker()
        #print(f"Matchmaking games: {matchmakergames}")
        for i in matchmakergames:
            #print(i)
            desiredAmt = self.games_to_play - self.builderStats[self.names.index(i[0])].playedAgainst.get(i[1], 0)
            if desiredAmt > 0:
                #print("Playing", desiredAmt, "games between", i[0], "and", i[1])
                gamePlayers.extend([\
                    GamePlayer(self.getMyBuilder(i[0]), self.getMyBuilder(i[1]))
                        for j in range(self.games_to_play)])
            #(GamePlayer(i[0], i[1]))
        for i in range(len(gamePlayers)):
            gamePlayers[i].gameNumber = i
        start_time = time.time()
        index_range = range(len(gamePlayers))
        if self.__parallelise:
            try:
                global force_exit
                pool = mp.Pool(mp.cpu_count(),initializer=init_worker)
                results = pool.map_async(self.playGame, gamePlayers)
                results = results.get(30)
                pool.close()
                pool.join()
            except KeyboardInterrupt as e:
                print("Caught KeyboardInterrupt, terminating workers")
                pool.terminate()
                pool.join()
                raise e
            except mp.TimeoutError as e:
                print("Caught TimeoutError, terminating workers")
                pool.terminate()
                pool.join()
                temp = []
                for i in results:
                    if i != None:
                        temp.append(i)
                results = temp
                #raise e
        else:
            results = [self.playGame(i) for i in gamePlayers]
        for i in results:
            if i != None and i.res != None:
                globalResults.append(i)
                if i.white not in self.names:
                    print("White not found", i.white)
                else:
                    self.builderStats[self.names.index(i.white)].registerGame(i)
                #self.builderStats[].registerGame(i)
        self.saveAll2()
        print(f"\nGames played: {len(results)}")
        print(f"Total games played: {sum([i.played for i in self.builderStats])}")
        print(f"Total AIs: {len(self.builderStats)}")
        print(f"Total valid AIs: {len(self.getValidBuildersForStats())}")
        print(f"Time taken: {time.time() - start_time}")

    def playGame(self, gamePlayer:GamePlayer):
        name1 = privateAttr(gamePlayer, "white_strategy")
        if isinstance(name1, AIBuilder_bcperry2):
            name1 = name1.__name__
        else:
            name1 = name1.__class__.__name__
        name2 = privateAttr(gamePlayer, "black_strategy")
        if isinstance(name2, AIBuilder_bcperry2):
            name2 = name2.__name__
        else:
            name2 = name2.__class__.__name__
        #print(f"S G{gamePlayer.gameNumber}")
        #print("Starting game", gamePlayer.gameNumber, "between", name1, "and", name2, "")
        result = gamePlayer(gamePlayer.gameNumber, 10)
        if result[1]==None:
            print(f"G{gamePlayer.gameNumber} TIMEOUT")
            return Result(name1, name2, None)
        else:
            #pass
            string = f"G{gamePlayer.gameNumber} "
            if result[1]==Colour.WHITE:
                string += name1 + " WINS"
            else:
                string += "LOSS"
            #print(string)
            pass
            #print("Game", gamePlayer.gameNumber, "finished between", name1, "and", name2, "with result", "White" if result[1]==Colour.WHITE else "Black" if result[1]==Colour.BLACK else "Timeout")

        return Result(name1, name2, result[1]==Colour.BLACK)

    def gamecount_goal(self, per_ai:int=0):
        goalcount = len(self.names) * len(AIStartRatings.keys()) * per_ai
        return goalcount
    
    def gamecount_missing(self):
        #goal = self.gamecount_goal(self.games_to_play)
        #goalPerBuilder = goal / len(self.names)
        missing = 0
        for i in self.builderStats:
            for j in AIStartRatings.keys():
                missing += max(0, self.games_to_play - i.playedAgainst.get(j, 0))
        return missing

    def getMinPlayedGames(self):
        return min([i.played for i in self.builderStats])

    def avg_playedgames(self):
        played = 0
        amt = 0
        for i in self.builderStats:
            played += i.played
            amt += 1
        if amt == 0:
            return 0
        return played / amt
    
    def push_additional_builders(self, num:int=1, scale:float=1.0):
        newNames = []
        newBuilders = []
        for i in range(num):
            newNames.append(createRandomBuilder(scale))
            newBuilders.append(createBuilder(newNames[-1]))
        self.names.extend(newNames)
        self.builders.extend(newBuilders)
        newbuilderstats = [BuilderGameStats(i) for i in newNames]
        for i in newbuilderstats:
            i.rating = trueskill.Rating()
        self.builderStats.extend(newbuilderstats)
        self.saveAll2()

    def purgeBuilder(self, builder:BuilderGameStats):
        push_obituary(builder)
        self.builderStats.remove(builder)
        self.names = [i.name for i in self.builderStats]
        self.builders = [createBuilder(i.name) for i in self.builderStats]
        global globalResults
        tempGlobalResults = []
        for i in globalResults:
            if i.white != builder.name and i.black != builder.name:
                tempGlobalResults.append(i)
        globalResults = tempGlobalResults
        #need to save

    def purgeLowestPerformers(self, num:int=1):
        global globalResults
        self.builderStats.sort(key=lambda x: x.rating.mu)
        removal = []
        for i in range(num):
            removal.append(self.builderStats[i])
        for i in removal:
            self.purgeBuilder(i)
        self.saveAll2()

    def getValidBuildersForStats(self):
        valid = []
        for i in self.builderStats:
            if i.played == 0:
                continue
            if not '%' in i.name:
                continue
            valid.append(i)
        return valid

    def rating_statistics(self):
        total = 0
        res = {}
        builderStats = self.getValidBuildersForStats()
        for i in builderStats:
            total += i.rating.mu
        res["avg"] = total / len(builderStats)
        res["min"] = min([i.rating.mu for i in builderStats])
        res["max"] = max([i.rating.mu for i in builderStats])
        return res
    def amt_threshold(self, threshold:float=0.5):
        stats = self.rating_statistics()
        amt = 0
        threshold_val = ( stats["max"] - stats["min"] ) * threshold + stats["min"]
        for i in self.builderStats:
            if i.rating.mu < threshold_val:
                amt += 1
        return amt

    def getWeightedBestConstants(self)->list:
        constants = [0 for x in globalFeatures]
        relative_total = 0
        builderStats = self.getValidBuildersForStats()
        for i in builderStats:
            relative_total += i.rating.mu
        for i in builderStats:
            builderConst = getConstantsFromBuilder(i.name)
            for j in range(len(globalFeatures)):
                constants[j] += builderConst[j] * (i.rating.mu / relative_total)
        return constants
    #define some types of mutations
    def getIndexesCaredAbout(self, constants:list)->list[int]:
        indices = []
        for i in range(len(constants)):
            if abs(constants[i]) > 0.1:
                indices.append(i)
        return indices
    def reverseSource(self, constants:list, chance:float = 0.5)->None:
        indices = self.getIndexesCaredAbout(constants)
        for i in indices:
            if random.random() > chance:
                constants[i] = -constants[i]
    def addSource(self, constants:list, chance:float = 0.5, scale:float = 1)->None:
        indices = self.getIndexesCaredAbout(constants)
        nonSource = [i for i in range(len(constants)) if i not in indices]
        if len(nonSource) == 0:
            nonSource = indices
        for i in nonSource:
            if random.random() > chance:
                constants[i] += random.gauss(0, 0.5 * scale)
    def removeSource(self, constants:list, chance:float = 0.5)->None:
        indices = self.getIndexesCaredAbout(constants)
        for i in indices:
            if random.random() > chance:
                constants[i] = 0
    def mutateSource(self, constants:list, chance:float = 0.5, scale:float = 1)->None:
        indices = self.getIndexesCaredAbout(constants)
        for i in indices:
            if random.random() > chance:
                if random.random() > 0.5:
                    constants[i] *= 1 + random.random() * 0.5 * scale
                else:
                    constants[i] *= 1 - random.random() * 0.5 * scale
    def randomNoise(self, constants:list, scale:float = 1)->None:
        for i in range(len(constants)):
            constants[i] += random.gauss(0, 0.1*scale)
    def mutateBuilder(self, constants:list, count:int=1, chanceBase:float=0.5, scale:float=1)->list[int]:
        newConstants = [i for i in constants]
        if scale==0:
            return newConstants
        numPossibleMutations = 7
        chances = {
            'reverse': 0.3 * scale,
            'add': 0.3 * scale,
            'remove': 0.3 * scale,
            'mutate': 0.4 * scale,
            'noise': 0.5 / scale,
            'all': 0.1 * scale,
            'extra': 0.1,
        }
        total = 0
        for i in chances:
            total += chances[i]
        for i in chances:
            chances[i] /= total
        def chanceUntil(key:str)->float:
            total = 0
            for i in chances:
                total += chances[i]
                if i == key:
                    return total
        times = 0
        while times < count:
            roll = random.random()
            if roll < chanceUntil('reverse'):
                self.reverseSource(newConstants, chanceBase)
            elif roll < chanceUntil('add'):
                self.addSource(newConstants, chanceBase, scale)
            elif roll < chanceUntil('remove'):
                self.removeSource(newConstants, chanceBase)
            elif roll < chanceUntil('mutate'):
                self.mutateSource(newConstants, chanceBase, scale)
            elif roll < chanceUntil('noise'):
                self.randomNoise(newConstants, scale)
            elif roll < chanceUntil('all'):
                self.reverseSource(newConstants, chanceBase)
                self.addSource(newConstants, chanceBase, scale)
                self.removeSource(newConstants, chanceBase)
                self.mutateSource(newConstants, chanceBase, scale)
                self.randomNoise(newConstants, scale)
            elif roll < chanceUntil('extra'):
                times -= 1
            times += 1
        return newConstants
    def createMutatedBuilder(self, constants:list, scale:float = 1)->str:
        newConstants = self.mutateBuilder(constants, 1, 0.3, scale)
        string = "%".join([f"{i:.2f}" for i in newConstants])
        return string

    def mutateBestBuilders(self, num:int=1, scale:float=1):
        constants = self.getWeightedBestConstants()
        for i in range(num):
            newBuilder = self.createMutatedBuilder(constants, scale)
            self.names.append(newBuilder)
            self.builders.append(createBuilder(newBuilder))
            self.builderStats.append(BuilderGameStats(newBuilder))
        self.saveAll2()

    def mutateBestBuilder(self, num:int=1, scale:float=1):
        builderStats = self.getValidBuildersForStats()
        builderStats.sort(key=lambda x: x.rating.mu * x.played, reverse=True)
        chosen = builderStats[0]
        constants = getConstantsFromBuilder(chosen.name)
        for i in range(num):
            newBuilder = self.createMutatedBuilder(constants, scale)
            self.names.append(newBuilder)
            self.builders.append(createBuilder(newBuilder))
            self.builderStats.append(BuilderGameStats(newBuilder))
        self.saveAll2()

    def copyBestBuilder(self, num:int=1):
        builderStats = self.getValidBuildersForStats()
        builderStats.sort(key=lambda x: x.rating.mu * x.played, reverse=True)
        chosen = builderStats[0]
        constants = getConstantsFromBuilder(chosen.name)
        for i in range(num):
            strs = [f"{i:.2f}" for i in constants]
            for j in range(len(strs)):
                strs[j] = strs[j][:-1]+"0"
            newBuilder = "%".join(strs)
            self.names.append(newBuilder)
            self.builders.append(createBuilder(newBuilder))
            self.builderStats.append(BuilderGameStats(newBuilder))
        self.saveAll2()

    def save_builder_ratings_better(self):
        filename = "builderRatings.json"
        temp = []
        savetime = time.time()
        builderstats = self.getValidBuildersForStats()
        for i in builderstats:
            i:BuilderGameStats
            born = 0 if i.oldestGame is None else i.oldestGame.time
            age = savetime - born
            #format the age to be more readable
            age = datetime.timedelta(seconds=age).__str__()
            
            info = {
                "name": i.name,
                "mu": f"{i.rating.mu:.2f}",
                "sigma": f"{i.rating.sigma:.2f}",
                "played": i.played,
                "age": age,
            }
            temp.append(info)
        temp.sort(key=lambda x: float(x["mu"]), reverse=True)
        with open(filename, "w") as f:
            json.dump(temp, f, indent=4)

    def saveAll2(self):
        saveBuilderGames()
        self.reloadBuilderStats()
        recalculateBuilderRatings()
        self.save_builder_ratings_better()

    def reloadBuilderStats(self):
        self.builderStats:list[BuilderGameStats] = []
        for i in self.names:
            self.builderStats.append(BuilderGameStats(i))
        games = getBuilderGames()
        for i in games:
            if i.white in self.names:
                self.builderStats[self.names.index(i.white)].registerGame(i)
            if i.black in self.names:
                self.builderStats[self.names.index(i.black)].registerGame(i)
        for i in self.builderStats:
            i.rating = getBuilderRating(i.name)

            
        
def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)
if __name__ == "__main__":
    force_exit = False
    opt = ExperimentalOptimizer(1)
    additionalBuilders = 3
    infinite = True
    while opt.gamecount_missing() > 0 or infinite:
        if opt.getMinPlayedGames() > 7:
            total = opt.getValidBuildersForStats()
            if len(total) > 10:  
                lowest30 = min(max(opt.amt_threshold(0.3), len(total)//3), len(total)//2)
                if lowest30 > 6:
                    purgecount = lowest30
                    print(f"Purging {purgecount} lowest performers")
                    opt.purgeLowestPerformers(purgecount)
                
                if opt.avg_playedgames() > 10:
                    print("Mutating from best builders, adding", additionalBuilders, "additional builders")
                    opt.mutateBestBuilders(additionalBuilders, 0.25)
                    print("Mutating from best builder, adding", additionalBuilders, "additional builders")
                    opt.mutateBestBuilder(additionalBuilders, 0.1)
                    print("Copying best builder for", additionalBuilders, "additional builders")
                    opt.copyBestBuilder(additionalBuilders)
            print("Pushing", additionalBuilders, "additional builders")
            opt.push_additional_builders(math.ceil(additionalBuilders/2), 1)
            opt.push_additional_builders(additionalBuilders//2, 2)
        opt.playGames()
        print(f"Missing: {opt.gamecount_missing()}")
        #break
