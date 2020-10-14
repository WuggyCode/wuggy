import re


class Language:
    single_letters = [u'a', u'i', u'u', u'o', u'e']
    single_letter_pattern = u'|'.join(single_letters)
    nucleuspattern = u'%s' % (single_letter_pattern)
    oncpattern = re.compile(u'(.*?)(%s)(.*)' % nucleuspattern)
