from wuggy.plugins.baselanguageplugin import BaseLanguagePlugin


class SyntheticLanguagePlugin(BaseLanguagePlugin):
    """Minimal plugin over the generated synthetic language data."""
    default_data = 'data.txt'
    default_word_lexicon = 'lexicon.txt'
    default_neighbor_lexicon = 'lexicon.txt'
    default_lookup_lexicon = 'lookup.txt'

    def transform(self, input_sequence, frequency=1):
        return self.copy_onc(input_sequence, frequency)
