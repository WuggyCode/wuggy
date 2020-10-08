import os
import sys
import random
import codecs
from fractions import Fraction
from collections import defaultdict, namedtuple
import pickle
import threading
from utilities.BigramChain import BigramChain
from .PseudowordGenerator import PseudowordGenerator
from math import floor
from enum import Enum
import warnings
from typing import Optional, Callable
# TODO: add orthographic_serbian.
from plugins import orthographic_basque, orthographic_dutch, orthographic_english, orthographic_french, orthographic_german, orthographic_italian, orthographic_polish, orthographic_serbian_cyrillic, orthographic_serbian_latin, orthographic_spanish, orthographic_vietnamese, phonetic_english_celex, phonetic_english_cmu, phonetic_french, phonetic_italian


def loaded_plugin_required(func: Callable):
    """
    Decorator used for most Wuggy methods to ensure that a valid language plugin is loaded before execution.
    """

    def wrapper(*args, **kwargs):
        if not hasattr(args[0], 'plugin_module'):
            raise Exception(
                "This function cannot be called if no language plugin is loaded!")
        # TODO: make sure this decorator works for the genererator given by generate(), or find alternative
        func(*args, **kwargs)
    return wrapper


class WuggyGenerator(PseudowordGenerator):

    def __init__(self):
        PseudowordGenerator.__init__(self)
        self.data_path = 'data'
        self.bigramchain = None
        self.bigramchains = {}
        self.supported_languages = {"orthographic_dutch": orthographic_dutch, "orthographic_english": orthographic_english, "orthographic_french": orthographic_french, "orthographic_german": orthographic_german, "orthographic_italian": orthographic_italian, "orthographic_polish": orthographic_polish, "orthographic_serbian_cyrillic": orthographic_serbian_cyrillic,
                                    "orthographic_serbian_latin": orthographic_serbian_latin, "orthographic_spanish": orthographic_spanish, "orthographic_vietnamese": orthographic_vietnamese, "phonetic_english_celex": phonetic_english_celex, "phonetic_english_cmu": phonetic_english_cmu, "phonetic_french": phonetic_french, "phonetic_italian": phonetic_italian}
        self.attribute_subchain = None
        self.frequency_subchain = None
        self.segmentset_subchain = None
        self.reference_sequence = None
        self.frequency_filter = None
        self.segmentset_filter = None
        self.current_sequence = None
        self.output_mode = None
        self.supported_statistics = ()
        self.supported_attribute_filters = {}
        self.attribute_filters = {}
        self.default_attributes = []
        self.statistics = {}
        self.word_lexicon = defaultdict(list)
        self.neighbor_lexicon = []
        self.reference_statistics = {}
        self.stat_cache = {}
        self.sequence_cache = []
        self.difference_statistics = {}
        self.match_statistics = {}
        self.lookup_lexicon = {}

    def load(self, language: str) -> None:
        """
        Loads in a language plugin, if available, and stores the corresponding bigramchains.
        """
        plugin_module = self.supported_languages.get(language)
        if plugin_module is None:
            raise ValueError(
                "This language is not supported by Wuggy at this moment")
        # TODO: check if cached bigramchain works
        if language not in self.bigramchains:
            path = u"%s/%s" % (self.data_path, plugin_module.default_data)
            data_file = codecs.open(path, 'r', plugin_module.default_encoding)
            self.bigramchains[plugin_module.__name__] = BigramChain(
                plugin_module)
            self.bigramchains[plugin_module.__name__].load(data_file)
        self.__activate(plugin_module.__name__)

    def __activate(self, name) -> None:
        """
        Activate a language plugin by setting the corresponding bigramchains and lexicon properties.
        This deactivates and garbage collects any previously activated language plugin.
        Should only be called internally, do not call on your own.
        """
        if type(name) == type(codecs):
            name = name.__name__
        self.bigramchain = self.bigramchains[name]
        self.plugin_module = self.bigramchain.plugin_module
        self.__load_neighbor_lexicon()
        self.__load_word_lexicon()
        self.__load_lookup_lexicon()
        self.supported_statistics = self.__get_statistics()
        self.supported_attribute_filters = self.__get_attributes()
        self.default_attributes = self.__get_default_attributes()

    def __load_word_lexicon(self) -> None:
        """
        Loads the default word lexicon for the currently set language plugin.
        This is currently used internally by __activate only, do not call on your own.
        """
        cutoff = 0
        data_file = codecs.open(
            "%s/%s" % (self.data_path, self.plugin_module.default_word_lexicon), 'r', self.plugin_module.default_encoding)
        self.word_lexicon = defaultdict(list)
        lines = data_file.readlines()
        for i, line in enumerate(lines):
            fields = line.strip().split('\t')
            word = fields[0]
            frequency_per_million = fields[-1]
            if float(frequency_per_million) > cutoff:
                self.word_lexicon[word[0], len(word)].append(word)
        data_file.close()

    def __load_neighbor_lexicon(self) -> None:
        """
        Loads the default neighbor word lexicon for the currently set language plugin.
        This is currently used internally by __activate only, do not call on your own.
        """
        cutoff = 0
        data_file = codecs.open(
            "%s/%s" % (self.data_path, self.plugin_module.default_neighbor_lexicon), 'r', self.plugin_module.default_encoding)
        self.neighbor_lexicon = []
        lines = data_file.readlines()
        for i, line in enumerate(lines):
            fields = line.strip().split('\t')
            word = fields[0]
            frequency_per_million = fields[-1]
            if float(frequency_per_million) > cutoff:
                self.neighbor_lexicon.append(word)
        data_file.close()

    def __load_lookup_lexicon(self, data_file=None) -> None:
        """
        Loads the default lookup word lexicon for the currently set language plugin.
        This is currently used internally by __activate only, do not call on your own.
        """
        self.lookup_lexicon = {}
        if data_file == None:
            data_file = codecs.open(
                "%s/%s" % (self.data_path, self.plugin_module.default_lookup_lexicon), 'r', self.plugin_module.default_encoding)
        lines = data_file.readlines()
        for i, line in enumerate(lines):
            fields = line.strip().split(self.plugin_module.separator)
            reference, representation = fields[0:2]
            self.lookup_lexicon[reference] = representation
        data_file.close()

    def lookup(self, reference: str) -> Optional[str]:
        """
        Look up a given reference (word) from the currently active lookup lexicon.
        Returns None if the word is not found.
        Commonly used to error check a given word before passing it as a reference sequence.
        """
        return self.lookup_lexicon.get(reference, None)

    def __get_attributes(self) -> [namedtuple]:
        """
        Returns a list of all attribute fields of the currently activated language plugin as a named tuple.
        This should only be used internally, read the property "supported_attribute_filters" instead.
        """
        return self.plugin_module.Segment._fields

    def __get_default_attributes(self) -> [str]:
        """
        Returns a list of default attribute fields of the currently activated language plugin.
        This should only be used internally, read the property "default_attributes" instead.
        """
        return self.plugin_module.default_fields

    @loaded_plugin_required
    def set_reference_sequence(self, sequence: str):
        """
        Set the reference sequence.
        This is commonly used before generate() in order to set the reference word for which pseudowords should be generated.
        """
        self.reference_sequence = self.plugin_module.transform(
            sequence).representation
        self.reference_sequence_frequencies = self.bigramchain.get_frequencies(
            self.reference_sequence)
        self.__clear_stat_cache()
        for name in self.__get_statistics():
            function = eval("self.plugin_module.statistic_%s" % (name))
            self.reference_statistics[name] = function(
                self, self.reference_sequence)

    def get_limit_frequencies(self, fields):
        # TODO: docstring
        limits = []
        if tuple(fields) not in self.bigramchain.limit_frequencies:
            self.bigramchain.build_limit_frequencies(fields)
        for i in range(0, len(self.reference_sequence)-1):
            subkey_a = (i, tuple(
                [self.reference_sequence[i].__getattribute__(field) for field in fields]))
            subkey_b = (
                i+1, tuple([self.reference_sequence[i+1].__getattribute__(field) for field in fields]))
            subkey = (subkey_a, subkey_b)
            try:
                limits.append(
                    self.bigramchain.limit_frequencies[tuple(fields)][subkey])
            except:
                limits.append([{max: 0, min: 0}])
        return limits

    def __get_statistics(self) -> [str]:
        """
        Lists all statistics supported by a given language plugin.
        This should only be used internally, read the property "supported_statistics" instead.
        """
        names = [name for name in dir(
            self.plugin_module) if name.startswith('statistic')]
        return [name.replace('statistic_', '') for name in names]

    def set_statistic(self, name: str) -> None:
        """
        Enable a statistic based on its name
        """
        if name not in self.supported_statistics:
            raise ValueError("Statistic {} is not supported.".format(name))
        self.statistics[name] = None

    def set_statistics(self, names: [str]) -> None:
        for name in names:
            if name not in self.supported_statistics:
                self.statistics = {}
                raise ValueError("Statistic {} is not supported.".format(name))
            self.statistics[name] = None

    def set_all_statistics(self) -> None:
        """
        Enable all statistics supported by the current active language plugin.
        """
        self.set_statistics(self.supported_statistics)

    def apply_statistics(self, sequence: str = None) -> None:
        """
        Apply all statistics which were set beforehand
        """
        if sequence == None:
            sequence = self.current_sequence
        for name in self.statistics:
            function = eval("self.plugin_module.statistic_%s" % (name))
            if (sequence, name) in self.stat_cache:
                self.statistics[name] = self.stat_cache[(sequence, name)]
            else:
                self.statistics[name] = function(self, sequence)
                self.stat_cache[(sequence, name)] = self.statistics[name]
            if 'match' in function.__dict__:
                self.match_statistics[name] = function.match(
                    self.statistics[name], self.reference_statistics[name])
            if 'difference' in function.__dict__:
                self.difference_statistics[name] = function.difference(
                    self.statistics[name], self.reference_statistics[name])

    def clear_statistics(self) -> None:
        """
        Clear all the statistics set previously.
        """
        self.statistics = {}

    def __clear_stat_cache(self) -> None:
        """
        Clears the statistics cache. Only used by Wuggy internally.
        """
        self.stat_cache = {}

    def __clear_sequence_cache(self) -> None:
        """
        Clears the sequence cache. Only used by Wuggy internally.
        """
        self.sequence_cache = []

    def list_output_modes(self) -> [str]:
        """
        List output modes of the currently activated language plugin.
        """
        names = [name for name in dir(
            self.plugin_module) if name.startswith('output')]
        return [name.replace('output_', '') for name in names]

    def set_output_mode(self, name: str) -> None:
        """
        Set an output mode supported by the currently activated language plugin.
        """
        if name not in self.list_output_modes():
            raise ValueError("Output mode {} is not supported.".format(name))
        self.output_mode = eval("self.plugin_module.output_%s" % (name))

    def set_attribute_filter(self, name, reference_sequence=None):
        """
        Set an attribute filter supported by the currently activated language plugin.
        """
        if reference_sequence == None:
            reference_sequence = self.reference_sequence
        if name not in self.supported_attribute_filters:
            raise ValueError(
                "Attribute filter {} is not supported.".format(name))
        self.attribute_filters[name] = reference_sequence
        self.attribute_subchain = None

    def set_attribute_filters(self, names, reference_sequence=None):
        """
        Set attribute filters supported by the currently activated language plugin.
        """
        for name in names:
            self.set_attribute_filter(
                name, reference_sequence=reference_sequence)

    def apply_attribute_filters(self):
        for attribute, reference_sequence in self.attribute_filters.items():
            subchain = self.attribute_subchain if self.attribute_subchain != None else self.bigramchain
            self.attribute_subchain = subchain.attribute_filter(
                reference_sequence, attribute)

    def clear_attribute_filters(self):
        self.attribute_filters = {}

    def clear_attribute_filter(self, name):
        del self.attribute_filters[name]

    def set_frequency_filter(self, lower, upper, kind='dev', reference_sequence=None):
        if reference_sequence == None:
            reference_sequence = self.reference_sequence
        self.frequency_filter = (reference_sequence, lower, upper, kind)

    def clear_frequency_filter(self):
        self.frequency_filter = None
        self.frequency_subchain = None

    def apply_frequency_filter(self):
        reference_sequence, lower, upper, kind = self.frequency_filter
        subchain = self.attribute_subchain if self.attribute_subchain != None else self.bigramchain
        self.frequency_subchain = subchain.frequency_filter(
            reference_sequence, lower, upper, kind)

    def set_segmentset_filter(self, segmentset):
        if type(segmentset) != set:
            segmentset = set(segmentset)
        self.segmentset_filter = segmentset

    def clear_segmentset_filter(self):
        self.segmentset_filter = None
        self.segmentset_subchain = None

    def apply_segmentset_filter(self):
        segmentset = self.segmentset_filter
        if self.frequency_subchain != None:
            subchain = self.frequency_subchain
        elif self.attribute_subchain != None:
            subchain = self.attribute_subchain
        else:
            subchain = self.bigramchain
        self.segmentset_subchain = subchain.segmentset_filter(
            self.reference_sequence, segmentset)

    def clear_filters(self):
        self.clear_attribute_filters()
        self.clear_frequency_filter()

    @loaded_plugin_required
    def generate(self, clear_cache=True):
        """
        Creates a generator which can be iterated to return generated pseudowords.
        If attributes such as \"output_mode\" are not set, sensible defaults are used.
        """
        if clear_cache == True:
            self.__clear_sequence_cache()
        if self.output_mode == None:
            self.set_output_mode("plain")
        if len(self.attribute_filters) == 0 and self.frequency_subchain == None and self.segmentset_subchain == None:
            subchain = self.bigramchain
        if len(self.attribute_filters) != 0:
            if self.attribute_subchain == None:
                self.apply_attribute_filters()
            subchain = self.attribute_subchain
        if self.frequency_filter != None:
            self.apply_frequency_filter()
            subchain = self.frequency_subchain
        if self.segmentset_filter != None:
            self.apply_segmentset_filter()
            subchain = self.segmentset_subchain
        if self.reference_sequence != None:
            subchain = subchain.clean(len(self.reference_sequence)-1)
            subchain.set_startkeys(self.reference_sequence)
        else:
            warnings.warn(
                "No reference sequence was set. Ignore this message if this was intentional.")
            subchain.set_startkeys()
        for sequence in subchain.generate():
            if self.plugin_module.output_plain(sequence) in self.sequence_cache:
                pass
            else:
                self.sequence_cache.append(
                    self.plugin_module.output_plain(sequence))
                self.current_sequence = sequence
                self.apply_statistics()
                yield self.output_mode(sequence)
