from math import exp

import statsmodels.api as sm
from Levenshtein import distance


def ld1nn(word_sample: [str],
          nonword_sample: [str],
          word_as_reference_level=True):
    """
    Implementation of the LD1NN algorithm, used to automatically detect bias in pseudowords.

    For an experiment containing a number of stimuli, the algorithm performs the following:
        1. Compute the Levenshtein distances between the currently presented stimulus and all previously presented stimuli.
        2. Identify the previously presented stimuli that are at the k nearest distances from the current
        stimulus.
        3. Compute the probability of a word response for the given stimulus based on the relative frequency of words among the nearest neighbors.

    For more information about LD1NN, see DOI: 10.1075/ml.6.1.02keu

    Parameters:
        word_sample: a list of real words. Make sure this list contains at least all words which all unique words in nonword_sample were based on. This list must contain the same amount of items as nonword_sample.

        nonword_sample: a list of nonwords words. This list must contain the same amount of items as word_sample.

        word_as_reference_level: set the word as reference level. If set to true, the odds returned by LD1NN represent how much likelier it is for a stimulus predicted as a word to be a word than a stimulus with a nonword prediction. If set to true, the vice versa is calculated.
    .. include:: ../../documentation/evaluators/ld1nn.md
    """
    # TODO: implement a parallel processing option

    if (len(word_sample) != len(nonword_sample)):
        raise ValueError("Both sample lists need to contain the same amount of strings.")

    def get_probability(index: int):
        samples_with_distance = []
        for word in sample[0:index]:
            samples_with_distance.append((word[0], word[1], distance(word[0], sample[index][0])))
        samples_with_distance.sort(key=lambda value: value[2])
        minimum_distance = samples_with_distance[0][2]
        distribution = [sample for sample in samples_with_distance if sample[2] <= minimum_distance]
        reference_level = "word" if word_as_reference_level else "nonword"
        probability = len([sample for sample in distribution if sample[1]
                           == reference_level]) / len(distribution)

        return probability

    sample = []
    for word in word_sample:
        sample.append((word, "word"))
    for word in nonword_sample:
        sample.append((word, "nonword"))

    index = 1
    # Start from the second word
    probabilities = [0.5]

    for word in sample[1::]:
        probabilities.append(get_probability(index))
        index += 1

    if word_as_reference_level:
        probabilities = list(map(lambda x: x*-1, probabilities))

    model_data = {"probabilities": probabilities, "types": [word[1] for word in sample]}
    fit = sm.formula.glm(
        "types~(-1+probabilities)",
        family=sm.families.Binomial(), data=model_data).fit()
    return {"odds": exp(fit.params[0]), "standard_error": fit.tvalues[0], "P>|z|": fit.pvalues[0]}
