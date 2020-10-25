import os
import sys
import random
import codecs
from fractions import Fraction
from collections import defaultdict, namedtuple
import pickle
import threading
from ..utilities.bigramchain import BigramChain
from .pseudowordgenerator import PseudowordGenerator
from math import floor
from enum import Enum
import warnings
from typing import Optional, Callable, Generator, Union, Any
from ..plugins import orthographic_basque, orthographic_dutch, orthographic_english, orthographic_french, orthographic_german, orthographic_italian, orthographic_polish, orthographic_serbian_cyrillic, orthographic_serbian_latin, orthographic_spanish, orthographic_vietnamese, phonetic_english_celex, phonetic_english_cmu, phonetic_french, phonetic_italian
from functools import wraps
from urllib.request import urlopen


def _loaded_plugin_required(func):
    """
    Decorator used for regular Wuggy methods to ensure that a valid language plugin is loaded before execution.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(args[0], 'plugin_module'):
            raise Exception(
                "This function cannot be called if no language plugin is loaded!")
        func(*args, **kwargs)
    return wrapper


def _loaded_plugin_required_generator(func):
    """
    Decorator used for Wuggy generator methods to ensure that a valid language plugin is loaded before execution.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(args[0], 'plugin_module'):
            raise Exception(
                "The generator cannot be iterated if no language plugin is loaded!")
        gen = func(*args, **kwargs)
        for val in gen:
            yield val
    return wrapper


class WuggyGenerator(PseudowordGenerator):
    supported_language_plugins = {"orthographic_dutch": orthographic_dutch, "orthographic_english": orthographic_english, "orthographic_french": orthographic_french, "orthographic_german": orthographic_german, "orthographic_italian": orthographic_italian, "orthographic_polish": orthographic_polish, "orthographic_serbian_cyrillic": orthographic_serbian_cyrillic,
                                  "orthographic_serbian_latin": orthographic_serbian_latin, "orthographic_spanish": orthographic_spanish, "orthographic_vietnamese": orthographic_vietnamese, "phonetic_english_celex": phonetic_english_celex, "phonetic_english_cmu": phonetic_english_cmu, "phonetic_french": phonetic_french, "phonetic_italian": phonetic_italian}

    def __init__(self):
        PseudowordGenerator.__init__(self)
        self.data_path = os.path.join(os.path.dirname(__file__), "..", "data")
        self.bigramchain = None
        self.bigramchains = {}
        self.__language_plugin_repository_url = "https://raw.githubusercontent.com/Zenulous/wuggy_language_plugin_data/master/"
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

    def load(self, language_plugin_name: str) -> None:
        """
        Loads in a language plugin, if available, and stores the corresponding bigramchains.
        """
        plugin_module = self.supported_language_plugins.get(
            language_plugin_name)
        if plugin_module is None:
            raise ValueError(
                f"This language is not supported by Wuggy at this moment. Wuggy supports: {(', '.join(self.supported_language_plugins))}")
        if language_plugin_name not in self.bigramchains:
            path = os.path.join(self.data_path, plugin_module.default_data)
            if (not os.path.exists(self.data_path)):
                os.makedirs(os.path)
            if (not os.path.isfile(path)):
                self.__download_language_plugin(language_plugin_name, path)
            data_file = codecs.open(path, 'r', encoding='utf-8')
            self.bigramchains[plugin_module.__name__] = BigramChain(
                plugin_module)
            self.bigramchains[plugin_module.__name__].load(data_file)
        self.__activate(plugin_module.__name__)

    def __download_language_plugin(self, language_plugin_name: str, path_to_save: str) -> None:
        """
        Downloads and saves given language plugin to local storage from the corresponding file repository.
        """
        # TODO: should this become a prompt? Currently auto-downloads.
        # TODO: ensure this works if you use Wuggy as a module, there are issues currently.
        warnings.warn(
            f"The language plugin {language_plugin_name} was not found. Wuggy is currently downloading this plugin for you...")
        raw_file = urlopen(
            f"{self.__language_plugin_repository_url}{language_plugin_name}.txt")
        file = open(f'{path_to_save}', 'w', encoding="utf-8")

        for line in raw_file:
            file.write(line.decode("utf-8"))

    def __activate(self, name: str) -> None:
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
        self.current_language_plugin_name = name

    def __load_word_lexicon(self) -> None:
        """
        Loads the default word lexicon for the currently set language plugin.
        This is currently used internally by __activate only, do not call on your own.
        """
        cutoff = 0
        data_file = codecs.open(
            "%s/%s" % (self.data_path, self.plugin_module.default_word_lexicon), 'r', encoding="utf-8")
        self.word_lexicon = defaultdict(list)
        lines = data_file.readlines()
        for line in lines:
            fields = line.strip().split('\t')
            word = fields[0]
            frequency_per_million = fields[-1]
            if float(frequency_per_million) >= cutoff:
                self.word_lexicon[word[0], len(word)].append(word)
        data_file.close()

    def __load_neighbor_lexicon(self) -> None:
        """
        Loads the default neighbor word lexicon for the currently set language plugin.
        This is currently used internally by __activate only, do not call on your own.
        """
        cutoff = 0
        data_file = codecs.open(
            "%s/%s" % (self.data_path, self.plugin_module.default_neighbor_lexicon), 'r', encoding="utf-8")
        self.neighbor_lexicon = []
        lines = data_file.readlines()
        for line in lines:
            fields = line.strip().split('\t')
            word = fields[0]
            frequency_per_million = fields[-1]
            if float(frequency_per_million) > cutoff:
                self.neighbor_lexicon.append(word)
        data_file.close()

    def __load_lookup_lexicon(self, data_file: bool = None) -> None:
        """
        Loads the default lookup word lexicon for the currently set language plugin.
        This is currently used internally by __activate only, do not call on your own.
        """
        self.lookup_lexicon = {}
        if data_file == None:
            data_file = codecs.open(
                "%s/%s" % (self.data_path, self.plugin_module.default_lookup_lexicon), 'r', encoding="utf-8")
        lines = data_file.readlines()
        for line in lines:
            fields = line.strip().split(self.plugin_module.separator)
            reference, representation = fields[0:2]
            self.lookup_lexicon[reference] = representation
        data_file.close()

    def lookup(self, reference: str) -> Optional[str]:
        """
        Look up a given reference (word) from the currently active lookup lexicon.
        Returns None if the word is not found.
        Commonly used to error check if a given word exists before passing it as a reference sequence.
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

    @_loaded_plugin_required
    def set_reference_sequence(self, sequence: str) -> None:
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
        # TODO: docstring and parameter type hint
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
        Enable a statistic based on its name.
        """
        if name not in self.supported_statistics:
            raise ValueError(f"Statistic {name} is not supported.")
        self.statistics[name] = None

    def set_statistics(self, names: [str]) -> None:
        """
        Enables statistics based on their names.
        """
        for name in names:
            if name not in self.supported_statistics:
                self.statistics = {}
                raise ValueError(f"Statistic {name} is not supported.")
            self.statistics[name] = None

    def set_all_statistics(self) -> None:
        """
        Enable all statistics supported by the current active language plugin.
        Enabling all statistics increases word generation computation time, especially for statistics such as ned1.
        """
        self.set_statistics(self.supported_statistics)

    def apply_statistics(self, sequence: str = None) -> None:
        """
        Apply all statistics which were set beforehand.
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
            raise ValueError(f"Output mode {name} is not supported.")
        self.output_mode = eval("self.plugin_module.output_%s" % (name))

    def set_attribute_filter(self, name: str) -> None:
        """
        Set an attribute filter supported by the currently activated language plugin.
        """
        reference_sequence = self.reference_sequence
        if name not in self.supported_attribute_filters:
            raise ValueError(
                f"Attribute filter {name} is not supported.")
        self.attribute_filters[name] = reference_sequence
        self.attribute_subchain = None

    def set_attribute_filters(self, names: [str]) -> None:
        """
        Set attribute filters supported by the currently activated language plugin.
        """
        for name in names:
            self.set_attribute_filter(name)

    def __apply_attribute_filters(self) -> None:
        """
        Apply all set attribute filters.
        This is currently used by generate() internally, do not call on your own.
        """
        for attribute, reference_sequence in self.attribute_filters.items():
            subchain = self.attribute_subchain if self.attribute_subchain != None else self.bigramchain
            self.attribute_subchain = subchain.attribute_filter(
                reference_sequence, attribute)

    def clear_attribute_filters(self) -> None:
        """
        Remove all set attribute filters.
        """
        self.attribute_filters = {}

    def set_frequency_filter(self, lower: int, upper: int) -> None:
        """
        Sets the frequency filter for concentric search.
        Stricter search (small values for lower and upper) result in faster word generation.
        """
        self.frequency_filter = (self.reference_sequence, lower, upper)

    def clear_frequency_filter(self) -> None:
        """
        Clear the previously set frequency filter.
        """
        self.frequency_filter = None
        self.frequency_subchain = None

    def apply_frequency_filter(self) -> None:
        """
        Apply the previously set frequency filter.
        """
        if self.frequency_filter is None:
            raise Exception("No frequency filter was set")
        reference_sequence, lower, upper = self.frequency_filter
        subchain = self.attribute_subchain if self.attribute_subchain != None else self.bigramchain
        self.frequency_subchain = subchain.frequency_filter(
            reference_sequence, lower, upper)

    def set_segmentset_filter(self, segmentset: set) -> None:
        """
        TODO: finish docstring, make sure the purpose of this function is clear
        """
        if type(segmentset) != set:
            segmentset = set(segmentset)
        self.segmentset_filter = segmentset

    def clear_segmentset_filter(self) -> None:
        """
        Set the previously set segmentset filter.
        """
        self.segmentset_filter = None
        self.segmentset_subchain = None

    def apply_segmentset_filter(self) -> None:
        """
        Apply the previously set segmentset filter.
        """
        if self.segmentset_filter is None:
            raise Exception("No segmentset filter has been set")
        if self.frequency_subchain != None:
            subchain = self.frequency_subchain
        elif self.attribute_subchain != None:
            subchain = self.attribute_subchain
        else:
            subchain = self.bigramchain
        self.segmentset_subchain = subchain.segmentset_filter(
            self.reference_sequence, self.segmentset_filter)

    @_loaded_plugin_required_generator
    def generate_simple(self, sequence: str) -> Generator[str, None, None]:
        # TODO: classic, copy UI possibilities
        """
        Creates a generator returning generated pseudowords, can be called immediately after loading a language plugin.
        Uses sensible defaults which do not have to be set by the user.
        Only pseudowords with a large overlap with the input sequence are returned.
        This method always clears the sequence cache.
        """
        self.__clear_sequence_cache()
        if self.lookup(sequence) == None:
            raise Exception(
                f"Word was not found in lexicon {self.current_language_plugin_name}")
        self.set_reference_sequence(sequence)
        self.set_output_mode("plain")
        subchain = self.bigramchain
        self.set_statistic("overlap_ratio")
        self.set_statistic("lexicality")
        # TODO: all stats on except deviation
        for i in range(1, 10, 1):
            # TODO: should we set the frequency filter automatically as done here? Probably most user friendly.
            self.set_frequency_filter(2**i, 2**i)
            self.apply_frequency_filter()
            subchain = self.frequency_subchain
            subchain = subchain.clean(len(self.reference_sequence)-1)
            subchain.set_startkeys(self.reference_sequence)
            for sequence in subchain.generate():
                if self.plugin_module.output_plain(sequence) in self.sequence_cache:
                    pass
                else:
                    self.current_sequence = sequence
                    self.apply_statistics()
                    # TODO: should we set the overlap ratio like here to generate 'close' pseudowords by default?
                    if (self.statistics["overlap_ratio"] == Fraction(2, 3) and self.statistics["lexicality"] == "N"):
                        # TODO: do we even need to add to cache if this function clears cache anyway?
                        self.sequence_cache.append(
                            self.plugin_module.output_plain(sequence))

                        yield self.output_mode(sequence)

    @_loaded_plugin_required_generator
    def generate(self, clear_cache: bool = True) -> Union[Generator[str, None, None], Generator[tuple, None, None]]:
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
                self.__apply_attribute_filters()
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
