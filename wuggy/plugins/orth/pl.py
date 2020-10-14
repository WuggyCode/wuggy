import re

double_letters=['ia', 'ie', 'io', 'iu']
single_letters=['a', 'e', 'i', 'o', 'u', 'y']
accented_letters=[u'ą', u'ę']
double_letter_pattern=u'|'.join(double_letters)
single_letter_pattern=u'|'.join(single_letters)
accented_letter_pattern=u'|'.join(accented_letters)
nucleuspattern = u'%s|%s|%s' % (double_letter_pattern, accented_letter_pattern, single_letter_pattern)
oncpattern=re.compile(u'(.*?)(%s)(.*)' % nucleuspattern)
