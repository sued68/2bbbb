import sqlite3
import json
import random
import os
from datetime import datetime

# ========== CONFIGURATION ==========
DB_PATH = os.getenv("DB_PATH", "/data/bingo.db")
DEPOSIT_BONUS = 10
MAX_CARDS_PER_USER = 3
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_ID", "6835994100"))
DEFAULT_CARD_PRICE = 20
DEFAULT_HOUSE_PERCENT = 10
DEFAULT_WITHDRAWAL_FEE_PERCENT = 5
DEFAULT_ROUND_DURATION = 300   # seconds

# Ensure the database directory exists
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    try:
        os.makedirs(db_dir, exist_ok=True)
        print(f"✅ Created database directory: {db_dir}")
    except Exception as e:
        print(f"❌ Failed to create directory {db_dir}: {e}")
        # Fallback to a local file in the current directory
        DB_PATH = "bingo.db"
        print(f"⚠️ Falling back to local database: {DB_PATH}")
# Write a test file
test_file = "/data/test_persistence.txt"
with open(test_file, "w") as f:
    f.write("This should persist.")
print(f"✅ Test file written to {test_file}")
# ========== 200 FIXED UNIQUE CARDS ==========
ALL_CARDS = {
  1: [14,12,10,5,9, 17,27,29,20,28, 35,31,"FREE",43,44, 49,58,46,53,54, 65,67,75,72,68],
  2: [7,13,2,11,4, 23,26,29,17,24, 35,40,"FREE",41,37, 60,53,47,57,49, 65,70,63,64,72],
  3: [4,6,7,15,3, 25,23,19,20,28, 40,45,"FREE",42,32, 51,54,58,52,60, 71,65,66,67,62],
  4: [1,13,7,12,11, 30,29,19,28,26, 34,33,"FREE",40,41, 54,59,47,53,48, 68,62,61,65,66],
  5: [7,2,1,4,15, 23,21,16,30,28, 37,34,"FREE",44,32, 49,48,47,51,52, 67,64,74,61,73],
  6: [8,13,12,5,2, 24,30,27,26,21, 42,33,"FREE",40,35, 53,51,60,56,52, 61,65,70,74,71],
  7: [2,11,6,8,9, 29,19,17,20,25, 38,37,"FREE",31,40, 54,48,50,57,58, 68,75,69,71,61],
  8: [5,11,9,7,13, 17,20,24,22,16, 42,41,"FREE",33,40, 56,55,49,51,60, 71,65,74,61,69],
  9: [1,4,11,5,7, 21,17,18,26,25, 32,33,"FREE",45,40, 52,51,49,60,54, 68,64,74,65,73],
  10: [14,5,4,9,10, 28,18,21,23,27, 42,44,"FREE",36,33, 56,51,47,58,60, 63,68,61,64,67],
  11: [7,10,5,8,4, 19,22,21,30,17, 33,34,"FREE",38,41, 56,49,60,46,58, 68,69,66,61,74],
  12: [9,11,6,12,15, 22,26,28,17,20, 40,43,"FREE",39,33, 52,49,50,51,60, 63,62,70,71,73],
  13: [10,12,5,7,4, 25,22,26,17,16, 42,36,"FREE",43,37, 56,59,46,53,60, 70,75,74,68,71],
  14: [5,1,13,15,4, 29,26,17,18,22, 42,35,"FREE",43,44, 53,51,50,46,55, 61,68,64,70,63],
  15: [11,12,6,7,8, 26,16,19,23,18, 35,42,"FREE",34,32, 50,51,55,49,53, 68,70,66,64,62],
  16: [8,15,13,3,9, 27,30,17,29,23, 44,40,"FREE",33,43, 51,57,47,60,55, 71,63,61,75,66],
  17: [15,13,5,1,4, 24,20,18,16,28, 31,34,"FREE",35,44, 52,53,50,57,47, 62,64,68,67,70],
  18: [9,12,7,1,15, 28,21,18,24,29, 36,40,"FREE",39,45, 53,48,52,57,51, 72,68,70,62,73],
  19: [14,13,7,15,5, 17,26,22,19,23, 34,44,"FREE",39,41, 56,52,46,48,51, 73,70,68,65,62],
  20: [7,3,11,8,12, 18,29,27,25,21, 38,31,"FREE",34,42, 55,56,60,52,57, 63,71,75,70,64],
  21: [15,14,2,3,5, 23,27,18,21,29, 45,42,"FREE",38,41, 48,49,54,46,53, 62,69,64,70,71],
  22: [15,4,8,11,14, 21,30,28,19,25, 32,37,"FREE",42,36, 51,58,59,60,56, 72,68,62,63,67],
  23: [9,11,5,14,6, 22,18,30,29,27, 36,38,"FREE",41,37, 48,50,55,51,49, 62,73,72,75,74],
  24: [14,15,11,12,10, 28,23,29,24,21, 42,32,"FREE",39,34, 52,49,56,59,55, 61,62,63,69,68],
  25: [3,8,4,11,7, 28,22,18,29,24, 31,43,"FREE",41,32, 49,52,53,57,55, 64,69,62,70,67],
  26: [13,5,3,8,6, 24,16,30,25,28, 40,39,"FREE",38,32, 47,54,49,46,57, 67,74,73,62,72],
  27: [4,3,7,9,6, 19,26,27,18,22, 33,32,"FREE",36,38, 50,60,51,53,58, 66,72,73,63,64],
  28: [15,13,4,10,6, 21,17,27,19,23, 37,31,"FREE",38,44, 53,52,60,59,48, 67,66,73,74,75],
  29: [15,5,3,4,12, 19,29,22,21,17, 42,32,"FREE",34,43, 53,55,52,49,48, 63,61,65,64,75],
  30: [3,13,15,11,9, 28,20,26,23,18, 43,33,"FREE",39,44, 60,57,58,46,59, 70,72,69,71,61],
  31: [8,15,1,12,13, 28,24,27,22,17, 45,33,"FREE",41,44, 55,60,49,56,59, 71,72,68,75,62],
  32: [8,2,4,15,9, 24,23,18,29,19, 34,39,"FREE",45,37, 59,58,51,48,52, 66,72,75,63,74],
  33: [12,11,15,10,3, 24,26,28,21,23, 43,40,"FREE",33,41, 47,56,59,58,55, 70,61,65,71,63],
  34: [4,15,5,10,2, 16,17,30,21,18, 45,37,"FREE",42,32, 48,58,59,51,49, 62,65,71,69,66],
  35: [12,6,3,4,15, 24,27,19,18,21, 41,33,"FREE",43,31, 48,60,47,54,52, 64,70,61,69,67],
  36: [5,12,6,2,14, 24,16,26,27,18, 38,31,"FREE",39,33, 59,60,54,52,51, 62,73,72,74,66],
  37: [11,10,14,3,8, 18,23,19,24,20, 44,41,"FREE",34,36, 53,50,59,55,48, 64,69,74,66,75],
  38: [12,14,8,11,3, 27,18,16,20,23, 44,31,"FREE",40,37, 59,49,53,57,48, 70,68,65,74,62],
  39: [7,5,3,2,4, 20,21,24,27,30, 33,36,"FREE",32,34, 51,48,54,55,50, 69,72,66,70,62],
  40: [2,7,13,3,1, 22,21,16,27,18, 42,45,"FREE",36,37, 49,54,50,59,53, 69,66,61,72,64],
  41: [4,6,15,3,9, 23,30,21,22,25, 35,44,"FREE",43,40, 58,59,60,54,56, 73,61,75,71,74],
  42: [13,3,12,2,14, 28,18,22,20,29, 39,38,"FREE",33,37, 46,56,59,50,54, 75,74,69,65,66],
  43: [4,9,7,15,6, 25,26,19,21,29, 37,41,"FREE",31,36, 47,51,55,57,54, 69,64,74,61,67],
  44: [7,9,3,10,2, 20,22,30,25,28, 41,37,"FREE",40,33, 58,48,53,56,46, 62,67,68,71,66],
  45: [1,10,2,11,7, 29,23,16,18,25, 40,41,"FREE",39,45, 50,54,49,53,60, 70,75,73,72,69],
  46: [11,9,3,15,5, 24,18,25,23,16, 39,34,"FREE",38,33, 58,48,50,54,49, 75,70,61,67,68],
  47: [11,4,13,14,5, 25,18,27,30,21, 40,37,"FREE",35,42, 60,49,55,53,46, 70,61,74,73,71],
  48: [13,12,7,14,10, 18,27,23,26,24, 38,36,"FREE",34,44, 49,55,57,46,51, 61,71,73,75,68],
  49: [8,11,6,7,9, 20,24,29,18,28, 36,44,"FREE",33,39, 48,49,57,51,59, 63,72,68,66,73],
  50: [1,2,6,11,4, 18,28,20,23,19, 31,43,"FREE",44,40, 55,48,54,57,47, 75,73,61,64,66],
  51: [4,6,5,2,14, 17,20,21,18,28, 42,40,"FREE",34,38, 46,56,51,50,55, 74,69,62,65,64],
  52: [5,9,6,7,10, 18,28,17,26,19, 32,42,"FREE",37,34, 54,47,56,53,48, 68,71,70,63,67],
  53: [13,12,15,11,5, 16,26,22,24,18, 40,34,"FREE",43,31, 53,46,60,51,54, 68,75,71,62,72],
  54: [6,1,7,5,14, 27,16,30,17,28, 45,38,"FREE",34,37, 48,52,47,46,50, 64,65,67,73,71],
  55: [2,1,3,8,13, 16,19,24,26,28, 39,31,"FREE",41,38, 49,51,60,48,53, 72,71,73,62,70],
  56: [3,15,8,2,11, 23,16,20,27,28, 33,41,"FREE",37,43, 58,54,50,59,48, 67,72,68,71,73],
  57: [12,9,5,7,15, 19,24,23,21,30, 32,35,"FREE",41,31, 48,49,46,60,54, 69,71,75,72,62],
  58: [2,14,4,10,9, 30,20,28,18,22, 36,43,"FREE",38,40, 51,46,47,50,54, 62,66,67,61,63],
  59: [5,15,1,12,4, 28,25,18,29,27, 34,32,"FREE",36,35, 51,52,46,56,57, 67,73,69,71,63],
  60: [1,10,14,7,6, 28,27,17,24,21, 41,44,"FREE",31,37, 49,60,50,48,54, 75,72,65,66,64],
  61: [5,4,9,6,1, 25,21,20,30,16, 36,44,"FREE",37,40, 46,59,55,51,53, 64,72,68,70,74],
  62: [9,7,12,3,14, 16,28,20,27,29, 35,37,"FREE",43,39, 48,49,60,56,46, 71,64,73,65,63],
  63: [4,9,2,7,6, 23,18,19,28,16, 41,45,"FREE",35,40, 56,50,46,54,51, 64,72,70,65,61],
  64: [3,13,5,11,2, 25,23,21,20,28, 41,44,"FREE",42,37, 59,47,51,53,54, 71,67,65,66,75],
  65: [4,5,14,1,8, 23,17,21,25,29, 35,39,"FREE",41,42, 51,49,46,55,60, 72,67,65,75,69],
  66: [4,8,12,14,3, 21,29,24,23,17, 36,40,"FREE",37,32, 51,50,47,59,57, 65,67,66,61,75],
  67: [13,15,11,5,12, 21,26,22,24,30, 37,34,"FREE",45,41, 47,48,54,50,58, 74,61,62,75,66],
  68: [14,4,10,9,1, 30,20,18,21,23, 45,36,"FREE",31,33, 53,58,47,46,48, 70,69,67,65,73],
  69: [2,10,11,12,13, 26,30,29,20,17, 38,41,"FREE",36,40, 55,60,52,59,47, 62,66,71,75,65],
  70: [5,1,10,13,14, 28,20,27,25,19, 38,39,"FREE",45,34, 49,50,51,55,46, 68,66,65,72,70],
  71: [15,13,2,7,14, 23,25,22,26,21, 39,33,"FREE",44,32, 58,47,55,59,56, 61,62,71,75,73],
  72: [11,2,9,8,1, 24,21,17,29,19, 42,32,"FREE",34,35, 56,52,48,58,47, 61,65,62,68,63],
  73: [12,8,9,15,4, 27,16,21,22,23, 44,39,"FREE",43,41, 56,57,46,51,60, 63,75,61,68,64],
  74: [4,10,11,12,3, 25,27,16,23,18, 44,45,"FREE",41,31, 46,57,59,55,54, 72,73,66,75,69],
  75: [1,2,6,8,11, 23,17,19,16,20, 34,33,"FREE",35,41, 55,51,50,47,48, 66,67,61,72,64],
  76: [15,9,6,4,8, 21,20,16,29,18, 32,43,"FREE",33,31, 48,56,59,58,51, 65,63,61,71,72],
  77: [14,6,3,11,9, 23,29,22,19,30, 32,41,"FREE",40,38, 49,48,60,57,59, 69,64,63,72,75],
  78: [10,7,12,5,11, 30,16,23,26,18, 33,36,"FREE",32,44, 47,59,50,55,54, 71,68,72,70,73],
  79: [15,2,6,13,11, 23,24,17,28,21, 32,38,"FREE",34,42, 54,53,47,59,60, 72,67,73,74,63],
  80: [3,11,1,4,7, 30,27,17,25,26, 41,34,"FREE",37,42, 46,56,51,52,48, 67,69,63,73,61],
  81: [9,5,15,4,12, 27,30,28,26,29, 40,31,"FREE",42,38, 50,49,47,57,60, 65,61,64,68,74],
  82: [10,6,8,15,3, 29,23,27,30,25, 41,45,"FREE",39,40, 60,54,48,57,56, 63,72,74,66,65],
  83: [10,14,5,8,7, 25,29,27,26,20, 36,42,"FREE",40,34, 56,57,49,46,55, 63,65,75,70,68],
  84: [13,15,5,4,3, 24,27,19,25,21, 43,44,"FREE",31,32, 58,51,48,54,57, 70,67,61,75,64],
  85: [4,10,2,8,5, 24,20,16,18,27, 34,35,"FREE",43,44, 48,46,50,57,49, 75,63,65,73,72],
  86: [13,3,8,15,2, 21,18,28,29,24, 35,44,"FREE",41,43, 60,55,59,49,58, 61,66,72,73,69],
  87: [12,6,1,8,11, 16,30,26,21,24, 44,34,"FREE",43,33, 52,57,53,46,47, 74,66,65,68,64],
  88: [6,14,15,12,9, 23,28,30,22,21, 42,32,"FREE",33,41, 48,50,53,54,47, 67,72,66,65,70],
  89: [10,11,5,14,3, 30,16,18,28,29, 37,31,"FREE",35,33, 54,53,57,46,52, 74,69,61,71,67],
  90: [15,4,6,1,12, 26,29,30,25,21, 37,35,"FREE",39,41, 57,47,53,50,59, 74,64,75,61,63],
  91: [11,6,3,10,14, 30,25,24,23,22, 32,33,"FREE",44,42, 52,60,54,51,46, 74,66,65,62,75],
  92: [15,7,3,4,9, 18,17,22,28,26, 38,40,"FREE",33,36, 56,51,49,55,52, 69,61,63,62,74],
  93: [12,10,14,11,6, 18,24,25,20,16, 38,39,"FREE",35,42, 54,48,51,52,57, 69,68,61,73,65],
  94: [3,12,9,8,13, 21,28,17,25,27, 31,42,"FREE",34,40, 49,51,58,57,53, 72,61,67,63,64],
  95: [12,5,11,2,1, 29,17,20,19,18, 31,39,"FREE",36,35, 57,50,54,56,52, 71,72,62,73,75],
  96: [14,3,12,11,8, 25,21,20,22,17, 43,34,"FREE",32,39, 50,54,49,57,60, 69,66,61,68,74],
  97: [10,13,15,4,9, 29,17,22,21,24, 36,44,"FREE",43,34, 55,57,58,47,54, 63,71,67,69,68],
  98: [6,3,13,14,15, 22,21,29,30,23, 37,41,"FREE",45,36, 51,54,59,57,53, 67,68,64,61,71],
  99: [5,1,9,11,13, 28,22,23,27,25, 31,42,"FREE",41,44, 50,57,48,56,60, 71,74,62,72,63],
  100: [11,8,15,9,14, 29,30,25,17,24, 38,34,"FREE",42,43, 54,60,57,48,59, 67,75,72,71,64],
  101: [13,10,6,12,8, 23,29,20,19,17, 35,43,"FREE",45,36, 52,56,50,55,47, 65,70,69,64,73],
  102: [9,12,15,10,6, 19,21,30,16,27, 40,41,"FREE",37,38, 51,55,60,53,47, 66,74,62,68,72],
  103: [5,1,7,11,14, 19,27,26,25,17, 34,37,"FREE",33,32, 46,54,47,52,50, 71,64,74,67,72],
  104: [9,14,13,12,15, 17,22,23,19,20, 33,43,"FREE",44,36, 57,58,52,55,54, 61,65,74,71,70],
  105: [12,15,13,1,2, 24,16,29,21,18, 34,36,"FREE",37,35, 58,48,47,46,60, 71,75,63,68,61],
  106: [8,5,3,10,12, 21,26,29,25,24, 37,32,"FREE",39,36, 48,52,59,58,55, 74,73,72,69,70],
  107: [13,3,9,14,6, 17,22,26,21,30, 42,36,"FREE",39,43, 57,49,55,60,51, 70,69,63,75,67],
  108: [2,6,8,1,13, 21,29,25,19,27, 36,40,"FREE",34,39, 53,59,55,50,60, 70,64,68,72,75],
  109: [12,5,8,4,15, 28,16,29,19,30, 36,45,"FREE",31,42, 54,56,59,46,60, 75,62,70,61,72],
  110: [1,3,9,5,12, 21,19,23,27,22, 34,38,"FREE",31,41, 48,49,52,60,47, 61,70,74,64,72],
  111: [9,1,14,2,12, 26,19,29,17,20, 38,40,"FREE",41,34, 51,57,56,48,54, 65,68,64,66,69],
  112: [1,11,6,13,8, 20,23,24,30,17, 34,37,"FREE",43,44, 55,46,48,54,60, 73,70,72,63,62],
  113: [15,6,5,11,7, 30,16,20,22,26, 33,42,"FREE",32,38, 49,55,57,54,47, 64,68,66,65,74],
  114: [4,6,5,14,3, 17,16,28,27,22, 33,31,"FREE",35,36, 47,54,56,49,57, 70,64,62,63,68],
  115: [15,6,10,2,7, 22,17,29,25,19, 33,37,"FREE",31,43, 50,46,59,53,58, 68,70,72,64,71],
  116: [3,2,13,15,12, 19,28,20,25,30, 39,37,"FREE",35,34, 60,46,51,52,55, 70,61,63,75,69],
  117: [4,11,12,5,1, 28,21,16,18,30, 44,39,"FREE",31,40, 51,47,60,53,52, 69,65,61,70,67],
  118: [14,5,4,10,12, 29,20,30,21,26, 34,39,"FREE",32,33, 54,47,50,56,55, 70,66,68,74,62],
  119: [2,5,11,10,14, 24,22,23,17,20, 38,40,"FREE",45,31, 53,56,47,60,50, 66,73,67,68,64],
  120: [8,12,3,5,10, 21,20,19,24,16, 33,35,"FREE",32,40, 49,54,58,56,57, 70,63,64,71,66],
  121: [6,5,15,14,12, 21,19,30,17,25, 40,32,"FREE",36,34, 52,60,56,46,55, 65,63,70,68,72],
  122: [11,13,8,9,6, 29,19,24,22,25, 45,38,"FREE",39,44, 54,57,49,48,46, 63,75,71,69,68],
  123: [3,6,13,14,10, 18,17,16,25,19, 45,44,"FREE",39,38, 59,49,52,48,56, 64,70,67,62,75],
  124: [12,13,10,4,6, 25,22,30,18,26, 39,32,"FREE",33,42, 58,50,52,54,46, 73,64,72,63,61],
  125: [5,1,7,3,15, 20,23,16,19,17, 43,37,"FREE",36,44, 49,52,53,59,55, 62,72,64,67,74],
  126: [6,12,15,3,1, 17,20,23,27,18, 33,37,"FREE",43,42, 55,57,52,59,51, 61,75,63,62,64],
  127: [4,15,1,7,13, 23,16,25,27,28, 39,40,"FREE",31,44, 47,53,49,57,54, 63,61,66,72,73],
  128: [13,1,5,8,3, 18,27,26,24,20, 42,38,"FREE",41,32, 56,60,59,46,55, 67,69,72,74,70],
  129: [13,6,12,4,15, 21,16,29,28,30, 37,33,"FREE",40,32, 55,57,59,60,56, 67,65,73,75,62],
  130: [10,8,2,3,12, 29,25,27,17,21, 40,35,"FREE",34,39, 51,49,46,60,54, 75,65,71,66,73],
  131: [14,8,3,9,6, 27,20,30,26,22, 33,42,"FREE",45,32, 59,46,57,51,52, 75,68,73,62,74],
  132: [3,4,15,6,11, 18,22,26,28,23, 36,34,"FREE",43,32, 49,55,46,53,56, 66,68,61,62,75],
  133: [12,7,6,3,2, 22,24,16,28,26, 44,32,"FREE",37,41, 57,60,47,54,52, 61,74,72,63,64],
  134: [5,13,8,10,11, 20,17,24,28,16, 35,36,"FREE",44,43, 46,54,56,53,48, 75,68,67,65,70],
  135: [1,9,7,5,2, 29,16,28,25,23, 40,42,"FREE",33,45, 60,52,54,58,57, 62,69,66,65,70],
  136: [7,15,10,6,12, 19,30,22,21,26, 43,31,"FREE",32,42, 53,46,59,55,49, 61,63,64,70,73],
  137: [12,4,14,1,10, 20,30,26,24,21, 33,39,"FREE",38,43, 56,54,52,46,48, 61,74,66,73,64],
  138: [4,6,13,2,9, 26,30,24,29,18, 34,36,"FREE",33,37, 57,52,56,50,53, 65,74,63,75,68],
  139: [10,11,8,14,15, 21,19,20,25,18, 42,41,"FREE",34,36, 53,54,52,49,55, 74,62,64,69,63],
  140: [12,3,1,5,4, 19,30,17,18,16, 34,35,"FREE",31,45, 51,57,50,47,55, 71,73,70,67,61],
  141: [2,10,5,6,7, 28,20,25,27,16, 42,32,"FREE",33,45, 48,58,59,52,56, 63,74,73,67,69],
  142: [1,15,14,8,9, 26,25,20,22,19, 42,36,"FREE",32,43, 57,49,48,58,54, 65,64,68,75,70],
  143: [7,8,2,6,4, 22,25,26,28,18, 34,38,"FREE",31,32, 51,52,60,56,57, 71,66,73,68,74],
  144: [1,4,9,3,11, 22,27,26,28,23, 32,41,"FREE",44,37, 57,53,56,55,60, 68,73,71,61,66],
  145: [8,1,10,6,9, 24,21,27,29,25, 45,40,"FREE",34,44, 57,51,52,60,46, 67,65,75,68,62],
  146: [6,1,14,5,9, 19,26,17,20,27, 41,43,"FREE",32,33, 50,52,55,54,47, 70,62,74,61,72],
  147: [12,15,13,14,8, 29,28,19,18,16, 31,44,"FREE",36,38, 50,49,60,54,52, 71,74,67,75,64],
  148: [2,13,5,4,9, 17,26,20,18,21, 37,40,"FREE",38,34, 55,49,46,54,59, 71,68,63,61,64],
  149: [4,13,3,11,1, 27,18,20,30,23, 42,38,"FREE",34,33, 58,60,57,56,47, 64,66,73,69,75],
  150: [13,1,8,4,15, 22,24,19,18,30, 32,39,"FREE",36,38, 53,50,52,58,56, 73,68,70,75,71],
  151: [11,7,12,1,6, 30,23,21,17,26, 45,42,"FREE",37,38, 60,48,54,46,52, 73,62,61,68,75],
  152: [15,5,3,4,7, 25,21,27,22,18, 36,32,"FREE",40,37, 58,59,48,50,52, 72,64,61,66,74],
  153: [7,3,5,6,13, 22,27,24,21,30, 33,34,"FREE",42,43, 51,53,47,58,49, 67,62,71,61,73],
  154: [10,9,15,14,13, 22,27,28,18,25, 36,39,"FREE",43,45, 51,57,54,55,47, 65,63,75,64,68],
  155: [10,1,15,4,12, 17,19,21,30,23, 37,32,"FREE",38,34, 60,58,50,55,49, 62,72,69,61,68],
  156: [10,13,4,2,5, 27,30,18,26,23, 35,36,"FREE",37,38, 58,57,56,60,50, 62,69,70,63,65],
  157: [1,15,3,13,2, 27,16,19,24,23, 44,38,"FREE",34,35, 59,49,58,46,51, 66,72,69,74,62],
  158: [5,11,15,12,4, 21,29,24,27,18, 38,43,"FREE",36,34, 59,60,49,56,52, 69,67,72,63,74],
  159: [8,14,1,5,12, 22,28,30,20,25, 32,41,"FREE",37,43, 55,57,56,60,47, 62,74,63,61,70],
  160: [10,11,6,12,15, 20,26,18,27,28, 43,39,"FREE",38,44, 59,46,50,56,57, 63,72,64,66,61],
  161: [1,3,5,10,2, 20,25,24,30,16, 36,33,"FREE",45,37, 50,60,52,53,47, 74,71,67,63,62],
  162: [1,15,3,4,12, 21,17,30,19,20, 35,40,"FREE",36,37, 57,55,53,58,56, 62,72,69,66,68],
  163: [11,2,13,12,8, 27,23,17,29,26, 42,34,"FREE",36,39, 57,53,55,56,46, 66,63,68,64,69],
  164: [1,5,2,15,10, 27,26,18,24,23, 39,35,"FREE",41,33, 54,51,47,55,52, 64,62,68,70,75],
  165: [7,4,8,6,1, 26,17,30,23,24, 37,44,"FREE",45,41, 55,52,60,47,56, 70,61,67,64,69],
  166: [11,5,7,12,14, 24,23,27,16,28, 38,33,"FREE",39,37, 59,58,51,53,56, 65,75,67,63,61],
  167: [5,13,6,8,10, 26,18,20,23,30, 37,35,"FREE",40,44, 47,59,55,57,51, 68,71,66,74,70],
  168: [1,14,3,2,13, 24,27,17,26,21, 33,35,"FREE",44,36, 48,57,53,54,52, 61,73,68,71,75],
  169: [10,12,3,8,15, 27,20,25,22,29, 37,36,"FREE",32,42, 60,55,53,51,46, 62,66,73,67,70],
  170: [1,3,8,14,6, 18,20,24,30,27, 33,38,"FREE",44,45, 50,60,58,54,52, 71,72,62,66,70],
  171: [13,14,1,10,9, 29,21,18,19,23, 45,36,"FREE",37,33, 53,58,46,48,52, 67,74,64,65,63],
  172: [13,9,7,8,5, 28,24,16,18,23, 40,38,"FREE",41,36, 58,50,52,59,46, 71,75,61,65,74],
  173: [8,12,11,6,10, 17,18,28,16,30, 31,43,"FREE",40,34, 55,49,48,60,54, 72,67,61,73,71],
  174: [9,10,4,13,12, 23,16,30,19,22, 35,40,"FREE",31,33, 50,57,47,51,49, 61,66,72,69,65],
  175: [4,10,6,7,15, 29,23,16,18,22, 44,43,"FREE",40,35, 57,60,54,51,55, 63,71,69,72,68],
  176: [14,6,2,3,12, 25,28,19,27,30, 37,40,"FREE",34,41, 51,47,49,60,54, 66,73,69,75,62],
  177: [7,5,9,1,2, 17,19,28,25,16, 39,38,"FREE",31,32, 50,55,48,52,60, 75,66,70,61,62],
  178: [2,6,5,4,1, 18,26,16,23,17, 35,32,"FREE",44,39, 50,46,60,51,55, 67,68,71,64,63],
  179: [9,15,5,2,12, 23,16,22,28,24, 34,35,"FREE",39,37, 46,57,55,51,47, 61,62,74,66,72],
  180: [13,4,12,2,1, 17,30,26,18,24, 40,32,"FREE",44,36, 52,54,46,56,59, 63,72,71,65,75],
  181: [8,9,10,14,2, 28,17,29,25,22, 32,34,"FREE",43,44, 56,59,47,58,52, 66,68,62,73,65],
  182: [13,6,10,9,8, 29,27,16,26,17, 44,34,"FREE",39,41, 48,49,60,55,53, 74,63,69,71,67],
  183: [11,3,6,14,12, 18,28,25,19,16, 44,34,"FREE",42,45, 51,58,55,52,50, 75,67,66,62,74],
  184: [14,3,13,12,9, 27,21,18,20,19, 38,31,"FREE",43,42, 59,53,50,55,54, 66,72,70,68,63],
  185: [11,15,10,6,7, 23,28,25,21,18, 42,44,"FREE",31,37, 53,51,59,46,47, 65,75,73,67,72],
  186: [15,2,3,10,11, 18,27,23,20,26, 42,36,"FREE",41,45, 56,51,48,54,55, 64,65,74,70,73],
  187: [7,6,4,12,5, 16,25,26,24,19, 42,45,"FREE",43,34, 56,48,59,46,60, 62,71,72,63,73],
  188: [14,5,9,7,13, 22,29,27,17,26, 35,41,"FREE",42,39, 58,49,50,56,48, 73,68,72,61,74],
  189: [8,3,1,10,2, 22,26,24,29,19, 34,45,"FREE",40,38, 58,48,56,52,54, 73,61,69,66,71],
  190: [2,1,15,3,7, 20,28,25,29,19, 33,36,"FREE",35,41, 47,53,57,58,60, 69,71,68,63,74],
  191: [14,13,6,12,2, 24,21,20,25,22, 38,34,"FREE",33,32, 58,52,59,48,56, 65,74,62,64,61],
  192: [3,11,7,15,4, 29,17,27,16,18, 34,32,"FREE",45,43, 50,60,49,57,51, 74,61,62,75,69],
  193: [2,10,7,1,5, 28,17,21,16,19, 32,31,"FREE",38,35, 49,53,48,46,54, 65,69,61,70,64],
  194: [15,5,4,13,11, 30,22,25,17,18, 44,33,"FREE",38,45, 56,54,57,49,55, 68,64,66,63,65],
  195: [7,15,8,9,4, 24,22,18,29,25, 38,40,"FREE",31,41, 53,59,57,60,48, 65,73,61,69,68],
  196: [4,8,10,13,1, 17,24,16,29,22, 37,40,"FREE",31,44, 55,49,58,48,47, 68,74,63,67,70],
  197: [14,1,10,4,11, 30,25,27,26,28, 33,45,"FREE",43,34, 48,49,54,58,47, 74,65,73,62,69],
  198: [10,13,1,12,9, 28,24,18,21,25, 43,31,"FREE",36,37, 60,52,53,55,57, 66,71,75,74,72],
  199: [7,10,8,6,9, 17,24,23,30,16, 33,44,"FREE",42,39, 60,56,59,57,49, 71,74,67,68,63],
  200: [10,1,2,8,7, 18,19,23,24,30, 32,37,"FREE",40,39, 53,49,50,59,55, 70,75,64,72,68]
}

# ========== DATABASE CONNECTION ==========
def get_connection():
    return sqlite3.connect(DB_PATH)

# ========== INITIALISATION ==========
def init_db():
    conn = get_connection()
    c = conn.cursor()

    # ----- Users -----
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        balance INTEGER DEFAULT 0,
        total_deposited INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # ----- Game rounds -----
    c.execute('''CREATE TABLE IF NOT EXISTS game_rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ended_at TIMESTAMP,
        status TEXT DEFAULT 'active',
        prize_pool INTEGER DEFAULT 0,
        duration_seconds INTEGER DEFAULT 300,
        is_paused INTEGER DEFAULT 0
    )''')

    # ----- Game settings (single row) -----
    c.execute('''CREATE TABLE IF NOT EXISTS game_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        card_price INTEGER DEFAULT 20,
        house_percent INTEGER DEFAULT 10,
        withdrawal_fee_percent INTEGER DEFAULT 5
    )''')

    # ----- Cardboards (fixed 200 cards) -----
    c.execute('''CREATE TABLE IF NOT EXISTS cardboards (
        id INTEGER PRIMARY KEY,
        numbers TEXT NOT NULL
    )''')

    # ----- Active cards for the current round -----
    c.execute('''CREATE TABLE IF NOT EXISTS user_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        cardboard_id INTEGER UNIQUE,
        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (cardboard_id) REFERENCES cardboards(id)
    )''')

    # ----- Permanent purchase history (per round) -----
    c.execute('''CREATE TABLE IF NOT EXISTS card_purchase_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_id INTEGER,
        user_id INTEGER,
        cardboard_id INTEGER,
        purchased_at TIMESTAMP,
        FOREIGN KEY (round_id) REFERENCES game_rounds(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ----- Called numbers per round -----
    c.execute('''CREATE TABLE IF NOT EXISTS called_numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_id INTEGER,
        number INTEGER,
        called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (round_id) REFERENCES game_rounds(id),
        UNIQUE(round_id, number)
    )''')

    # ----- Payments (deposits) -----
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id TEXT UNIQUE,
        user_id INTEGER,
        amount INTEGER,
        status TEXT DEFAULT 'pending',
        screenshot TEXT,
        approved_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ----- Withdrawals -----
    c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        fee INTEGER,
        final_amount INTEGER,
        payout_method TEXT,
        payout_account TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ----- House earnings (track profit) -----
    c.execute('''CREATE TABLE IF NOT EXISTS house_earnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        amount INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_user_cards_user_id ON user_cards(user_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_withdrawals_user_id ON withdrawals(user_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_called_numbers_round ON called_numbers(round_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_history_round ON card_purchase_history(round_id)')

    conn.commit()

    # Load fixed cards if empty
    c.execute("SELECT COUNT(*) FROM cardboards")
    if c.fetchone()[0] == 0:
        for cid, nums in ALL_CARDS.items():
            c.execute("INSERT INTO cardboards (id, numbers) VALUES (?, ?)", (cid, json.dumps(nums)))
        conn.commit()
        print("✅ 200 cards loaded into database.")

    # Insert default game settings if missing
    c.execute("SELECT COUNT(*) FROM game_settings")
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO game_settings (id, card_price, house_percent, withdrawal_fee_percent)
                     VALUES (1, ?, ?, ?)''',
                  (DEFAULT_CARD_PRICE, DEFAULT_HOUSE_PERCENT, DEFAULT_WITHDRAWAL_FEE_PERCENT))
        conn.commit()
        print("✅ Default game settings loaded.")

    # Start an initial round if no active round exists
    c.execute("SELECT id FROM game_rounds WHERE status = 'active'")
    if not c.fetchone():
        c.execute('''INSERT INTO game_rounds (status, duration_seconds)
                     VALUES ('active', ?)''', (DEFAULT_ROUND_DURATION,))
        conn.commit()
        print("✅ Initial game round started.")

    conn.close()

# ========== USER FUNCTIONS ==========
def get_user_by_telegram_id(telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    return row

def create_user(telegram_id, username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (telegram_id, username, balance) VALUES (?, ?, 0)",
              (telegram_id, username))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id

def get_user_id(telegram_id):
    user = get_user_by_telegram_id(telegram_id)
    return user[0] if user else None

def get_user_balance(telegram_id):
    user = get_user_by_telegram_id(telegram_id)
    return user[3] if user else 0

def update_user_balance(telegram_id, new_balance):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = ? WHERE telegram_id = ?", (new_balance, telegram_id))
    conn.commit()
    conn.close()

# ========== CARD FUNCTIONS ==========
def get_cardboard(card_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT numbers FROM cardboards WHERE id = ?", (card_id,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def get_cardboard_as_grid(card_id):
    nums = get_cardboard(card_id)
    if not nums:
        return None
    grid = []
    for row in range(5):
        row_start = row * 5
        grid.append(nums[row_start:row_start + 5])
    return grid

def get_user_cards(telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT cardboard_id FROM user_cards
                 WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)
                 ORDER BY purchased_at''', (telegram_id,))
    cards = [row[0] for row in c.fetchall()]
    conn.close()
    return cards

def get_all_cards_with_status():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT 
            cardboards.id,
            cardboards.numbers,
            user_cards.user_id IS NOT NULL as taken
        FROM cardboards
        LEFT JOIN user_cards ON cardboards.id = user_cards.cardboard_id
        ORDER BY cardboards.id
    ''')
    rows = c.fetchall()
    conn.close()
    return [{"id": row[0], "numbers": json.loads(row[1]), "taken": bool(row[2])} for row in rows]

# ========== GAME ROUND FUNCTIONS ==========
def start_new_round():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT duration_seconds FROM game_rounds ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    duration = row[0] if row else DEFAULT_ROUND_DURATION
    c.execute("INSERT INTO game_rounds (status, duration_seconds) VALUES ('active', ?)", (duration,))
    conn.commit()
    round_id = c.lastrowid
    conn.close()
    return round_id

def get_active_round():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM game_rounds WHERE status = 'active' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_round_prize_pool(round_id=None):
    if round_id is None:
        round_id = get_active_round()
        if not round_id:
            return 0
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT prize_pool FROM game_rounds WHERE id = ?", (round_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def is_round_expired(round_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT started_at, duration_seconds FROM game_rounds WHERE id = ?", (round_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return True
    started_at, duration = row
    started = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S')
    now = datetime.utcnow()
    elapsed = (now - started).total_seconds()
    return elapsed >= duration

def pause_round(round_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE game_rounds SET is_paused = 1 WHERE id = ?", (round_id,))
    conn.commit()
    conn.close()

def resume_round(round_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE game_rounds SET is_paused = 0 WHERE id = ?", (round_id,))
    conn.commit()
    conn.close()

# ========== CARD PURCHASE ==========
def buy_card(telegram_id, cardboard_id):
    conn = get_connection()
    c = conn.cursor()

    user_id = get_user_id(telegram_id)
    if not user_id:
        conn.close()
        return False, "User not found. Please register first."

    round_id = get_active_round()
    if not round_id:
        conn.close()
        return False, "No active game round. Please wait for admin to start one."

    c.execute("SELECT card_price FROM game_settings WHERE id = 1")
    row = c.fetchone()
    price = row[0] if row else DEFAULT_CARD_PRICE

    c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    balance = c.fetchone()[0]
    if balance < price:
        conn.close()
        return False, f"❌ Insufficient balance. Need {price}, you have {balance}."

    c.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (user_id,))
    if c.fetchone()[0] >= MAX_CARDS_PER_USER:
        conn.close()
        return False, f"❌ Maximum {MAX_CARDS_PER_USER} cards allowed per round."

    try:
        c.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (price, user_id))
        c.execute("UPDATE game_rounds SET prize_pool = prize_pool + ? WHERE id = ?", (price, round_id))
        c.execute("INSERT INTO user_cards (user_id, cardboard_id) VALUES (?, ?)", (user_id, cardboard_id))
        c.execute('''
            INSERT INTO card_purchase_history (round_id, user_id, cardboard_id, purchased_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (round_id, user_id, cardboard_id))
        conn.commit()
        conn.close()
        return True, f"✅ Card purchased! New balance: {balance - price}"
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return False, "❌ This card is already taken by another user."

# ========== CALLED NUMBERS ==========
def call_number(round_id=None):
    if round_id is None:
        round_id = get_active_round()
        if not round_id:
            return None

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT is_paused, status FROM game_rounds WHERE id = ?", (round_id,))
    row = c.fetchone()
    if not row or row[1] != 'active' or row[0] == 1:
        conn.close()
        return None

    c.execute("SELECT number FROM called_numbers WHERE round_id = ?", (round_id,))
    used = {row[0] for row in c.fetchall()}

    available = [n for n in range(1, 76) if n not in used]
    if not available:
        conn.close()
        return None

    number = random.choice(available)
    c.execute("INSERT INTO called_numbers (round_id, number) VALUES (?, ?)", (round_id, number))
    conn.commit()
    conn.close()
    return number

def get_called_numbers(round_id=None):
    if round_id is None:
        round_id = get_active_round()
        if not round_id:
            return []
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT number FROM called_numbers WHERE round_id = ? ORDER BY called_at", (round_id,))
    nums = [row[0] for row in c.fetchall()]
    conn.close()
    return nums

# ========== WINNER DETECTION ==========
def check_card_winner(card, called_numbers):
    called = set(called_numbers)
    for row in card:
        if all(cell == "FREE" or cell in called for cell in row):
            return True
    for col in range(5):
        if all(card[row][col] == "FREE" or card[row][col] in called for row in range(5)):
            return True
    return False

def find_winners(round_id=None):
    if round_id is None:
        round_id = get_active_round()
        if not round_id:
            return []

    conn = get_connection()
    c = conn.cursor()

    called = get_called_numbers(round_id)
    if not called:
        conn.close()
        return []

    c.execute('SELECT user_id, cardboard_id FROM user_cards')
    winners = []
    for user_id, cardboard_id in c.fetchall():
        card_data = get_cardboard(cardboard_id)
        if not card_data:
            continue
        card_grid = [card_data[i*5:(i+1)*5] for i in range(5)]
        if check_card_winner(card_grid, called):
            winners.append(user_id)

    conn.close()
    return winners

# ========== PRIZE DISTRIBUTION ==========
def handle_winner(winner_user_id, round_id=None):
    conn = get_connection()
    c = conn.cursor()

    if round_id is None:
        round_id = get_active_round()
        if not round_id:
            conn.close()
            return "No active round."

    c.execute("UPDATE game_rounds SET status = 'processing' WHERE id = ? AND status = 'active'", (round_id,))
    if c.rowcount == 0:
        conn.close()
        return "Round already finished or being processed."

    c.execute("SELECT prize_pool, started_at, duration_seconds FROM game_rounds WHERE id = ?", (round_id,))
    row = c.fetchone()
    if not row:
        conn.rollback()
        conn.close()
        return "Round not found."
    prize_pool, started_at, duration = row

    started = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S')
    if (datetime.utcnow() - started).total_seconds() > duration:
        conn.rollback()
        conn.close()
        return refund_round(round_id)

    if prize_pool <= 0:
        conn.rollback()
        conn.close()
        return "Prize pool empty."

    c.execute("SELECT house_percent FROM game_settings WHERE id = 1")
    house_percent = c.fetchone()[0]

    house_cut = (prize_pool * house_percent) // 100
    winner_amount = prize_pool - house_cut

    c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (winner_amount, winner_user_id))
    c.execute("INSERT INTO house_earnings (source, amount) VALUES ('bingo_round', ?)", (house_cut,))
    c.execute('''UPDATE game_rounds SET status = 'finished', ended_at = CURRENT_TIMESTAMP
                 WHERE id = ?''', (round_id,))

    conn.commit()
    conn.close()

    new_round_id = start_new_round()
    return f"🏆 Winner paid {winner_amount} ETB. House earned {house_cut} ETB. New round {new_round_id} started."

def refund_round(round_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        SELECT user_id, SUM(price) FROM (
            SELECT uc.user_id, gs.card_price as price
            FROM user_cards uc
            JOIN game_settings gs ON 1=1
            WHERE uc.cardboard_id IN (
                SELECT cardboard_id FROM card_purchase_history WHERE round_id = ?
            )
        ) GROUP BY user_id
    ''', (round_id,))
    refunds = c.fetchall()

    if not refunds:
        c.execute("UPDATE game_rounds SET status = 'finished', ended_at = CURRENT_TIMESTAMP WHERE id = ?", (round_id,))
        conn.commit()
        conn.close()
        start_new_round()
        return "Round closed (no players)."

    for user_id, total_paid in refunds:
        c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (total_paid, user_id))

    c.execute('''UPDATE game_rounds SET status = 'refunded', ended_at = CURRENT_TIMESTAMP
                 WHERE id = ?''', (round_id,))

    conn.commit()
    conn.close()

    new_round_id = start_new_round()
    return f"All players refunded. New round {new_round_id} started."

def check_round_timeout():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM game_rounds WHERE status = 'active' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if not row:
        conn.close()
        return

    round_id = row[0]
    if is_round_expired(round_id):
        c.execute("SELECT status FROM game_rounds WHERE id = ?", (round_id,))
        status = c.fetchone()[0]
        if status == 'active':
            conn.close()
            return refund_round(round_id)
    conn.close()

# ========== DEPOSITS (Payments) ==========
def request_deposit(telegram_id, amount, transaction_ref):
    conn = get_connection()
    c = conn.cursor()

    user_id = get_user_id(telegram_id)
    if not user_id:
        conn.close()
        return "User not found."

    c.execute("""
        INSERT INTO payments (payment_id, user_id, amount, status)
        VALUES (?, ?, ?, 'pending')
    """, (transaction_ref, user_id, amount))

    conn.commit()
    conn.close()
    return "✅ Deposit request submitted. Waiting for admin approval."

def approve_deposit(admin_id, payment_id):
    if admin_id != ADMIN_TELEGRAM_ID:
        return "⛔ Not authorized."

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT user_id, amount, status FROM payments WHERE payment_id = ?", (payment_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return "Deposit not found."

    user_id, amount, status = row
    if status != "pending":
        conn.close()
        return "Already processed."

    c.execute("UPDATE payments SET status = 'approved', approved_by = ?, approved_at = CURRENT_TIMESTAMP WHERE payment_id = ?",
              (admin_id, payment_id))
    c.execute("UPDATE users SET balance = balance + ? + ? WHERE id = ?", (amount, DEPOSIT_BONUS, user_id))
    c.execute("UPDATE users SET total_deposited = total_deposited + ? WHERE id = ?", (amount, user_id))

    conn.commit()
    conn.close()
    return "✅ Deposit approved and balance updated."

def reject_deposit(admin_id, payment_id):
    if admin_id != ADMIN_TELEGRAM_ID:
        return "⛔ Not authorized."

    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE payments SET status = 'rejected' WHERE payment_id = ?", (payment_id,))
    conn.commit()
    conn.close()
    return "❌ Deposit rejected."

def get_pending_deposits():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT payments.id, users.username, payments.amount, payments.payment_id
        FROM payments
        JOIN users ON payments.user_id = users.id
        WHERE payments.status = 'pending'
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

# ========== WITHDRAWALS ==========
def request_withdrawal(telegram_id, amount, payout_method, payout_account):
    conn = get_connection()
    c = conn.cursor()

    user_id = get_user_id(telegram_id)
    if not user_id:
        conn.close()
        return "User not found."

    c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    balance = c.fetchone()[0]

    if amount <= 0:
        conn.close()
        return "Invalid amount."

    if balance < amount:
        conn.close()
        return "❌ Insufficient balance."

    c.execute("SELECT withdrawal_fee_percent FROM game_settings WHERE id = 1")
    fee_percent = c.fetchone()[0]

    fee = (amount * fee_percent) // 100
    final_amount = amount - fee

    c.execute('''
        INSERT INTO withdrawals (user_id, amount, fee, final_amount, payout_method, payout_account)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount, fee, final_amount, payout_method, payout_account))

    conn.commit()
    conn.close()
    return f"✅ Withdrawal requested.\nFee: {fee}\nYou will receive: {final_amount}"

def approve_withdrawal(admin_id, withdrawal_id):
    if admin_id != ADMIN_TELEGRAM_ID:
        return "⛔ Not authorized."

    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        SELECT user_id, amount, fee, final_amount, status
        FROM withdrawals
        WHERE id = ?
    ''', (withdrawal_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return "Withdrawal not found."

    user_id, amount, fee, final_amount, status = row
    if status != "pending":
        conn.close()
        return "Already processed."

    c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    balance = c.fetchone()[0]
    if balance < amount:
        conn.close()
        return "User has insufficient balance now."

    c.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
    c.execute("INSERT INTO house_earnings (source, amount) VALUES ('withdrawal_fee', ?)", (fee,))
    c.execute("UPDATE withdrawals SET status = 'approved' WHERE id = ?", (withdrawal_id,))

    conn.commit()
    conn.close()
    return "✅ Withdrawal approved. Pay user manually."

def reject_withdrawal(admin_id, withdrawal_id):
    if admin_id != ADMIN_TELEGRAM_ID:
        return "⛔ Not authorized."

    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE withdrawals SET status = 'rejected' WHERE id = ?", (withdrawal_id,))
    conn.commit()
    conn.close()
    return "❌ Withdrawal rejected."

def get_pending_withdrawals():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT withdrawals.id, users.username, withdrawals.amount,
               withdrawals.fee, withdrawals.final_amount,
               withdrawals.payout_method, withdrawals.payout_account
        FROM withdrawals
        JOIN users ON withdrawals.user_id = users.id
        WHERE withdrawals.status = 'pending'
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

# ========== ADMIN FUNCTIONS ==========
def reset_round(admin_telegram_id):
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        return "⛔ You are not admin."

    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        UPDATE game_rounds
        SET status = 'finished', ended_at = CURRENT_TIMESTAMP
        WHERE status = 'active'
    ''')
    c.execute("DELETE FROM user_cards")
    conn.commit()
    conn.close()

    new_round_id = start_new_round()
    return f"♻ Round reset. New round started (ID: {new_round_id})"

def set_card_price(admin_telegram_id, new_price):
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        return "⛔ You are not admin."
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE game_settings SET card_price = ? WHERE id = 1", (new_price,))
    conn.commit()
    conn.close()
    return f"✅ Card price updated to {new_price}."

def set_house_percent(admin_telegram_id, new_percent):
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        return "⛔ You are not admin."
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE game_settings SET house_percent = ? WHERE id = 1", (new_percent,))
    conn.commit()
    conn.close()
    return f"✅ House percent updated to {new_percent}%."

def set_withdrawal_fee(admin_telegram_id, new_percent):
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        return "⛔ You are not admin."
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE game_settings SET withdrawal_fee_percent = ? WHERE id = 1", (new_percent,))
    conn.commit()
    conn.close()
    return f"✅ Withdrawal fee updated to {new_percent}%."

def set_round_duration(admin_telegram_id, new_duration_seconds):
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        return "⛔ You are not admin."
    conn = get_connection()
    c = conn.cursor()
    round_id = get_active_round()
    if round_id:
        c.execute("UPDATE game_rounds SET duration_seconds = ? WHERE id = ?", (new_duration_seconds, round_id))
    conn.commit()
    conn.close()
    return f"✅ Round duration updated to {new_duration_seconds} seconds."

def admin_stats():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT SUM(total_deposited) FROM users")
    total_deposits = c.fetchone()[0] or 0

    c.execute("SELECT prize_pool FROM game_rounds WHERE status='active'")
    row = c.fetchone()
    current_prize_pool = row[0] if row else 0

    c.execute("SELECT COUNT(*) FROM game_rounds")
    total_rounds = c.fetchone()[0]

    c.execute("SELECT SUM(amount) FROM house_earnings")
    total_house = c.fetchone()[0] or 0

    conn.close()
    return {
        "total_users": total_users,
        "total_deposits": total_deposits,
        "current_prize_pool": current_prize_pool,
        "total_rounds": total_rounds,
        "total_house_earnings": total_house
    }

# ========== INITIALISE ON IMPORT ==========
try:
    init_db()
    print("✅ Database initialized successfully.")
except Exception as e:
    print(f"❌ ERROR initializing database: {e}")
    raise