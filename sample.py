from wuggy.generators.wuggygenerator import WuggyGenerator
import re
import time
from fractions import Fraction
import random
import sys

g = WuggyGenerator()
g.load("orthographic_english")
for sequence in g.generate_simple("dog"):
    print(sequence)
