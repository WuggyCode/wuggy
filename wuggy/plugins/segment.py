class Error(Exception):
    """Base class for Exceptions in this module"""
    pass

class SegmentationError(Error):
    """Occurs when an input string cannot be segmented"""
    pass        


def onsetnucleuscoda(orthographic_syllable, lang=None):
    oncpattern=lang.oncpattern
    m=oncpattern.match(orthographic_syllable)
    try:
        return [m.group(1), m.group(2), m.group(3)]
    except AttributeError:
        raise SegmentationError('Input syllable could not be segmented')
