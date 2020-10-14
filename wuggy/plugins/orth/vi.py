import re


class Language:
    double_letters = [u'eo', u'éo', u'èo', u'ẻo', u'ẽo', u'ẹo', u'êu', u'ếu', u'ều',
                      u'ểu', u'ễu', u'ệu', u'ia', u'ía', u'ìa', u'ỉa', u'ĩa', u'ịa', u'ia', u'iá',
                      u'ià', u'iả', u'iã', u'iạ', u'iê', u'iế', u'iề', u'iể', u'iễ', u'iệ', u'oo',
                      u'oó', u'oò', u'oỏ', u'oõ', u'oọ', u'uô', u'uố', u'uồ', u'uổ', u'uỗ', u'uộ',
                      u'ưa', u'ứa', u'ừa', u'ửa', u'ữa', u'ựa', u'ươ', u'ướ', u'ườ', u'ưở', u'ưỡ',
                      u'ượ', u'yê', u'yế', u'yề', u'yể', u'yễ', u'yệ', u'uơ', u'uớ', u'uờ', u'uở',
                      u'uỡ', u'uợ']

    single_letters = [u'a', u'á', u'à', u'ả', u'ã', u'ạ', u'â', u'ấ', u'ầ', u'ẩ',
                      u'ẫ', u'ậ', u'ă', u'ắ', u'ằ', u'ẳ', u'ẵ', u'ặ', u'e', u'é', u'è', u'ẻ', u'ẽ',
                      u'ẹ', u'ê', u'ế', u'ề', u'ể', u'ễ', u'ệ', u'i', u'í', u'ì', u'ỉ', u'ĩ', u'ị',
                      u'o', u'ó', u'ò', u'ỏ', u'õ', u'ọ', u'ô', u'ố', u'ồ', u'ổ', u'ỗ', u'ộ', u'ơ',
                      u'ớ', u'ờ', u'ở', u'ỡ', u'ợ', u'u', u'ú', u'ù', u'ủ', u'ũ', u'ụ', u'ư', u'ứ',
                      u'ừ', u'ử', u'ữ', u'ự', u'y', u'ý', u'ỳ', u'ỷ', u'ỹ', u'ỵ']

    double_letter_pattern = '|'.join(double_letters)
    single_letter_pattern = '|'.join(single_letters)
    nucleuspattern = '%s|%s' % (double_letter_pattern, single_letter_pattern)
    oncpattern = re.compile('(.*?)(%s)(.*)' % nucleuspattern)
