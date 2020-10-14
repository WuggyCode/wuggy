import re


class Language:
    single_vowels = ['a', 'e', 'i', 'o', 'u', 'r']
    nucleuspattern = '%s' % (single_vowels)
    oncpattern = re.compile('(.*?)(%s)(.*)' % nucleuspattern)
