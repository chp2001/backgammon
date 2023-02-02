import time
import datetime
import random
from typing import Callable
from src.colour import Colour
from src.game import Game
from src.experiment import GamePlayer
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
import os
from src.bcperry2 import globalFeatures
globalFeatures = globalFeatures[:8]
def configStartRating(percentile:float):
    new = trueskill.Rating()
    mu = new.mu
    sigma = new.sigma
    #assuming percentile is between 0 and 1, average is at 0.5
    mu = mu + (percentile - 0.5) * sigma
    return trueskill.Rating(mu, sigma)
AIStartRatings = {
    #"MoveRandomPiece": configStartRating(0.1),
    #"MoveFurthestBackStrategy": configStartRating(0.6),
    #"CompareAllMovesSimple": configStartRating(0.3),
    #"player1_anderson": configStartRating(0.5),
    #"player2_anderson": configStartRating(0.5),
    #"CompareAllMovesWeightingDistanceAndSinglesWithEndGame": configStartRating(0.7),
    #"CompareAllMovesWeightingDistanceAndSingles": configStartRating(0.6),
    "CompareAllMovesWeightingDistance": configStartRating(0.5),
    #"player1_bcperry2": configStartRating(0.6),
    #"player2_bcperry2": configStartRating(0.5),
}
AINames = list(AIStartRatings.keys())
def copyRating(rating:trueskill.Rating):
    return trueskill.Rating(rating.mu, rating.sigma)
def getRating(name:str):
    return copyRating(AIStartRatings[name])
class Result:
    def __init__(self, white, black, res:bool, _time:float=None):
        #With old system, res was true for black win. 
        #With new system, res is true for white win
        if type(white) != str:
            white = white.__name__
        if type(black) != str:
            black = black.__name__
        self.white = white
        self.black = black
        self.res = res
        self.winner = white if res else black
        self.loser = black if res else white
        self.time = _time if _time is not None else time.time()
    def __str__(self):#we want to be able to use this to load from a string
        return "%s,%s,%s,%s" % (self.white, self.black, int(self.res), self.time)
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
        return Result(white, black, int(res), float(time))
def ratingRange()->list[float]:
    rateMin = math.inf
    rateMax = 0
    for name, rating in AIStartRatings.items():
        rateMin = min(rateMin, rating.mu)
        rateMax = max(rateMax, rating.mu)
    if rateMin == rateMax:
        rateMin = 0
    return [rateMin, rateMax]
temp = ratingRange()
minRating = temp[0]
maxRating = temp[1]
class OrderAgnosticRating:
    def __init__(self, ratingNum:float=0, count:int=0):
        self.rating = ratingNum
        self.count = count
    def add(self, res:Result):
        if res.res:
            self.rating += getRating(res.black).mu - minRating
        else:
            self.rating += getRating(res.black).mu - maxRating
        self.count += 1
    def getRating(self):
        if self.count == 0:
            return 0
        return 10*self.rating / self.count
    def __str__(self):
        return "%s,%s" % (self.rating, self.count)
    def __repr__(self):
        return str(self)
#When running games, white will always be a builder, and black will always be a strategy
class GameHistory:
    def __init__(self, filename:str, filepath:str=None):
        self.filename = filename if filepath is None else filepath + filename
        self.games = []
        self.calculated = {}
        self.load()
    def load(self):
        try:
            self.games = []
            with open(self.filename, "r") as f:
                for line in f:
                    self.games.append(Result.fromStr(line))
            self.changeAll()
        except FileNotFoundError:
            with open(self.filename, "w") as f:
                f.write("")
    def save(self):
        with open(self.filename, "w") as f:
            for game in self.games:
                f.write(str(game) + "\n")
    def add(self, game:Result):
        self.games.append(game)
        self.changeAll()
    def addBatch(self, games:list[Result]):
        self.games.extend(games)
        self.save()
    def isChanged(self, key:str):
        if key in self.calculated:
            return not self.calculated[key]
        return True
    def change(self, key:str):
        if key in self.calculated:
            self.calculated[key] = False
        else:
            self.calculated[key] = False
    def changeAll(self):
        self.calculated = {}
    def calculate(self, key:str):
        if key in self.calculated:
            self.calculated[key] = True
        else:
            self.calculated[key] = True
    def getBuilderNames(self):
        if self.isChanged("builders"):
            self.builders = []
            for game in self.games:
                if not game.white in self.builders:
                    self.builders.append(game.white)
            self.change("builders")
        return self.builders
    def getStrategyNames(self):
        return AINames
    def getBuilderGames(self, builder:str):
        if self.isChanged("builderGames"):
            self.builderGames = {}
            for game in self.games:
                if not game.white in self.builderGames:
                    self.builderGames[game.white] = []
                self.builderGames[game.white].append(game)
            self.calculate("builderGames")
        return self.builderGames[builder]

class Builder:
    def __init__(self, name:str):
        self.name = name
        self.active = True
        self.games = []
        self.gameCount = 0
        self.win = 0
        self.loss = 0
        self.rating = trueskill.Rating()
        self.orderAgnosticRating = OrderAgnosticRating()
        self.opponents = {}
        self.opponentStats = {}
        for opponent in AINames:
            self.opponentStats[opponent] = {"win":0, "loss":0}
            self.opponents[opponent] = 0
        self.ratingHistory = []
        self.ratingHistory.append(self.rating)
        self.history = None
        self.strategy = AIBuilder_bcperry2(self.name)
    def link(self, history:GameHistory):
        self.history = history
        for game in self.history.getBuilderGames(self.name):
            self.addGame(game)
            self.rateGame(game)
    def addGame(self, game:Result):
        self.games.append(game)
        self.gameCount += 1
        if game.res:
            self.win += 1
        else:
            self.loss += 1
        if game.black in self.opponents:
            self.opponents[game.black] += 1
            self.opponentStats[game.black]["win"] += 1 if game.res else 0
            self.opponentStats[game.black]["loss"] += 0 if game.res else 1
        else:
            self.opponents[game.black] = 1
            self.opponentStats[game.black] = {"win":1 if game.res else 0, "loss":0 if game.res else 1}
    def rateGame(self, game:Result):
        if game.res:
            self.rating, _ = trueskill.rate_1vs1(self.rating, getRating(game.black))
        else:
            _, self.rating = trueskill.rate_1vs1(getRating(game.black), self.rating)
        self.ratingHistory.append(self.rating)
        self.orderAgnosticRating.add(game)
    def recalculateRating(self):
        self.rating = trueskill.Rating()
        self.ratingHistory = []
        for game in self.games:
            self.rateGame(game)
    def getRating(self):
        return copyRating(self.rating)
    def getRatingHistory(self):
        return self.ratingHistory
    def getWinRate(self):
        return self.win / (self.win + self.loss)
    def getWinRateAgainst(self, opponent:str):
        if opponent in self.opponents:
            return self.opponentStats[opponent]["win"] / self.opponents[opponent]
        return 0
    def __str__(self):
        #return "%s,%s,%s,%s,%s,%s,%s" % (self.name, self.win, self.loss, self.rating.mu, self.rating.sigma, self.orderAgnosticRating.getRating(), self.active)
        return f"{self.name},{self.win},{self.loss},"+\
            f"{self.rating.mu:.2f},"+\
            f"{self.rating.sigma:.2f},"+\
            f"{self.orderAgnosticRating.getRating():.2f},"+\
            f"{self.active}"
    def leaderboardStr(self):
        sting = ""
        sting += f"{self.name}\n ({self.win}W/{self.loss}L) \n"
        sting += f"Rating: {self.rating.mu:.2f} \n"
        sting += f"Order Agnostic Rating: {self.orderAgnosticRating.getRating():.2f} \n"
        return sting
    def __repr__(self):
        return str(self)
    def __eq__(self, other):
        if type(other) != Builder:
            return False
        return self.name == other.name and self.win == other.win and \
            self.loss == other.loss and self.rating == other.rating
    def deactivate(self):
        self.active = False
    def activate(self):
        self.active = True
    @staticmethod
    def fromStr(line:str):#Should not be used, better to create a new builder and link it to the history
        name, win, loss, mu, sigma, orderAgn, active = line.split(",")
        b = Builder(name)
        b.win = int(win)
        b.loss = int(loss)
        b.rating = trueskill.Rating(float(mu), float(sigma))
        b.orderAgnosticRating = OrderAgnosticRating(float(orderAgn), int(win) + int(loss))
        b.active = bool(active)
        return b
    def getStrategy(self):
        return self.strategy
    def getConstants(self):
        return self.strategy.getConstants()
    def getConstantsList(self):
        return list(self.strategy.getConstants().values())

class DataManager:
    def __init__(self, filename:str, filepath:str=None):
        self.filename = filename if filepath is None else filepath + filename
        self.builders = {}
        self.activeBuilders = []
        self.history = GameHistory("games.txt", filepath=filepath)
        self.load()
        
    def load(self):
        self.history.load()
        for builder in self.history.getBuilderNames():
            self.builders[builder] = Builder(builder)
            self.builders[builder].link(self.history)
        return
        try:
            with open(self.filename, "r") as f:
                for line in f:
                    name, win, loss, mu, sigma, orderAgn, active = line.split(",")
                    if name in self.builders:
                        self.builders[name].active = bool(active)
        except:
            pass
        
    def save(self):
        self.history.save()
        temp = self.getBuildersByRating()
        with open(self.filename, "w") as f:
            for builder in temp:
                tempBuilder = self.builders[builder]
                if len(tempBuilder.games) > 0:
                    f.write(tempBuilder.leaderboardStr() + "\n")
    def addGame(self, game:Result):
        self.history.add(game)
        if not game.white in self.builders:
            self.builders[game.white] = Builder(game.white)
        self.builders[game.white].addGame(game)
        self.builders[game.white].rateGame(game)
    def addBatch(self, games:list[Result]):
        self.history.addBatch(games)
        for game in games:
            if not game.white in self.builders:
                self.builders[game.white] = Builder(game.white)
            self.builders[game.white].addGame(game)
            self.builders[game.white].rateGame(game)
    def getBuilder(self, name:str):
        return self.builders[name]
    def getBuilders(self):
        return self.builders
    def getBuilderNames(self):
        return self.history.getBuilderNames()
    def getStrategyNames(self):
        return self.history.getStrategyNames()
    def getBuilderGames(self, builder:str):
        return self.history.getBuilderGames(builder)
    def getBuilderWinRate(self, builder:str):
        return self.builders[builder].getWinRate()
    def getRating(self, name:str):
        if name in AINames:
            return getRating(name)
        return self.builders[name].getRating()
    def getRatingHistory(self, name:str):
        if name in AINames:
            return [getRating(name)]
        return self.builders[name].getRatingHistory()
    def getActiveBuilders(self):
        return [b for b in self.builders if self.builders[b].active]
    def getInactiveBuilders(self):
        return [b for b in self.builders if not self.builders[b].active]
    def getBuildersByRating(self, ascending:bool = False):
        return sorted(self.builders, key=lambda b:self.builders[b].getRating(), reverse=not ascending)
    def getBuildersByRatingAgnostic(self, ascending:bool = False):
        return sorted(self.builders, key=lambda b:self.builders[b].orderAgnosticRating.getRating(), reverse=not ascending)
    def getBuildersByGames(self, ascending:bool = False):
        return sorted(self.builders, key=lambda b:len(self.builders[b].games), reverse=not ascending)
    def deactivateBuilder(self, builder:str):
        self.builders[builder].deactivate()
    def activateBuilder(self, builder:str):
        self.builders[builder].activate()
    def addBuilder(self, builder=None):
        if isinstance(builder, Builder):
            self.builders[builder.name] = builder
        elif isinstance(builder, str):
            self.builders[builder] = Builder(builder)
        else:
            raise TypeError("Builder must be a string or a Builder object")

class PopulationManager:
    def __init__(self, parent=None):
        self.parent = None
        self.builders = {}
        self.builderCount = 0
        self.activeBuilders = []
        self.inactiveBuilders = []
        self.dataCache = {}
        self.uptodate = False
        #calculate target games per builder
        self.targetGames = 50
        self.targetMaxGames = self.targetGames * 3
        self.targetActiveBuilders = 100
        if parent is not None:
            self.link(parent)
            self.getBuilderData()
    def link(self, parent):
        self.parent = parent
    def getBuilderData(self):
        self.builders = self.parent.builders
        self.builderCount = len(self.builders)
        self.activeBuilders = self.parent.dataManager.getActiveBuilders()
        self.inactiveBuilders = self.parent.dataManager.getInactiveBuilders()
        self.uptodate = True
        self.dataCache = {}
    def getValidPops(self):
        if not self.uptodate:
            self.getBuilderData()
        return [b for b in self.builders if self.builders[b].active and self.parent.gameRunner.useBuilderForGames(self.builders[b])]
    def getRatingPercentile(self, ratio:float, below:bool=True): #ratio is a number between 0 and 1, we want to return the list of builders below that percentile
        builders = self.parent.dataManager.getBuildersByRating()
        builders = self.filterOutFewGames(builders)
        amt = int(len(builders) * ratio)
        if below:
            return builders[:amt]
        return builders[-amt:]
    def getRatingPercentileAgnostic(self, ratio:float, below:bool=True): #ratio is a number between 0 and 1, we want to return the list of builders below that percentile
        builders = self.parent.dataManager.getBuildersByRatingAgnostic()
        builders = self.filterOutFewGames(builders)
        amt = math.ceil(len(builders) * ratio)
        if below:
            return builders[:amt]
        return builders[-amt:]
    def getBuildersNeedingGames(self, amt:int, cond:Callable[[Builder], bool]=lambda b:True):
        builders = self.parent.dataManager.getBuildersByGames(ascending=True)
        builders = [b for b in builders if cond(self.builders[b])]
        if amt > len(builders):
            amt = len(builders)
        return builders[:amt]
    def getAvgGameCount(self):
        if not self.uptodate:
            self.getBuilderData()
        return sum([self.builders[b].gameCount for b in self.builders]) / self.builderCount
    def filterOutFewGames(self, builders:list[str], minGames:int=10) -> list[str]:
        return [b for b in builders if self.builders[b].gameCount >= minGames]
    def filterOutMaxGames(self, builders:list[str], maxGames:int=100) -> list[str]:
        return [b for b in builders if self.builders[b].gameCount <= maxGames]
    def needRepopulation(self)->bool:
        if not self.uptodate:
            self.getBuilderData()
        builders1 = list(self.builders.keys())
        builders1 = self.filterOutFewGames(builders1)
        if len(builders1) < 10:
            return False
        builders = self.getValidPops()
        #builders = self.filterOutMaxGames(builders, self.targetMaxGames)
        #if len(builders) < self.targetActiveBuilders:
        #    return True
        builders = self.filterOutMaxGames(builders, self.targetGames)
        if len(builders) < self.targetActiveBuilders:
            return True
        return False
    def getBuildersToRepopulate(self)->int:
        if not self.uptodate:
            self.getBuilderData()
        builders = self.getValidPops()
        print("There are currently", str(len(builders))+"/"+str(self.targetActiveBuilders), "valid builders")
        #exit()
        builders = self.filterOutMaxGames(builders, self.targetMaxGames)
        print("There are currently", str(len(builders))+"/"+str(self.targetActiveBuilders), "builders with less than", self.targetMaxGames, "games")
        if self.targetActiveBuilders - len(builders) == 0:
            amt = random.randrange(0,10)
            print("No need to repopulate, adding", amt, "builders")
            return amt
        if len(builders) < self.targetActiveBuilders:
            amt = max(random.randrange(0,10),self.targetActiveBuilders - len(builders))
            print("Not enough builders, adding", amt, "builders")
            return amt
        amt = random.randrange(0,10)
        print("Repopulating", amt, "builders")
        return amt
    def managePopulation(self)->None:
        if not self.uptodate:
            self.getBuilderData()
        if len(self.builders) < self.targetActiveBuilders:
            print("Not enough builders, adding", self.targetActiveBuilders - len(self.builders), "builders")
            for i in range(self.targetActiveBuilders - len(self.builders)):
                self.parent.addBuilder(self.parent.createFromConst(self.parent.newBuilder()))
            self.getBuilderData()
        elif self.needRepopulation():
            amt = self.getBuildersToRepopulate()
            print("Repopulating", amt, "builders")
            for i in range(amt):
                self.repopulate()
            self.getBuilderData()
        else:
            self.repopulate()
    def repopulate(self)->None:
        #two types of repopulation: random off of population, random off of best
        #random off of population
        amtRepopable = len(self.filterOutFewGames(list(self.builders.keys())))
        if amtRepopable < 10:
            return
        if random.random() < 0.5:
            self.repopulatePopulation()
        else:
            self.repopulateBest()
    def repopulatePopulation(self)->None:
        #get a the center of the population
        base = self.getRepopulationBase()
        #add some noise to it
        constants = self.randomNoise(base, 0.5)
        #create a new builder with those constants
        builder = self.parent.createFromConst(constants)
        #add it to the population
        self.parent.addBuilder(builder)
    def repopulateBest(self)->None:
        #get a list of the best builders
        builders = self.getRatingPercentile(0.8, below=False)
        #pick one at random
        builder = random.choice(builders)
        #get their constants
        constants = self.builders[builder].getConstantsList()
        #add some noise to it
        constants = self.randomNoise(constants, 0.05)
        if random.random() < 0.5:
            constants = self.silenceRandomConstant(constants)
        if random.random() < 0.5:
            constants = self.mutateSingleConstant(constants, 0.1)
        if random.random() < 0.5:
            constants = self.activateRandomConstant(constants, 0.2)
        #create a new builder with those constants
        builder = self.parent.createFromConst(constants)
        #add it to the population
        self.parent.addBuilder(builder)

    def getRepopulationBase(self)->list[float]:
        builders = self.getRatingPercentile(0.5, below=False)
        if len(builders) == 0:
            return [0 for _ in globalFeatures]
        constants = [0 for _ in globalFeatures]
        for b in builders:
            for i in range(len(constants)):
                constants[i] += self.builders[b].getConstantsList()[i]
        for i in range(len(constants)):
            constants[i] /= len(builders)
        return constants
    def randomNoise(self, base:list[float], scale:float=1)->list[float]:
        return [base[i] + random.uniform(-scale,scale) for i in range(len(base))]
    def getActiveConstantIndices(self, constants:list[float])->list[int]:
        return [i for i in range(len(constants)) if constants[i] != 0]
    def silenceRandomConstant(self, constants:list[float])->list[float]:
        indices = self.getActiveConstantIndices(constants)
        if len(indices) == 0:
            return constants
        index = random.choice(indices)
        constants[index] = 0
        return constants
    def activateRandomConstant(self, constants:list[float], scale:float=1)->list[float]:
        indices = self.getActiveConstantIndices(constants)
        if len(indices) == len(constants):
            return constants
        index = random.choice([i for i in range(len(constants)) if i not in indices])
        constants[index] = random.gauss(0,scale)
        return constants
    def mutateSingleConstant(self, constants:list[float], scale:float=1)->list[float]:
        index = random.randint(0, len(constants)-1)
        constants[index] += random.gauss(0,scale)
        return constants

class GameRunner:
    def __init__(self,parent=None):
        self.parent = parent
        self.popManager:PopulationManager = self.parent.populationManager
        self.dataManager:DataManager = self.parent.dataManager
        self.gameCount = 0
        self.maxGameConcurrent = mp.cpu_count()
    def calcMaxConcurrent(self)->int:
        max_cpu = mp.cpu_count()
        ai_count = len(self.popManager.builders)
        maxNum = max(max_cpu, ai_count)
        return maxNum
    def gameTarget(self, builder:Builder)->int:
        targets = []
        for i in AINames:
            temp = [i, builder.opponents[i] if i in builder.opponents else 0]
            targets.append(temp)
        targets.sort(key=lambda x: x[1])
        temp = [i[0] for i in targets if i[1] == targets[0][1]]
        return random.choice(temp)
    def useBuilderForGames(self, builder:Builder)->bool:
        if builder.gameCount < 5:
            return True
        if builder.gameCount > 5 and builder.win == 0:
            return False
        if builder.gameCount > 10 and builder.win < 2:
            return False
        if builder.gameCount > 20 and builder.win < 6:
            return False
        if builder.gameCount > 50 and builder.win < 20:
            return False
        if builder.gameCount > 100 and builder.win < 50:
            return False
        return True
    def runGame(self, builder:Builder)->None:
        white = builder.strategy
        black = StrategyFactory.create_by_name(self.gameTarget(builder))
        game = GamePlayer(white, black)
        res = game(self.gameCount, 10)
        if res[1] == None:
            print("TIMEOUT")
            return Result(builder.name, black.__class__.__name__, False)
        if res[1] == Colour.WHITE:
            return Result(builder.name, black.__class__.__name__, True)
        return Result(builder.name, black.__class__.__name__, False)
    def runGames(self):
        self.maxGameConcurrent = self.calcMaxConcurrent()
        print(f"Max {self.maxGameConcurrent};",end="")
        targets = self.popManager.getBuildersNeedingGames(self.maxGameConcurrent, self.useBuilderForGames)
        targets = [self.parent.builders[i] for i in targets]
        if len(targets) == 0:
            return
        print(f"Running {len(targets)};",end="")
        with mp.Pool(mp.cpu_count()) as pool:
            results = pool.map(self.runGame, targets)
        self.parent.addBatch(results)
        self.gameCount += len(results)
        self.parent.save()



        
    
class BuilderPool:
    def __init__(self, filepath:str="Optimizer_Unfeatured/") -> None:
        if not filepath.endswith("/"):
            filepath += "/"
        if not os.path.exists(filepath):
            os.mkdir(filepath)
        self.dataManager = DataManager("builders.txt",filepath=filepath)
        self.builders = self.dataManager.getBuilders()
        self.activeBuilders = self.dataManager.getActiveBuilders()
        self.builderCount = len(self.activeBuilders)
        self.populationManager = PopulationManager(self)
        self.gameRunner = GameRunner(self)
        self.cycleCount = 0
    
    def save(self):
        self.dataManager.save()
    
    def newBuilder(self, base=None, scale:float = 1)->list[float]:
        if isinstance(base, str):
            base = self.dataManager.getBuilder(base)
        if isinstance(base, Builder):
            base = base.getConstantsList()
        if base == None:
            base = [0 for _ in globalFeatures]

        for i in range(len(base)):
            base[i] = random.gauss(base[i], scale)
        return base
    
    def freshBuilder(self)->list[float]:
        return self.newBuilder(scale=0)

    def createBuilder(self, name:str)->Builder:
        return Builder(name)

    def createFromConst(self, constants:list[float])->Builder:
        return Builder("%".join([f"{c:.2f}" for c in constants]))

    def addBuilder(self, builder:Builder):
        self.dataManager.addBuilder(builder)
        self.builders[builder.name] = builder
        self.activeBuilders.append(builder)
        self.builderCount += 1

    def addGame(self, game:Result):
        self.dataManager.addGame(game)

    def addBatch(self, games:list[Result]):
        self.dataManager.addBatch(games)

    def cycle(self):
        if self.cycleCount % 10 == 0:
            print("Managing Population")
            self.populationManager.managePopulation()
            self.cycleCount = 0
        #return
        self.gameRunner.runGames()
        self.cycleCount += 1
        self.save()


        
if __name__ == "__main__":
    optPool = BuilderPool()
    optPool.save()
    #print(optPool.activeBuilders)
    #print(optPool.populationManager.targetGames)
    #exit()
    while True:
        optPool.cycle()
        print(len(optPool.dataManager.getBuilders()))
        #break