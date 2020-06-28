"""Tests for fuzzymatcher module."""
import pytest
import spacy
from spacy.tokens import Doc

from spaczz.fuzz.fuzzyconfig import FuzzyConfig
from spaczz.fuzz.fuzzysearch import FuzzySearch

# Global Variables
nlp = spacy.blank("en")
fs = FuzzySearch()


def test_fuzzysearch_config_contains_predefined_defaults():
    """Its config contains predefined defaults."""
    temp_fs = FuzzySearch(config="default")
    assert temp_fs._config._fuzzy_funcs


def test_fuzzysearch_uses_passed_config():
    """It uses the config passed to it."""
    fc = FuzzyConfig(empty=False)
    temp_fs = FuzzySearch(config=fc)
    assert temp_fs._config._fuzzy_funcs


def test_regexsearch_raises_error_if_config_is_not_fuzzyconfig():
    """It raises a TypeError if config is not recognized string or FuzzyConfig."""
    with pytest.raises(TypeError):
        FuzzySearch(config="Will cause error")


def test_regex_search_has_empty_config_if_empty_passed():
    """Its config is empty."""
    temp_fs = FuzzySearch(config="empty")
    assert temp_fs._config._fuzzy_funcs == {}


def test__precheck_query_raises_error_without_doc():
    """It raises TypeError if query is not a Doc."""
    with pytest.raises(TypeError):
        fs._precheck_query("not a doc")


def test__precheck_query_passes_doc():
    """It passes query through if prechecks pass."""
    query = nlp("Query string")
    precheck_query = fs._precheck_query(query)
    assert isinstance(precheck_query, Doc)


def test__precheck_query_warns_if_trimmers_affect_query():
    """It provides a UserWarning if trimmer rules will affect the query."""
    query = nlp("Query with punctuation!")
    with pytest.warns(UserWarning):
        fs._precheck_query(query, trimmers=["punct"])


def test_match_works_with_defaults():
    """Checks match is working as intended."""
    assert fs.match("spaczz", "spacy") == 73


def test_match_without_ignore_case():
    """Checks ignore_case is working."""
    assert fs.match("SPACZZ", "spaczz", ignore_case=False) == 0


def test__calc_flex_with_default():
    """It returns len(query) if set with "default"."""
    query = nlp("Test query.")
    assert fs._calc_flex(query, "default") == 3


def test__calc_flex_passes_through_valid_value():
    """It passes through a valid flex value (<= len(query))."""
    query = nlp("Test query.")
    assert fs._calc_flex(query, 1) == 1


def test__calc_flex_warns_if_flex_longer_than_query():
    """It provides UserWarning if flex > len(query)."""
    query = nlp("Test query.")
    with pytest.warns(UserWarning):
        fs._calc_flex(query, 5)


def test__calc_flex_raises_error_if_non_valid_value():
    """It raises TypeError if flex is not an int or "default"."""
    query = nlp("Test query.")
    with pytest.raises(TypeError):
        fs._calc_flex(query, None)


def test__index_max_returns_key_with_max_value():
    """It returns the earliest key with the largest value."""
    d = {1: 30, 8: 100, 9: 100}
    assert fs._index_max(d) == 8


def test__index_max_with_empty_dict_returns_none():
    """It returns an empty Dict if passed an empty Dict."""
    d = {}
    assert fs._index_max(d) is None


def test__indice_maxes_returns_n_keys_with_max_values():
    """It returns the n keys with the largest values
    in descending value order, then ascending
    key order.
    """
    d = {1: 30, 4: 50, 5: 50, 9: 100}
    assert fs._indice_maxes(d, 3) == [9, 4, 5]


def test__indice_maxes_returns_input_if_n_is_0():
    """It returns input unchanged if n is 0."""
    d = {1: 30, 4: 50, 5: 50, 9: 100}
    assert fs._indice_maxes(d, 0) == d


def test__indice_maxes_with_empty_dict_returns_empty_list():
    """It returns an empty Dict if passed an empty Dict."""
    d = {}
    assert fs._indice_maxes(d, 3) == []


def test__scan_doc_returns_matches_over_min_r1():
    """It returns all spans of len(query) in doc
    if span's fuzzy ratio with query >= min_r1.
    """
    doc = nlp.make_doc("Don't call me Sh1rley")
    query = nlp.make_doc("Shirley")
    assert fs._scan_doc(
        doc, query, fuzzy_func="simple", min_r1=50, ignore_case=True
    ) == {4: 86}


def test__scan_doc_returns_all_matches_with_no_min_r1():
    """It returns all spans of len(query) in doc if min_r1 = 0."""
    doc = nlp.make_doc("Don't call me Sh1rley")
    query = nlp.make_doc("Shirley")
    assert fs._scan_doc(
        doc, query, fuzzy_func="simple", min_r1=0, ignore_case=True
    ) == {0: 0, 1: 0, 2: 18, 3: 22, 4: 86}


def test__scan_doc_with_no_matches():
    """It returns an empty Dict if no matches >= min_r1."""
    doc = nlp.make_doc("Don't call me Sh1rley")
    query = nlp.make_doc("xenomorph")
    assert (
        fs._scan_doc(doc, query, fuzzy_func="simple", min_r1=50, ignore_case=True) == {}
    )


def test__enforce_start_trimmers_changes_start_index_based_on_trimmers():
    """It changes the span start index based on span trimmer rules."""
    doc = nlp("this starts with a stop word")
    assert fs._enforce_start_trimmers(doc, 0, 2, start_trimmers=["stop"]) == 1


def test__enforce_start_trimmers_returns_none_if_start_equals__end_after_enforcing():
    """It returns None if span start index = span end index
    after start trimmer enforcing.
    """
    doc = nlp("this starts with a stop word")
    assert fs._enforce_start_trimmers(doc, 0, 1, start_trimmers=["stop"]) is None


def test__enforce_start_trimmers_does_not_change_start_index_if_unnecessary():
    """It does not change start index if unaffected by span trimmers."""
    doc = nlp("Unnecessary to trim.")
    assert fs._enforce_start_trimmers(doc, 0, 1, start_trimmers=["stop"]) == 0


def test__enforce_start_trimmers_returns_none_if_start_runs_into_end_during_enforcing():
    """It returns None if span start index = span end index during trimmer enforcing."""
    doc = nlp("this the that")
    assert fs._enforce_start_trimmers(doc, 1, 2, start_trimmers=["stop"]) is None


def test__enforce_end_trimmers_changes_end_index_based_on_trimmers():
    """It changes the span end index based on span trimmer rules."""
    doc = nlp.make_doc("we don't want no punctuation.")
    assert fs._enforce_end_trimmers(doc, 5, 7, end_trimmers=["punct"]) == 6


def test__enforce_end_trimmers__returns_none_if_start_equals_end_after_enforcing():
    """It returns None if span start index = span end index
    after end trimmer enforcing.
    """
    doc = nlp.make_doc("we don't want no punctuation.")
    assert fs._enforce_end_trimmers(doc, 6, 7, end_trimmers=["punct"]) is None


def test__enforce_start_trimmers_does_not_change_end_index_if_unnecessary():
    """It does not change end index if unaffected by span trimmers."""
    doc = nlp.make_doc("we don't want no punctuation.")
    assert fs._enforce_end_trimmers(doc, 5, 6, end_trimmers=["punct"]) == 6


def test__enforce_trimming_rules_returns_updated_boundaries():
    """It updates the span boundaries based on trimming rules."""
    doc = nlp("The token we are looking for is: xenomorph.")
    assert fs._enforce_trimming_rules(doc, 7, 10, trimmers=["punct"]) == (8, 9)


def test__enforce_trimming_rules_returns_unchanged_boundaries_without_trimmers():
    """It does not change span boundaries without trimmers present."""
    doc = nlp("The token we are looking for is: xenomorph.")
    assert fs._enforce_trimming_rules(doc, 7, 10) == (7, 10)


def test__enforce_trimming_rules_returns_none_if_trimmers_squash_match():
    """If start index runs into end index during enforcement,
    start index will be None.
    """
    doc = nlp("The token we are looking for is: the.")
    assert fs._enforce_trimming_rules(doc, 7, 10, trimmers=["stop", "punct"]) == (
        None,
        10,
    )


def test__adjust_left_right_positions_finds_better_match():
    """It optimizes the initial match to find a better match."""
    doc = nlp.make_doc("Patient was prescribed Zithromax tablets.")
    query = nlp.make_doc("zithromax tablet")
    match_values = {3: 100}
    assert fs._adjust_left_right_positions(
        doc,
        query,
        match_values,
        pos=3,
        fuzzy_func="simple",
        min_r2=70,
        ignore_case=True,
        flex=2,
    ) == (3, 5, 97)


def test__adjust_left_right_positions_finds_better_match2():
    """It optimizes the initial match to find a better match."""
    doc = nlp.make_doc("There was a great basketball player named: Karem Abdul Jabar")
    query = nlp.make_doc("Kareem Abdul-Jabbar")
    match_values = {8: 73}  # arbitrary ratio value
    assert fs._adjust_left_right_positions(
        doc,
        query,
        match_values,
        pos=8,
        fuzzy_func="simple",
        min_r2=70,
        ignore_case=True,
        flex=4,
        trimmers=["punct"],
    ) == (8, 11, 89)


def test__adjust_left_right_positions_finds_better_match3():
    """It optimizes the initial match to find a better match."""
    doc = nlp.make_doc("There was a great basketball player named: Karem Abdul Jabar")
    query = nlp.make_doc("Kareem Abdul-Jabbar")
    match_values = {7: 73}  # arbitrary ratio value
    assert fs._adjust_left_right_positions(
        doc,
        query,
        match_values,
        pos=7,
        fuzzy_func="simple",
        min_r2=70,
        ignore_case=True,
        flex=4,
        trimmers=["punct"],
    ) == (8, 11, 89)


def test__adjust_left_right_positions_finds_better_match4():
    """It optimizes the initial match to find a better match."""
    doc = nlp.make_doc("There was a great basketball player named: Karem Abdul-Jabar")
    query = nlp.make_doc("Kareem Abdul Jabbar")
    match_values = {7: 73}  # arbitrary ratio value
    assert fs._adjust_left_right_positions(
        doc,
        query,
        match_values,
        pos=7,
        fuzzy_func="simple",
        min_r2=70,
        ignore_case=True,
        flex=4,
        trimmers=["punct"],
    ) == (8, 12, 89)


def test__adjust_left_right_positions_with_no_flex():
    """It returns the intial match when flex value = 0."""
    doc = nlp.make_doc("Patient was prescribed Zithromax tablets.")
    query = nlp.make_doc("zithromax")
    match_values = {3: 100}
    assert fs._adjust_left_right_positions(
        doc,
        query,
        match_values,
        pos=3,
        fuzzy_func="simple",
        min_r2=70,
        ignore_case=True,
        flex=0,
    ) == (3, 4, 100)


def test__adjust_left_right_positions_returns_none_due_to_trimmer_enforcing():
    """If trimmers result in no match present, returns None."""
    doc = nlp.make_doc("this that the is")
    query = nlp.make_doc("that the")
    match_values = {1: 100}
    assert (
        fs._adjust_left_right_positions(
            doc,
            query,
            match_values,
            pos=1,
            fuzzy_func="simple",
            min_r2=70,
            ignore_case=True,
            flex=2,
            trimmers=["stop"],
        )
        is None
    )


def test__adjust_left_right_positions_returns_none_bc_minr2_not_met():
    """If min_r2 is not met None is returned."""
    doc = nlp.make_doc("Patient was prescribed Zithromax capsules.")
    query = nlp.make_doc("zithromax tablet")
    match_values = {3: 100}
    assert (
        fs._adjust_left_right_positions(
            doc,
            query,
            match_values,
            pos=3,
            fuzzy_func="simple",
            min_r2=90,
            ignore_case=True,
            flex=2,
        )
        is None
    )


def test__filter_overlapping_matches_filters_correctly():
    """It only returns the first match if more than one encompass the same tokens."""
    matches = [(1, 2, 80), (1, 3, 70)]
    assert fs._filter_overlapping_matches(matches) == [(1, 2, 80)]


def test_best_match_finds_best_match():
    """It finds the single best fuzzy match that meets threshold."""
    doc = nlp("G-rant Anderson lives in TN.")
    query = nlp("Grant Andersen")
    assert fs.best_match(doc, query) == (0, 4, 90)


def test_best_match_return_none_when_no_matches():
    """It returns None if no fuzzy match meets threshold."""
    doc = nlp("G-rant Anderson lives in TN.")
    query = nlp("xenomorph")
    assert fs.best_match(doc, query) is None


def test_best_match_raises_error_without_doc():
    """Raises a Type error if doc is not a Doc object."""
    doc = "G-rant Anderson lives in TN."
    query = nlp("xenomorph")
    with pytest.raises(TypeError):
        fs.best_match(doc, query)


def test_multi_match_finds_best_matches():
    """It returns all the fuzzy matches that meet threshold.
    In order of descending match ratio, then ascending start index.
    """
    doc = nlp("chiken from Popeyes is better than chken from Chick-fil-A")
    query = nlp("chicken")
    assert fs.multi_match(doc, query, ignore_case=False) == [(0, 1, 92), (6, 7, 83)]


def test_multi_match_return_empty_list_when_no_matches():
    """It returns an empty list if no fuzzy matches meet threshold."""
    doc = nlp("G-rant Anderson lives in TN.")
    query = nlp("xenomorph")
    assert fs.multi_match(doc, query) == []


def test_multi_match_with_n_less_than_actual_matches():
    """It returns the n best fuzzy matches that meet threshold.
    In order of descending match ratio, then ascending start index.
    """
    doc = nlp("cow, cow, cow, cow")
    query = nlp("cow")
    assert fs.multi_match(doc, query, n=2) == [(0, 1, 100), (2, 3, 100)]


def test_multi_match_raises_error_without_doc():
    """It raises a TypeError if doc is not a Doc object."""
    doc = "G-rant Anderson lives in TN."
    query = nlp("xenomorph")
    with pytest.raises(TypeError):
        fs.multi_match(doc, query)
