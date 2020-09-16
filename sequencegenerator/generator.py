import os
import sys
import random
import codecs
from fractions import Fraction
from collections import defaultdict
import pickle
import threading
from sequencegenerator import bigramchain
from math import floor

class Generator(object):
    def __init__(self):
        self.data_path='data'
        self.bigramchain=None
        self.bigramchains={}
        self.attribute_subchain=None
        self.frequency_subchain=None
        self.segmentset_subchain=None
        self.reference_sequence=None
        self.frequency_filter=None
        self.segmentset_filter=None
        self.current_sequence=None
        self.output_mode=None
        self.attribute_filters={}
        self.statistics={}
        self.word_lexicon=defaultdict(list)
        self.neighbor_lexicon=[]
        self.reference_statistics={}
        self.stat_cache={}
        self.sequence_cache=[]
        self.difference_statistics={}
        self.match_statistics={}
        self.lookup_lexicon={}
        self.status={'message':'','progress':0}
        self.subscribers=[]
    
    def set_status(self, message, progress):
        for receiver in [self]+self.subscribers:
            receiver.status['message']=message
            receiver.status['progress']=progress
    
    def clear_status(self):
        for receiver in [self]+self.subscribers:
            receiver.status['message']=''
            receiver.status['progress']=0
    
    def load(self, plugin_module, data_file=None, size=100, cutoff=1, token=False):
        if plugin_module.__name__ not in self.bigramchains:
            if data_file==None:
                path = u"%s/%s" % (self.data_path, plugin_module.default_data)
                data_file = codecs.open(path,'r',plugin_module.default_encoding)
            self.bigramchains[plugin_module.__name__]=bigramchain.BigramChain(plugin_module)
            self.bigramchains[plugin_module.__name__].subscribers.append(self)
            self.bigramchains[plugin_module.__name__].load(data_file, size=size, cutoff=cutoff, token=token)
        self.activate(plugin_module.__name__)
        
    def activate(self, name):
        if type(name)==type(codecs):    # unfortunately, the only way I know to check if something is of type 'module'
            name=name.__name__
        self.bigramchain=self.bigramchains[name]
        self.plugin_module=self.bigramchain.plugin_module
        self.load_neighbor_lexicon()
        self.load_word_lexicon()
        self.load_lookup_lexicon()
    
    def load_word_lexicon(self, data_file=None, cutoff=0):
        if data_file==None:
            data_file=codecs.open("%s/%s" % (self.data_path, self.plugin_module.default_word_lexicon), 'r', self.plugin_module.default_encoding)
        self.word_lexicon=defaultdict(list)
        lines=data_file.readlines()
        nlines=float(len(lines))
        for i,line in enumerate(lines):
            if i%1000==0:
                self.set_status('Loading Word Lexicon', i/nlines*100)
            fields=line.strip().split('\t')
            word=fields[0]
            frequency_per_million=fields[-1]
            if float(frequency_per_million)>cutoff:
                self.word_lexicon[word[0],len(word)].append(word)
        data_file.close()
        self.clear_status()
    
    def load_neighbor_lexicon(self, data_file=None, cutoff=1):
        if data_file==None:
            data_file=codecs.open("%s/%s" % (self.data_path, self.plugin_module.default_neighbor_lexicon), 'r', self.plugin_module.default_encoding)
        self.neighbor_lexicon=[]
        lines=data_file.readlines()
        nlines=float(len(lines))
        for i,line in enumerate(lines):
            if i%1000==0:
                self.set_status('Loading Neighbor Lexicon', i/nlines*100)
            fields=line.strip().split('\t')
            word=fields[0]
            frequency_per_million=fields[-1]
            if float(frequency_per_million)>cutoff:
                self.neighbor_lexicon.append(word)
        data_file.close()
        self.clear_status()
    
    def load_lookup_lexicon(self, data_file=None):
        self.lookup_lexicon={}
        if data_file==None:
            data_file=codecs.open("%s/%s" % (self.data_path, self.plugin_module.default_lookup_lexicon), 'r', self.plugin_module.default_encoding)
        lines=data_file.readlines()
        nlines=float(len(lines))
        for i,line in enumerate(lines):
            if i%1000==0:
                self.set_status('Loading Segmentation Lookup Lexicon', i/nlines*100)
            fields=line.strip().split(self.plugin_module.separator)
            reference, representation=fields[0:2]
            self.lookup_lexicon[reference]=representation
        data_file.close()
        self.clear_status()
        
    def lookup(self, reference):
        return self.lookup_lexicon.get(reference, None)

    def list_attributes(self):
        return self.plugin_module.Segment._fields
    
    def list_default_attributes(self):
        return self.plugin_module.default_fields
    
    def set_reference_sequence(self, sequence):
        self.reference_sequence=self.plugin_module.transform(sequence).representation
        self.reference_sequence_frequencies=self.bigramchain.get_frequencies(self.reference_sequence)
        # clear all statistics related to previous reference sequences
        self.clear_stat_cache()
        # compute the reference sequence's lexical statistics
        for name in self.list_statistics():
            function=eval("self.plugin_module.statistic_%s" % (name))
            self.reference_statistics[name]=function(self, self.reference_sequence)
        # # set the default attributes
        # for attribute in self.list_default_attributes():
        #     self.set_attribute_filter(attribute,self.reference_sequence)
    
    def get_limit_frequencies(self, fields):
        limits=[]
        if tuple(fields) not in self.bigramchain.limit_frequencies:
            self.bigramchain.build_limit_frequencies(fields)
        for i in range(0,len(self.reference_sequence)-1):
            subkey_a=(i,tuple([self.reference_sequence[i].__getattribute__(field) for field in fields]))
            subkey_b=(i+1,tuple([self.reference_sequence[i+1].__getattribute__(field) for field in fields]))
            subkey=(subkey_a,subkey_b)
            try:
                limits.append(self.bigramchain.limit_frequencies[tuple(fields)][subkey])
            except:
                limits.append([{max:0,min:0}])
        return limits

    def list_statistics(self):
        names=[name for name in dir(self.plugin_module) if name.startswith('statistic')]
        return [name.replace('statistic_','') for name in names]
    
    def set_statistic(self, name):
        self.statistics[name]=None
    
    def set_statistics(self, names):
        for name in names:
            self.statistics[name]=None
    
    def set_all_statistics(self):
        self.set_statistics(self.list_statistics())
    
    def apply_statistics(self, sequence=None):
        if sequence==None:
            sequence=self.current_sequence
        for name in self.statistics:
            function=eval("self.plugin_module.statistic_%s" % (name))
            if (sequence,name) in self.stat_cache:
                self.statistics[name]=self.stat_cache[(sequence,name)]
            else:
                self.statistics[name]=function(self, sequence)
                self.stat_cache[(sequence, name)]=self.statistics[name]
            # compute matching and difference statistics
            if 'match' in function.__dict__:
                self.match_statistics[name]=function.match(self.statistics[name],self.reference_statistics[name])
            if 'difference' in function.__dict__:
                self.difference_statistics[name]=function.difference(self.statistics[name],self.reference_statistics[name])
    
    def clear_statistics(self):
        self.statistics={}
    
    def clear_stat_cache(self):
        self.stat_cache={}
    
    def clear_sequence_cache(self):
        self.sequence_cache=[]
    
    def list_output_modes(self):
        names=[name for name in dir(self.plugin_module) if name.startswith('output')]
        return [name.replace('output_','') for name in names]
    
    def set_output_mode(self, name):
        self.output_mode=eval("self.plugin_module.output_%s" % (name))
    
    def set_attribute_filter(self, name, reference_sequence=None):
        if reference_sequence==None:
            reference_sequence=self.reference_sequence
        self.attribute_filters[name]=reference_sequence
        self.attribute_subchain=None
    
    def set_attribute_filters(self, names, reference_sequence=None):
        for name in names:
            self.set_attribute_filter(name, reference_sequence=reference_sequence)
    
    def apply_attribute_filters(self):
        for attribute,reference_sequence in self.attribute_filters.items():
            subchain=self.attribute_subchain if self.attribute_subchain!=None else self.bigramchain
            self.attribute_subchain=subchain.attribute_filter(reference_sequence, attribute)
    
    def clear_attribute_filters(self):
        self.attribute_filters={}
    
    def clear_attribute_filter(self, name):
        del self.attribute_filters[name]
    
    def set_frequency_filter(self, lower, upper, kind='dev', reference_sequence=None):
        if reference_sequence==None:
            reference_sequence=self.reference_sequence
        self.frequency_filter=(reference_sequence, lower, upper, kind)
        
    def clear_frequency_filter(self):
        self.frequency_filter=None
        self.frequency_subchain=None
    
    def apply_frequency_filter(self):
        reference_sequence,lower, upper,kind=self.frequency_filter
        subchain=self.attribute_subchain if self.attribute_subchain!=None else self.bigramchain
        self.frequency_subchain=subchain.frequency_filter(reference_sequence,lower,upper,kind)
        
    def set_segmentset_filter(self, segmentset):
        if type(segmentset)!=set:
            segmentset=set(segmentset)
        self.segmentset_filter=segmentset
        
    def clear_segmentset_filter(self):
        self.segmentset_filter=None
        self.segmentset_subchain=None
        
    def apply_segmentset_filter(self):
        segmentset=self.segmentset_filter
        if self.frequency_subchain!=None:
            subchain=self.frequency_subchain
        elif self.attribute_subchain!=None:
            subchain=self.attribute_subchain
        else:
            subchain=self.bigramchain
        self.segmentset_subchain=subchain.segmentset_filter(self.reference_sequence, segmentset)
        
    def clear_filters(self):
        self.clear_attribute_filters()
        self.clear_frequency_filter()
    
    def generate(self, clear_cache=True):
        if clear_cache==True:
            self.clear_sequence_cache()
        if self.output_mode==None:
            output_mode=self.plugin_module.output_pass
        else:
            output_mode=self.output_mode
        if len(self.attribute_filters)==0 and self.frequency_subchain==None and self.segmentset_subchain==None:
            subchain=self.bigramchain
        if len(self.attribute_filters)!=0:
            if self.attribute_subchain==None:
                self.apply_attribute_filters()
            subchain=self.attribute_subchain
        if self.frequency_filter!=None:
            self.apply_frequency_filter()
            subchain=self.frequency_subchain
        if self.segmentset_filter!=None:
            self.apply_segmentset_filter()
            subchain=self.segmentset_subchain
        if self.reference_sequence!=None:
            subchain=subchain.clean(len(self.reference_sequence)-1)
            subchain.set_startkeys(self.reference_sequence)
        else:
            subchain.set_startkeys()
        for sequence in subchain.generate():
            if self.plugin_module.output_plain(sequence) in self.sequence_cache:
                pass
            else:
                self.sequence_cache.append(self.plugin_module.output_plain(sequence))
                self.current_sequence=sequence
                self.apply_statistics()
                yield output_mode(sequence)
    
