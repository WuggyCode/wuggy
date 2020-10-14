from pseudowordgenerators.WuggyGenerator import WuggyGenerator
import re
import time
from fractions import Fraction
import random
import sys

g = WuggyGenerator()
g.load("orthographic_english")
words = ["flower"]
ncandidates = 5

for sequence in g.generate_simple("trumpet"):
    print(sequence)
# for word in words:
#     g.set_reference_sequence(g.lookup(word))
#     # g.set_attribute_filter('sequence_length')
#     g.set_attribute_filter('segment_length')
#     g.set_statistic('overlap_ratio')
#     g.set_statistic('plain_length')
#     g.set_statistic('transition_frequencies')
#     g.set_statistic('lexicality')
#     # takes long time
#     g.set_statistic('ned1')
#     g.set_output_mode('syllabic')
#     j = 0
#     for i in range(1, 10, 1):
#         g.set_frequency_filter(2**i, 2**i)
#         for sequence in g.generate(clear_cache=True):
#             match = False
#             if (g.statistics['overlap_ratio'] == Fraction(2, 3) and
#                     g.statistics['lexicality'] == "N"):
#                 match = True
#             if match == True:
#                 print("match")
#                 print(sequence)
#                 j = j+1
#                 if j > ncandidates:
#                     break
#         if j > ncandidates:
#             break

# for word in words:
#     g.set_reference_sequence(g.lookup(word))
#     g.set_attribute_filter('sequence_length')
#     g.set_attribute_filter('segment_length')
#     g.set_statistic('overlap_ratio')
#     g.set_statistic('plain_length')
#     g.set_statistic('transition_frequencies')
#     g.set_statistic('lexicality')
#     g.set_statistic('ned1')
#     g.set_output_mode('syllabic')
#     print(g.list_statistics())
#     j=0
#     for i in range(1,10,1):
#         g.set_frequency_filter(2**i,2**i)
#         for sequence in g.generate(clear_cache=False):
#             match=False
#             if (g.statistics['overlap_ratio']==Fraction(2,3) and
#                         g.statistics['lexicality']=="N"):
#                 match=True
#             if match==True:
#                 print(sequence)
#                 j=j+1
#                 if j>ncandidates:
#                     break
#         if j>ncandidates:
#             break
