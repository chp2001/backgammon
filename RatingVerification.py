import OptimalityTester as OT
import trueskill
import math
import random
import time
import datetime

import os

#check if there is a folder named RatingTest
if not os.path.exists("RatingTest"):
    os.makedirs("RatingTest")
#check if there is a file in that folder named iteration.txt
if not os.path.exists("RatingTest/iteration.txt"):
    #if not, create it and write 0 in it
    f = open("RatingTest/iteration.txt", "w")
    f.write("0")
    f.close()
#open the file and read the number of iterations
f = open("RatingTest/iteration.txt", "r")
iteration = int(f.read())
f.close()
def chooseRandomName():
    names = OT.AIStartRatings.keys()
    return random.choice(list(names))
def generateRandomGameResults(num:int, winChance:float=0.5)->list[OT.Result]:
    def chance()->bool:
        return random.random() > winChance
    results = []
    for i in range(num):
        results.append(OT.Result("default", chooseRandomName(), chance()))
    return results
def applyRating(result:OT.Result, rating:trueskill.Rating)->trueskill.Rating:
    if rating is None:
        rating = trueskill.Rating()
    if result.res == False:
        a, b = trueskill.rate_1vs1(rating, OT.getAIRating(result.black))
    else:
        b, a = trueskill.rate_1vs1(OT.getAIRating(result.black), rating)
    return a
def saveResultsToFile(results:list[OT.Result], filename:str):
    f = open(filename, "w")
    for result in results:
        f.write(str(result) + "\n")
    f.close()
def loadResultsFromFile(filename:str)->list[OT.Result]:
    f = open(filename, "r")
    results = []
    for line in f.readlines():
        results.append(OT.Result.fromStr(line))
    f.close()
    return results
def calcRatingFromResults(results:list[OT.Result])->trueskill.Rating:
    rating = None
    for result in results:
        rating = applyRating(result, rating)
    return rating
#check if there is a file in that folder named games.txt
if not os.path.exists("RatingTest/games.txt"):
    temp = generateRandomGameResults(100)
    saveResultsToFile(temp, "RatingTest/games.txt")
loadLastGames = False
if loadLastGames:
    #load the games from the file
    games = loadResultsFromFile("RatingTest/games.txt")
else:
    #generate new games
    games = generateRandomGameResults(100, 0.9)
    #save the games to the file
    saveResultsToFile(games, "RatingTest/games.txt")
#calculate the rating from the games
rating = calcRatingFromResults(games)
#write the rating to the file
f = open("RatingTest/rating.txt", "w")
f.write(str(rating) + "\n")
f.close()
#prepare to shuffle and recalculate the rating
#for each shuffle, append the calculated rating to the file 'ratings.txt'
f = open("RatingTest/ratings.txt", "w")
f.write(str(rating) + "\n")
f.close()
numShuffles = 100
for i in range(numShuffles):
    #shuffle the games
    random.shuffle(games)
    #calculate the rating
    rating = calcRatingFromResults(games)
    #append the rating to the file
    f = open("RatingTest/ratings.txt", "a")
    f.write(str(rating) + "\n")
    f.close()
    #print the progress
    print("Shuffle " + str(i) + " of " + str(numShuffles) + " done")

#increase the iteration number
iteration += 1
#save the iteration number  
f = open("RatingTest/iteration.txt", "w")
f.write(str(iteration))
f.close()

#Ratings verified as accurate as of 1/28/2023