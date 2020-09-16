from sequencegenerator.generator import Generator
import re
import time
from fractions import Fraction
import random

import sys
from sequencegenerator.generator import Generator
from plugins import orthographic_english

g=Generator()
g.data_path=('./data')
g.load(orthographic_english)
g.load_word_lexicon()
g.load_neighbor_lexicon()
g.load_lookup_lexicon()

words=["car"]
ncandidates = 5
## TODO: this should become an elaborate class, allowing a user to generate pseudowords
for word in words:
    g.set_reference_sequence(g.lookup(word))
    g.set_attribute_filter('sequence_length')
    g.set_attribute_filter('segment_length')
    g.set_statistic('overlap_ratio')
    g.set_statistic('plain_length')
    g.set_statistic('transition_frequencies')
    g.set_statistic('lexicality')
    g.set_statistic('ned1')
    g.set_output_mode('syllabic')
    j=0
    for i in range(1,10,1):
        g.set_frequency_filter(2**i,2**i)
        for sequence in g.generate(clear_cache=False):
            match=False
            if (g.statistics['overlap_ratio']==Fraction(2,3) and 
                        g.statistics['lexicality']=="N"):
                match=True
            if match==True:
                print(sequence)
                j=j+1
                if j>ncandidates:
                    break
        if j>ncandidates:
            break

# DEPRECATED: this is the old startup command for Wuggy, only use for reference until Wuggy is fully reimplemented
# TODO: remove this function altogether
def Run(self, options, reference_sequence, match_expression, outputwindow):
        # set the output window
        self.outputwindow=outputwindow
        # clear previous results
        self.clear_sequence_cache()
        self.clear_statistics()
        self.clear_filters()
        # get some general options
        self.maxtime=int(options['search_time'])
        self.maxcandidates=int(options['ncandidates'])
        # which statistics were required by the user?
        statistics=('lexicality', 'old20', 'ned1', 'overlap_ratio')
        active_statistics=[stat for stat in statistics if options[stat]==True]
        # set the reference sequence
        self.raw_reference_sequence=reference_sequence
        self.set_reference_sequence(reference_sequence)
        # set segment length filter if required 
        if options['match_segment_length']==True:
                self.set_attribute_filters(('segment_length',))
        # some options require computation of statistics
        required_statistics=[]
        if options['overlapping_segments']==True:
            required_statistics.append('overlap_ratio')
        if options['output_type']!='Both':
            required_statistics.append('lexicality')
        if options['maxdeviation']==True:
            required_statistics.append('transition_frequencies')
        if options['match_segment_length']==False and options['match_plain_length']==True:
            required_statistics.append('plain_length')
        self.set_statistics(required_statistics)
        # set output mode (also transform reference sequence if necessary)
        if options['output_mode']=="Syllables":
            self.set_output_mode('syllabic')
        elif options['output_mode']=="Segments":
            self.set_output_mode('segmental')
        else:
            self.set_output_mode('plain')
            reference_sequence=reference_sequence.replace(u'-','')
        # compile the matching expression if required (matching is always done on specified output mode!)
        if match_expression!=u"":
            regex=re.compile(match_expression)
        #initialize variables for the main loop
        exponent=1 #frequency matching exponent 
        self.ncandidates=0
        self.nchecked=0
        self.starttime=time.time()
        self.stopgenerator=False

        # the while loop is only relevant for concentric search 
        while(1):
            self.UpdateStatus()
            if self.stopgenerator==True or self.elapsed_time>self.maxtime:
                break
            if options['concentric']==True:
                self.set_frequency_filter(2**exponent,2**exponent)
                exponent=exponent+1
            # this is the loop where the main work is done
            # as concentric search would always find the same sequences
            # we have to keep the found sequences in a cache
            for sequence in self.generate(clear_cache=False):
                # break if required 
                if self.stopgenerator==True:
                    break
                # matching routine #
                # initially, match is True (since all conditions have 
                # to be fulfilled we can reject on one False)
                match=True 
                if (options['overlapping_segments']==True and
                    self.statistics['overlap_ratio']!=Fraction(int(options['overlap_numerator']), 
                    int(options['overlap_denominator']))):
                    match=False
                if (options['match_segment_length']==False and 
                    options['match_plain_length']==True and
                    self.difference_statistics['plain_length']!=0):
                    match=False
                if options['output_type']=='Only pseudowords' and self.statistics['lexicality']=='W':
                    match=False
                if options['output_type']=='Only words' and self.statistics['lexicality']=='N':
                    match=False
                if match_expression!=u"":
                    if regex.match(sequence)==None:
                        match=False
                # what to do if we found a matching candidate
                if match==True:
                    self.ncandidates=self.ncandidates+1
                    # compute statistics required only for output
                    for statistic in active_statistics:
                        self.set_statistic(statistic)
                    self.apply_statistics()
                    # prepare the output #
                    output=[]
                    # append reference sequence and generated sequence (always)
                    output.append(reference_sequence)
                    output.append(sequence)
                    # append all required statistics
                    for statistic in active_statistics:
                        output.append(self.statistics[statistic])
                        if statistic in ['old20', 'ned1']:
                            output.append(self.difference_statistics[statistic])
                    # compute maximal deviation statistic if required
                    if options['maxdeviation']==True:
                        reference_frequencies=self.reference_statistics['transition_frequencies']
                        differences=self.difference_statistics['transition_frequencies']
                        maxindex,maxdev=max(differences.items(),key=lambda x:abs(x[1]))
                        sumdev=sum((abs(d) for d in differences.values()))
                        # maximal deviation
                        output.append(maxdev)
                        # summed deviation
                        output.append(sumdev)
                        # the maximally deviating transition
                        segments=[element.letters for element in self.current_sequence]
                        visual=segments
                        visual[maxindex]=u"[%s" % visual[maxindex]
                        visual[maxindex+1]=u"%s]" % visual[maxindex+1]
                        output.append(u"".join(visual).replace('^','_').replace('$','_'))
                    print(output)
                # make sure only required statistics are computed on the next yield
                self.clear_statistics()
                self.set_statistics(required_statistics)
                self.nchecked=self.nchecked+1
                self.UpdateStatus()
                if self.elapsed_time>=self.maxtime or self.ncandidates>=self.maxcandidates:
                    self.stopgenerator=True
        if options['concentric']==False:
            self.stopgenerator=True