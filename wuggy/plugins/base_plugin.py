import sys
from fractions import Fraction
from collections import namedtuple

Sequence=namedtuple('Sequence',['representation','frequency'])

# decorators
def compute_difference(gen_stat, ref_stat):
    if type(gen_stat) in (tuple,list):
        return [gen_stat[i]-ref_stat[i] for i in range(min(len(gen_stat),len(ref_stat)))]
    elif type(gen_stat)==dict:
        return dict((i,gen_stat[i]-ref_stat[i]) for i in range(len(gen_stat)))
    elif type(gen_stat) in [float, int]:
        return gen_stat-ref_stat

def compute_match(gen_stat, ref_stat):
    if gen_stat==ref_stat:
        return True
    else:
        return False

def difference(function):
    function.difference=compute_difference
    return function

def match(function):
    function.match=compute_match
    return function

