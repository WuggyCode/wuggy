import re


class Language:
    single_vowels = ['a', 'e', 'и', 'o', 'u', 'р']
    nucleuspattern = '%s' % (single_vowels)
    oncpattern = re.compile('(.*?)(%s)(.*)' % nucleuspattern)
