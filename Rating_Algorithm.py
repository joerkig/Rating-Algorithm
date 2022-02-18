import statistics
import os
import json
import math
import csv
import Multi

# TODO: download from scoresaber if map missing

# Get ID
try:
    f = open('bs_path.txt', 'r')
    bs_path = f.read()
    f.close()
except FileNotFoundError:
    print('Enter Beat Saber custom songs folder:')
    # TODO: validate path
    bs_path = input()
    f = open('bs_path.txt', 'w')
    dat = f.write(bs_path)
    f.close()

print('Enter song ID:')
song_id = input()
# song_id = "1fe06"  # For Debugging
print('Enter difficulty (like ExpertPlus):')
song_diff = input() + 'Standard.dat'
#song_diff = "ExpertPlusStandard.dat"


# Minimum precision (how close notes are together) to consider 2 very close notes a slider
sliderPrecision = 1/6
dotSliderPrecision = 1/5

staminaRollingAverage = 128
patternRollingAverage = 128
combinedRollingAverage = 128

"""
https://bsmg.wiki/mapping/map-format.html#notes-2
"""


class Bloq:
    def __init__(self, type, cutDirection, bloqPos, startTime, swingTime):
        self.numNotes = 1
        self.type = type
        self.cutDirection = cutDirection
        self.bloqPos = bloqPos
        self.swingAngle = 200
        self.time = startTime
        self.swingTime = swingTime
        self.swingSpeed = 0
        self.forehand = True
        self.angleDiff = Multi.ANGLE_EASY
        self.posDiff = Multi.SIDE_EASY
        self.stamina = 0
        self.patternDiff = 0
        self.combinedDiff = 0
        self.combinedDiffSmoothed = 0

        # Non-negoitables, Up and a select diagonal is backhand
        if self.cutDirection in [0, 4, 5]:  # 4 = NW Left Hand, 5 = NE Right Hand
            if (self.type == 0 & self.cutDirection in [0, 4]):
                self.forehand = False
            elif (self.type == 1 & self.cutDirection in [0, 5]):
                self.forehand = False
        # Non-negoitables, Down and a select diagonal is forehand
        elif self.cutDirection in [1, 6, 7]:
            # 6 = SE Left Hand, 7 = SW Right Hand
            if (self.type == 0 & self.cutDirection in [1, 7]):
                self.forehand = True
            elif (self.type == 1 & self.cutDirection in [1, 6]):
                self.forehand = True
        else:
            if type == 0:
                # If it's the first note, assign most likely, correct Forehand/backhand assignment
                self.forehand = cutDirection in [5, 3, 7, 1]
            elif type == 1:
                self.forehand = cutDirection in [6, 4, 2, 1]
        self.calcAngleDiff()

    def addNote(self):
        self.numNotes += 1
        self.swingAngle += 36.87

    def setForehand(self, hand):
        self.forehand = hand
        self.calcAngleDiff()
        self.calcPosDiff()

    # TODO: shorten function
    def calcPosDiff(self):
        if(self.type == 0):  # Left Hand Side to Side Diff
            # LH centered around 2
            if(self.forehand):
                # Checks if position is easy, medium or difficult

                # TODO: probably a typo below (ranges 1-4, not 0-3)
                if(self.bloqPos[0] == 2):
                    self.posDiff = Multi.SIDE_EASY
                elif(self.bloqPos[0] in [1, 3]):
                    self.posDiff = Multi.SIDE_SEMI_MID
                elif(self.bloqPos[0] == 4):
                    self.posDiff = Multi.SIDE_MID

            elif(not self.forehand):
                # Checks if position is easy, medium or difficult
                if(self.bloqPos[0] == 0):
                    self.posDiff = Multi.SIDE_HARD
                elif(self.bloqPos[0] == 1):
                    self.posDiff = Multi.SIDE_MID
                elif(self.bloqPos[0] == 2):
                    self.posDiff = Multi.SIDE_SEMI_MID
                elif(self.bloqPos[0] == 3):
                    self.posDiff = Multi.SIDE_EASY
        elif(self.type == 1):  # Right Hand
            if(self.forehand):
                # Checks if position is easy, medium or difficult
                if(self.bloqPos[0] == 1):
                    self.posDiff = Multi.SIDE_EASY
                elif(self.bloqPos[0] in [0, 2]):
                    self.posDiff = Multi.SIDE_SEMI_MID
                elif(self.bloqPos[0] == 3):
                    self.posDiff = Multi.SIDE_MID
            elif(not self.forehand):
                # Checks if position is easy, medium or difficult
                if(self.bloqPos[0] == 3):
                    self.posDiff = Multi.SIDE_HARD
                elif(self.bloqPos[0] == 2):
                    self.posDiff = Multi.SIDE_MID
                elif(self.bloqPos[0] == 1):
                    self.posDiff = Multi.SIDE_SEMI_MID
                elif(self.bloqPos[0] == 0):
                    self.posDiff = Multi.SIDE_EASY

        # Up and Down Diff
        if(self.forehand):
            if(self.bloqPos[1] == 0):
                self.posDiff *= Multi.VERT_EASY
            elif(self.bloqPos[1] == 1):
                self.posDiff *= Multi.VERT_SEMI_MID
            elif(self.bloqPos[1] == 2):
                self.posDiff *= Multi.VERT_MID
        elif(not self.forehand):
            if(self.bloqPos[1] == 0):
                self.posDiff *= Multi.VERT_MID
            elif(self.bloqPos[1] == 1):
                self.posDiff *= Multi.VERT_SEMI_MID
            elif(self.bloqPos[1] == 2):
                self.posDiff *= Multi.VERT_EASY

    # TODO: shorten function
    def calcAngleDiff(self):
        if(self.type == 0):  # Left Hand
            if(self.forehand):
                # Checks if angle is easy, medium or difficult
                if(self.cutDirection in [1, 7]):
                    self.angleDiff = Multi.ANGLE_EASY
                elif(self.cutDirection == 3):
                    self.angleDiff = Multi.ANGLE_SEMI_MID
                elif(self.cutDirection in [5, 6]):
                    self.angleDiff = Multi.ANGLE_MID
                elif(self.cutDirection in [0, 2, 4]):
                    self.angleDiff = Multi.ANGLE_HARD
            elif(not self.forehand):
                # Checks if angle is easy, medium or difficult
                if(self.cutDirection in [1, 3]):
                    self.angleDiff = Multi.ANGLE_HARD
                elif(self.cutDirection in [5, 6]):
                    self.angleDiff = Multi.ANGLE_MID
                elif(self.cutDirection == 2):
                    self.angleDiff = Multi.ANGLE_SEMI_MID
                elif(self.cutDirection in [0, 4]):
                    self.angleDiff = Multi.ANGLE_EASY
        elif(self.type == 1):  # Right Hand
            if(self.forehand):
                # Checks if angle is easy, medium or difficult
                if(self.cutDirection in [1, 6]):
                    self.angleDiff = Multi.ANGLE_EASY
                elif(self.cutDirection == 2):
                    self.angleDiff = Multi.ANGLE_SEMI_MID
                elif(self.cutDirection in [4, 7]):
                    self.angleDiff = Multi.ANGLE_MID
                elif(self.cutDirection in [0, 3]):
                    self.angleDiff = Multi.ANGLE_HARD
            elif(not self.forehand):
                # Checks if angle is easy, medium or difficult
                if(self.cutDirection in [1, 2]):
                    self.angleDiff = Multi.ANGLE_HARD
                elif(self.cutDirection in [4, 7]):
                    self.angleDiff = Multi.ANGLE_MID
                elif(self.cutDirection == 3):
                    self.angleDiff = Multi.ANGLE_SEMI_MID
                elif(self.cutDirection in [0, 5]):
                    self.angleDiff = Multi.ANGLE_EASY


def load_song_dat(path):
    main_path = path
    try:
        with open(main_path) as json_dat:
            dat = json.load(json_dat)
    except FileNotFoundError:
        print("That map doesn't exist! Make sure it's downloaded and you spelt the map name correctly")
        print("Huh maybe it has a weird file name")
        print("This time I won't autocomplete it with Standard. you'll need to type out the whole map file name minus .dat")
        print('Enter difficulty (like ExpertPlusStandard):')
        song_diff = input()
        main_path = bs_song_path + song_folder + '/' + song_diff + '.dat'
        with open(main_path) as json_dat:
            dat = json.load(json_dat)

    return dat


# TODO: sliding window instead of reactive (for future expansion)
def extractBloqData(songNoteArray):

    BloqDataArray: list[Bloq] = []

    for i, block in enumerate(songNoteArray):

        # Checks if the note behind is super close, and treats it as a single swing
        if i == 0:
            BloqDataArray.append(Bloq(
                block["_type"], block["_cutDirection"], [block["_lineIndex"], block["_lineLayer"]], block["_time"], block["_time"] * mspb))
            BloqDataArray[-1].setForehand(block['_lineLayer'] != 2)

        # TODO: ??????
        elif (block["_time"] - songNoteArray[i-1]['_time'] <= (dotSliderPrecision if block["_cutDirection"] == 8 else sliderPrecision)
              and (block['_cutDirection'] in [songNoteArray[i-1]['_cutDirection'], 8])) or (block["_time"] - songNoteArray[i-1]['_time'] <= 0.001):

            # Adds 1 to keep track of how many notes in a single swing
            BloqDataArray[-1].addNote()

        else:
            BloqDataArray.append(
                Bloq(block["_type"], block["_cutDirection"], [block["_lineIndex"], block["_lineLayer"]], block["_time"], 0))
            if(BloqDataArray[-1].cutDirection not in [0, 1, 4, 5, 6, 7]):
                BloqDataArray[-1].setForehand(not BloqDataArray[-2].forehand)

            # calculates swingTime and Speed and shoves into class for processing later
            BloqDataArray[-1].swingTime = (BloqDataArray[-1].time -
                                           BloqDataArray[-2].time)*mspb
            BloqDataArray[-1].swingSpeed = BloqDataArray[-1].swingAngle / \
                BloqDataArray[-1].swingTime

            # TODO: move this elsewhere, should be part of processBloqData, not extract
            temp = 0
            # Uses a rolling average to judge stamina
            for j in range(0, staminaRollingAverage):
                if(len(BloqDataArray) >= j+1):
                    temp += (BloqDataArray[-1*(j+1)].swingSpeed)
            # Helps Speed Up the Average Ramp, then does a proper average past staminaRollingAverage/4 and switches to the conventional rolling average after
            if(len(BloqDataArray) < staminaRollingAverage/4):
                BloqDataArray[-1].stamina = (temp/(staminaRollingAverage/4))
            elif(len(BloqDataArray) < staminaRollingAverage):
                BloqDataArray[-1].stamina = (temp/len(BloqDataArray))
            else:
                BloqDataArray[-1].stamina = (temp/staminaRollingAverage)
            temp = 0
            # Uses a rolling average to judge pattern difficulty
            for j in range(0, patternRollingAverage):
                if(len(BloqDataArray) >= j+1):
                    temp += (BloqDataArray[-1*(j+1)].angleDiff *
                             BloqDataArray[-1*(j+1)].posDiff)
            # Helps Speed Up the Average Ramp, then does a proper average past staminaRollingAverage/4 and switches to the conventional rolling average after
            if(len(BloqDataArray) < patternRollingAverage/4):
                BloqDataArray[-1].patternDiff = (temp /
                                                 (patternRollingAverage/4))
            elif(len(BloqDataArray) < patternRollingAverage):
                BloqDataArray[-1].patternDiff = (temp/len(BloqDataArray))
            else:
                BloqDataArray[-1].patternDiff = (temp/patternRollingAverage)
            # The best way to compound the data to get reasonable results. I have no idea why it works but it does
            #BloqDataArray[-1].combinedDiff =  6*math.sqrt(math.sqrt((BloqDataArray[-1].stamina**2 + BloqDataArray[-1].patternDiff**2)*(min(BloqDataArray[-1].stamina*4,(BloqDataArray[-1].patternDiff)))+BloqDataArray[-1].stamina+BloqDataArray[-1].patternDiff))-6
            BloqDataArray[-1].combinedDiff = math.sqrt(
                BloqDataArray[-1].stamina**2 + BloqDataArray[-1].patternDiff**2)*math.sqrt(BloqDataArray[-1].stamina)
    return BloqDataArray

# TODO: misleading function name


def combineArray(array1, array2):
    combinedArray: list[Bloq] = array1 + array2
    combinedArray.sort(key=lambda x: x.time)

    # TODO: ask Lack what this does
    temp = len(combinedArray)
    i = 1
    while(i < temp):  # Cleans up Duplicate Times
        if(combinedArray[i].time == combinedArray[i-1].time):
            combinedArray[i-1].numNotes += 1
            combinedArray.pop(i)
            temp = len(combinedArray)
            i = i - 1
        i += 1

    # TODO: change from n**2 to sliding window
    for i in range(0, len(combinedArray)):
        temp = 0
        # Uses a rolling average to smooth difficulties between the hands
        for j in range(0, min(combinedRollingAverage, i)):
            temp += combinedArray[i -
                                  min(combinedRollingAverage, j)].combinedDiff
        combinedArray[i].combinedDiffSmoothed = 6 * \
            temp/min(combinedRollingAverage, i+1)

    return combinedArray


# Setup ------------------------------------------------------ #
bs_song_path = bs_path
if bs_song_path[-1] not in ['\\', '/']:  # Checks if song path is empty
    bs_song_path += '/'
song_options = os.listdir(bs_song_path)
for song in song_options:
    if song.find(song_id) != -1:
        song_folder = song
        break
song_folder_contents = os.listdir(bs_song_path + song_folder + '/')
for song in song_folder_contents:
    if song[-4:] in ['.egg', '.ogg']:
        song_file_name = song
        break

#---------------Where Stuff Happens-----------------------------------------------------------------------------#

song_dat = load_song_dat(bs_song_path + song_folder + '/' + song_diff)
song_info = load_song_dat(bs_song_path + song_folder + "/Info.dat")

bpm = song_info['_beatsPerMinute']
mspb = 60*1000/bpm  # milliseconds per beat

song_notes = song_dat['_notes']

# remove the bombs
song_notes = list(filter(lambda x: x['_type'] in [0, 1], song_notes))

# split into red and blue notes
songNoteLeft = [block for block in song_notes if block['_type'] == 0]
songNoteRight = [block for block in song_notes if block['_type'] == 1]

BloqDataLeft = extractBloqData(songNoteLeft)
BloqDataRight = extractBloqData(songNoteRight)

combinedArrayRaw = combineArray(BloqDataLeft, BloqDataRight)

# export results to spreadsheet
excelFileName = os.path.join(
    f"Spreadsheets/{song_id} {song_info['_songName']} {song_diff} export.csv")

try:
    f = open(excelFileName, 'w', newline="")
except FileNotFoundError:
    print('Making Spreadsheets Folder')
    os.mkdir('Spreadsheets')
    f = open(excelFileName, 'w', newline="")
finally:
    writer = csv.writer(f)
    writer.writerow(["_Time", "C Swing Speed degree/ms", "C Angle Diff", "C Pos Diff",
                    "C Stamina", "C Pattern Diff", "C CombinedDiff", "C SmoothedDiff"])
    for bloq in combinedArrayRaw:
        writer.writerow([bloq.time, bloq.swingSpeed, bloq.angleDiff, bloq.posDiff,
                        bloq.stamina, bloq.patternDiff, bloq.combinedDiff, bloq.combinedDiffSmoothed])
    f.close()

# calculate final difficulty
combinedArray = [bloq.combinedDiffSmoothed for bloq in combinedArrayRaw]
median = statistics.median(combinedArray)
print(median)

# saber length is 1 meter
# distance between top and bottom notes is roughly 1.5m
# distance between side to side notes it roughly 2m
# totalSwingAnglec = 200degrees + numberOfBlocks * RadToDegrees(tan-1(0.75/1))

# Import song dat file✅
# Filter note dat file into Left and Right Block arrays✅
# Identify stacks/sliders (maybe pauls/poodles) and turn the 2-4 Blocks into a single Block with a large swing angle ✅
# Calculate Block distance into seconds or ms 73.74 ✅
# using 100 degree in, 60 degree out rule to calculate beginning and end points of the saber✅
# using swingtime, swingAngle and 1 meter saber length, calculate saber speed ✅
# List off hard swing angles for both hands + Appended angle diff to class✅

# Each swing entry for left and right hand array should contain
# Block[numberOfBlocks[1 to 4], cutDirection, totalAngleNeeded[160-273.74], timeForSwing(ms), ForeHand?]✅

# Final difficulty based on Total amount of notes, fastest swings using a rolling average of 4, angle difficulty average for whole map ✅
