import re

class Language:
    double_letters = ['aa', 'ea', 'ee', 'ia', 'ie',
                      'io(?!u)', 'oo', 'oe', 'ou', '(?<!q)ui(?=.)', 'ei', 'eu', 'ae', 'ey(?=.)', 'oa']
    single_letters = ['a', 'e', 'i(?!ou)', 'o', '(?<!q)u', 'y(?![aeiou])']
    accented_letters = [u'à', u'ê', u'è', u'é', u'â', u'ô', u'ü']
    double_letter_pattern = '|'.join(double_letters)
    single_letter_pattern = '|'.join(single_letters)
    accented_letter_pattern = '|'.join(accented_letters)
    nucleuspattern = '%s|%s|%s' % (
        double_letter_pattern, accented_letter_pattern, single_letter_pattern)
    oncpattern = re.compile('(.*?)(%s)(.*)' % nucleuspattern)
