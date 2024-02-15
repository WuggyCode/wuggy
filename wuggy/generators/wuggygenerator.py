import codecs
import copy
import importlib
import inspect
import os
from collections import defaultdict, namedtuple
from csv import writer
from fractions import Fraction
from functools import wraps
from pathlib import Path
from shutil import rmtree
from sys import stdout
from time import time
from typing import Dict, Generator, Optional, Union
from urllib.request import urlopen
from warnings import warn

from ..plugins.baselanguageplugin import BaseLanguagePlugin
from ..utilities.bigramchain import BigramChain


def _loaded_language_plugin_required(func):
    """
    Decorator used for regular Wuggy methods to ensure that a valid language plugin is loaded before execution.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(args[0], 'language_plugin'):
            raise Exception(
                "This function cannot be called if no language plugin is loaded!")
        return func(*args, **kwargs)
    return wrapper


def _loaded_language_plugin_required_generator(func):
    """
    Decorator used for Wuggy generator methods to ensure that a valid language plugin is loaded before execution.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(args[0], 'language_plugin'):
            raise Exception(
                "The generator cannot be iterated if no language plugin is loaded!")
        gen = func(*args, **kwargs)
        for val in gen:
            yield val
    return wrapper


class WuggyGenerator():
    def __init__(self):
        self.bigramchain = None
        self.bigramchains = {}
        self.supported_official_language_plugin_names = [
            "orthographic_basque",
            "orthographic_dutch",
            "orthographic_english",
            "orthographic_french",
            "orthographic_german",
            "orthographic_italian",
            "orthographic_polish",
            "orthographic_serbian_cyrillic",
            "orthographic_serbian_latin",
            "orthographic_spanish",
            "orthographic_vietnamese",
            "orthographic_estonian",
            "phonetic_english_celex",
            "phonetic_english_cmu",
            "phonetic_french",
            "phonetic_italian"]
        self.__official_language_plugin_repository_url = "https://raw.githubusercontent.com/WuggyCode/wuggy_language_plugin_data/master"
        self.attribute_subchain = None
        self.frequency_subchain = None
        self.reference_sequence = None
        self.frequency_filter = None
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

    def load(self, language_plugin_name: str,
             local_language_plugin: BaseLanguagePlugin = None) -> None:
        """
        Loads in a language plugin, if available, and stores the corresponding bigramchains.
        Parameters:
            language_plugin_name: must be the exact string of an official language plugin (see self.supported_official_language_plugin_names). If you are loading in a local plugin, the name can be anything as long as it does not conflict with an already loaded plugin name.

            local_language_plugin: must be a child class of BaseLanguagePlugin: see BaseLanguagePlugin for more information on how to create a custom language plugin.
        """
        if local_language_plugin:
            # TODO: if someone does not pass a class INSTANCE, they get TypeError: <class 'type'> is a built-in class, this is a vague error and probably should be abstracted
            self.language_plugin_data_path = os.path.dirname(
                inspect.getfile(local_language_plugin.__class__))
            self.language_plugin_name = language_plugin_name
            language_plugin = local_language_plugin

        if local_language_plugin is None:
            if language_plugin_name not in self.supported_official_language_plugin_names:
                raise ValueError(
                    "This language is not officially supported by Wuggy at this moment. If this is a local plugin, pass the local_language_plugin")
            self.language_plugin_name = language_plugin_name
            language_plugins_folder_dirname = os.path.join(
                Path(__file__).parents[1], "plugins", "language_data")
            self.language_plugin_data_path = os.path.join(
                language_plugins_folder_dirname, language_plugin_name)
            if not os.path.exists(self.language_plugin_data_path):
                self.download_language_plugin(
                    language_plugin_name)
            # Official language plugins MUST have the class name "OfficialLanguagePlugin"!
            language_plugin = importlib.import_module(
                f".plugins.language_data.{language_plugin_name}.{language_plugin_name}",
                "wuggy").OfficialLanguagePlugin()

        if language_plugin_name not in self.bigramchains:
            default_data_path = os.path.join(
                self.language_plugin_data_path, language_plugin.default_data)

            data_file = codecs.open(default_data_path, 'r', encoding='utf-8')
            self.bigramchains[self.language_plugin_name] = BigramChain(
                language_plugin)
            self.bigramchains[self.language_plugin_name].load(
                data_file)
        self.__activate(self.language_plugin_name)

    @staticmethod
    def remove_downloaded_language_plugins() -> None:
        """
        Removes all downloaded (official) language plugins.
        Useful to cleanup after an experiment or to remove corrupt language plugins.
        """
        try:
            rmtree(os.path.join(Path(__file__).parents[1], "plugins", "language_data"))
        except FileNotFoundError as err:
            raise FileNotFoundError(
                "The official language plugin folder is already removed.") from err

    def download_language_plugin(
            self, language_plugin_name: str, auto_download=False) -> None:
        """
        Downloads and saves given language plugin to local storage from the corresponding official file repository.
        This method is called when you load in a language plugin automatically and you are missing the plugin locally.
        If you need to ensure your Wuggy script works on any machine without user confirmation, execute this method with the auto_download flag set to True before using the load method.
        Parameters:
            language_plugin_name: this is the name for the official language plugin you want to download. If the language name is not officially supported, the method will throw an error.

            auto_download: determines whether Wuggy provides the user with a prompt to confirm downloading a language plugin.
        """
        if language_plugin_name not in self.supported_official_language_plugin_names:
            raise ValueError("This language is not officially supported by Wuggy at this moment.")

        if not auto_download:
            while True:
                stdout.write(
                    f"The language plugin {language_plugin_name} was not found in local storage. Do you allow Wuggy to download this plugin? [y/n]\n")
                choice = input().lower()
                if (not (choice.startswith("y") or choice.startswith("n"))):
                    stdout.write("Please respond with 'y' or 'n'")
                elif choice.startswith("n"):
                    raise ValueError(
                        "User declined permission for Wuggy to download necessary language plugin.")
                else:
                    break

        language_plugins_folder_dirname = os.path.join(
            Path(__file__).parents[1], "plugins", "language_data")
        if not os.path.exists(language_plugins_folder_dirname):
            os.makedirs(language_plugins_folder_dirname)

        self.language_plugin_data_path = os.path.join(
            language_plugins_folder_dirname, language_plugin_name)
        if not os.path.exists(self.language_plugin_data_path):
            os.makedirs(self.language_plugin_data_path)

        print(
            f"Wuggy is currently downloading the plugin {language_plugin_name} for you from the official repository...")
        
        py_file_name = f"{language_plugin_name}.py"
        print(f"{self.__official_language_plugin_repository_url}/{language_plugin_name}/{py_file_name}")
        py_file = urlopen(
            f"{self.__official_language_plugin_repository_url}/{language_plugin_name}/{py_file_name}")

        file = open(f'{self.language_plugin_data_path}/{py_file_name}',
                    'w', encoding="utf-8")
        # The current setup assumes that every official Wuggy language plugin use a single data file
        for line in py_file:
            file.write(line.decode("utf-8"))
        data_file_name = f"{language_plugin_name}.txt"
        data_file = urlopen(
            f"{self.__official_language_plugin_repository_url}/{language_plugin_name}/{data_file_name}")
        file = open(f'{self.language_plugin_data_path}/{data_file_name}',
                    'w', encoding="utf-8")

        for line in data_file:
            file.write(line.decode("utf-8"))

        print(f"Wuggy has finished downloading {language_plugin_name}.")

    def __activate(self, name: str) -> None:
        """
        Activate a language plugin by setting the corresponding bigramchains and lexicon properties.
        This deactivates and garbage collects any previously activated language plugin.
        Should only be called internally, do not call on your own.
        """
        if isinstance(name, type(codecs)):
            name = name.__name__
        self.bigramchain = self.bigramchains[name]
        self.language_plugin = self.bigramchain.language_plugin
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
            "%s/%s" % (self.language_plugin_data_path, self.language_plugin.default_word_lexicon),
            'r', encoding="utf-8")
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
            "%s/%s" %
            (self.language_plugin_data_path,
             self.language_plugin.default_neighbor_lexicon),
            'r',
            encoding="utf-8")
        self.neighbor_lexicon = []
        lines = data_file.readlines()
        for line in lines:
            fields = line.strip().split('\t')
            word = fields[0]
            frequency_per_million = fields[-1]
            if float(frequency_per_million) >= cutoff:
                self.neighbor_lexicon.append(word)
        data_file.close()

    def __load_lookup_lexicon(self, data_file: bool = None) -> None:
        """
        Loads the default lookup word lexicon for the currently set language plugin.
        This is currently used internally by __activate only, do not call on your own.
        """
        self.lookup_lexicon = {}
        if data_file is None:
            data_file = codecs.open(
                "%s/%s" %
                (self.language_plugin_data_path,
                 self.language_plugin.default_lookup_lexicon),
                'r',
                encoding="utf-8")
        lines = data_file.readlines()
        for line in lines:
            fields = line.strip().split(self.language_plugin.separator)
            reference, representation = fields[0:2]
            self.lookup_lexicon[reference] = representation
        data_file.close()

    def lookup_reference_segments(self, reference: str) -> Optional[str]:
        """
        Look up a given reference (word) from the currently active lookup lexicon.
        Returns the segments of the found word, if the word is not found it returns None.
        This should be used before setting a word as a reference sequence.
        """
        return self.lookup_lexicon.get(reference, None)

    def __get_attributes(self) -> [namedtuple]:
        """
        Returns a list of all attribute fields of the currently activated language plugin as a named tuple.
        This should only be used internally, read the property "supported_attribute_filters" instead.
        """
        return self.language_plugin.Segment._fields

    def __get_default_attributes(self) -> [str]:
        """
        Returns a list of default attribute fields of the currently activated language plugin.
        This should only be used internally, read the property "default_attributes" instead.
        """
        return self.language_plugin.default_fields

    @_loaded_language_plugin_required
    def set_reference_sequence(self, sequence: str) -> None:
        """
        Set the reference sequence.
        This is commonly used before generate methods in order to set the reference word for which pseudowords should be generated.
        """
        self.reference_sequence = self.language_plugin.transform(
            sequence).representation
        self.reference_sequence_frequencies = self.bigramchain.get_frequencies(
            self.reference_sequence)
        self.__clear_stat_cache()
        for name in self.__get_statistics():
            function = eval("self.language_plugin.statistic_%s" % (name))
            self.reference_statistics[name] = function(
                self, self.reference_sequence)

    def __get_statistics(self) -> [str]:
        """
        Lists all statistics supported by a given language plugin.
        This should only be used internally, read the property "supported_statistics" instead.
        """
        names = [name for name in dir(
            self.language_plugin) if name.startswith('statistic')]
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
        if sequence is None:
            sequence = self.current_sequence
        for name in self.statistics:
            function = eval("self.language_plugin.statistic_%s" % (name))
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
            self.language_plugin) if name.startswith('output')]
        return [name.replace('output_', '') for name in names]

    def set_output_mode(self, name: str) -> None:
        """
        Set an output mode supported by the currently activated language plugin.
        """
        if name not in self.list_output_modes():
            raise ValueError(f"Output mode {name} is not supported.")
        self.output_mode = eval("self.language_plugin.output_%s" % (name))

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
        This is currently used by Wuggy internally, do not call on your own.
        """
        for attribute, reference_sequence in self.attribute_filters.items():
            subchain = self.attribute_subchain if self.attribute_subchain is not None else self.bigramchain
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
        subchain = self.attribute_subchain if self.attribute_subchain is not None else self.bigramchain
        self.frequency_subchain = subchain.frequency_filter(
            reference_sequence, lower, upper)

    @_loaded_language_plugin_required
    def generate_classic(
            self, input_sequences: [str],
            ncandidates_per_sequence: int = 10, max_search_time_per_sequence: int = 10,
            subsyllabic_segment_overlap_ratio: Union[Fraction, None] = Fraction(2, 3),
            match_subsyllabic_segment_length: bool = True, match_letter_length: bool = True,
            output_mode: str = "plain", concentric_search: bool = True) -> [Dict]:
        """
        This is the classic method to generate pseudowords using Wuggy and can be called immediately after loading a language plugin.
        The defaults for this method are similar to those set in the legacy version of Wuggy, resulting in sensible pseudowords.
        This method returns a list of pseudoword matches, including all match and difference statistics (lexicality, ned1, old2, plain_length, deviation statistics...).
        Beware that this method always clears the sequence cache and all previously set filters.
        Parameters:
            input_sequences: these are the input sequences (words) for which you want to generate pseudowords.

            ncandidates_per_sequence: this is the n (maximum) amount of pseudowords you want to generate per input sequence.

            max_search_time_per_sequence: this is the maximum time in seconds to search for pseudowords per input sequence.

            subsyllabic_segment_overlap_ratio: this is the Fraction ratio for overlap between subsyllabic segments. The default ensures your pseudowords are very word-like but not easily identifiable as related to an existing word. If set to None, this constraint is not applied.

            match_subsyllabic_segment_length: determines whether the generated pseudowords must retain the same subsyllabic segment length as the respective input sequence.

            match_letter_length: determines whether the generated pseudowords must retain the same word length as the respective input sequence. This option is redundant if match_subsyllabic_segment_length is set to True.

            output_mode: output mode for pseudowords, constricted by the output modes supported by the currently loaded language plugin.

            concentric_search: enable/disable concentric search. Wuggy operates best and fastest when concentric search is enabled. First, the algorithm will try to generate candidates that exactly match the transition frequencies of the reference word. Then the maximal allowed deviation in transition frequencies will increase by powers of 2 (i.e., +/-2, +/-4, +/-8, etc.).
        .. include:: ../../documentation/wuggygenerator/generate_classic.md
        """
        pseudoword_matches = []
        for input_sequence in input_sequences:
            pseudoword_matches.extend(
                self.__generate_classic_inner(
                    input_sequence,
                    ncandidates_per_sequence,
                    max_search_time_per_sequence,
                    subsyllabic_segment_overlap_ratio,
                    match_subsyllabic_segment_length,
                    match_letter_length, output_mode, concentric_search))
        return pseudoword_matches

    def __generate_classic_inner(
            self, input_sequence: str, ncandidates_per_sequence: int, max_search_time: int,
            subsyllabic_segment_overlap_ratio: Union[Fraction, None],
            match_subsyllabic_segment_length: bool, match_letter_length: bool, output_mode: str,
            concentric_search: bool = True):
        """
        Inner method for generate_classic(), which outputs a list of pseudoword matches for an input sequence.
        Should only be used by WuggyGenerator internally.
        """
        self.__clear_sequence_cache()
        self.clear_attribute_filters()
        self.clear_frequency_filter()
        input_sequence_segments = self.lookup_reference_segments(input_sequence)
        if input_sequence_segments is None:
            raise Exception(
                f"Sequence {input_sequence} was not found in lexicon {self.current_language_plugin_name}")
        self.set_reference_sequence(input_sequence_segments)
        self.set_output_mode(output_mode)
        subchain = self.bigramchain
        starttime = time()
        pseudoword_matches = []
        frequency_exponent = 1
        if match_subsyllabic_segment_length:
            self.set_attribute_filter("segment_length")
            self.__apply_attribute_filters()
            subchain = self.attribute_subchain
        while True:
            if concentric_search:
                self.set_frequency_filter(
                    2**frequency_exponent, 2**frequency_exponent)
                frequency_exponent += 1
                self.apply_frequency_filter()
                subchain = self.frequency_subchain
            subchain = subchain.clean(len(self.reference_sequence) - 1)
            subchain.set_startkeys(self.reference_sequence)
            for sequence in subchain.generate():
                # Mandatory statistics before finding a suitable match
                self.clear_statistics()
                self.set_statistics(["overlap_ratio", "plain_length", "lexicality"])
                if (time() - starttime) >= max_search_time:
                    return pseudoword_matches
                if self.language_plugin.output_plain(sequence) in self.sequence_cache:
                    continue
                self.current_sequence = sequence
                self.apply_statistics()
                if (not match_subsyllabic_segment_length and match_letter_length and self.difference_statistics["plain_length"] != 0):
                    continue
                if (subsyllabic_segment_overlap_ratio is not None and self.statistics["overlap_ratio"] !=
                        subsyllabic_segment_overlap_ratio):
                    continue
                if self.statistics["lexicality"] == "W":
                    continue
                # (Re)apply all statistics only if match is found: else search becomes unnecessarily slow
                self.set_all_statistics()
                self.apply_statistics()
                self.sequence_cache.append(
                    self.language_plugin.output_plain(sequence))
                match = {"word": input_sequence,
                         "segments": input_sequence_segments,
                         "pseudoword": self.output_mode(sequence)}
                match.update({"statistics": self.statistics,
                              "difference_statistics": self.difference_statistics})

                pseudoword_matches.append(copy.deepcopy(match))
                if len(pseudoword_matches) >= ncandidates_per_sequence:
                    return pseudoword_matches

    @_loaded_language_plugin_required_generator
    def generate_advanced(self, clear_cache: bool = True) -> Union[Generator[str, None, None],
                                                                   Generator[tuple, None, None]]:
        """
        Creates a custom generator which can be iterated to return generated pseudowords.
        The generator's settings, such as output statistics, should be set by you before calling this method.
        If attributes such as \"output_mode\" are not set, sensible defaults are used.
        Note that this method is for advanced users and may result in unexpected results if handled incorrectly.
        .. include:: ../../documentation/wuggygenerator/generate_advanced.md
        """
        if clear_cache:
            self.__clear_sequence_cache()
        if self.output_mode is None:
            self.set_output_mode("plain")
        if len(self.attribute_filters) == 0 and self.frequency_subchain is None:
            subchain = self.bigramchain
        if len(self.attribute_filters) != 0:
            if self.attribute_subchain is None:
                self.__apply_attribute_filters()
            subchain = self.attribute_subchain
        if self.frequency_filter is not None:
            self.apply_frequency_filter()
            subchain = self.frequency_subchain
        if self.reference_sequence is not None:
            subchain = subchain.clean(len(self.reference_sequence) - 1)
            subchain.set_startkeys(self.reference_sequence)
        else:
            warn(
                "No reference sequence was set. Ignore this message if this was intentional.")
            subchain.set_startkeys()
        for sequence in subchain.generate():
            if self.language_plugin.output_plain(sequence) in self.sequence_cache:
                pass
            else:
                self.sequence_cache.append(
                    self.language_plugin.output_plain(sequence))
                self.current_sequence = sequence
                self.apply_statistics()
                yield self.output_mode(sequence)

    def export_classic_pseudoword_matches_to_csv(
            self, pseudoword_matches: [Dict],
            csv_path: str) -> None:
        """
        Helper function to export generated pseudoword matches from generate_classic to CSV.
        The dictionairies from the matches are flattened before exporting to CSV.
        Parameters:
            pseudoword_matches: a dictionary of pseudoword matches retrieved from generate_classic

            csv_path: relative path to save csv file to (including the filename, e.g. ./pseudowords.csv)
        """
        def get_csv_headers(dictionary: dict):
            headers = []

            def flatten_nested_dict_keys(dictionary: dict, parent_dict_key=None):
                for key, value in dictionary.items():
                    key = str(key)
                    if isinstance(value, dict):
                        flatten_nested_dict_keys(
                            value, (parent_dict_key + "_" + key if parent_dict_key else key))
                    else:
                        if parent_dict_key:
                            headers.append((parent_dict_key + "_" + key))
                        else:
                            headers.append(key)
                return headers
            flatten_nested_dict_keys(dictionary)
            return headers

        def get_values_from_nested_dictionary(dictionary: dict):
            dict_vals = []

            def flatten_nested_dict_values(dictionary: dict):
                for value in dictionary.values():
                    if isinstance(value, dict):
                        flatten_nested_dict_values(value)
                    else:
                        dict_vals.append(value)
            flatten_nested_dict_values(dictionary)
            return dict_vals

        with open(csv_path, "w", newline='') as csvfile:
            file_writer = writer(csvfile)
            file_writer.writerow(get_csv_headers(pseudoword_matches[0]))
            for match in pseudoword_matches:
                file_writer.writerow(get_values_from_nested_dictionary(match))
