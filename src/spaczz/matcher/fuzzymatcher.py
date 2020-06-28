"""Module for FuzzyMatcher class with an API semi-analogous to spaCy matchers."""
from __future__ import annotations

from collections import defaultdict
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)
import warnings

from spacy.tokens import Doc
from spacy.vocab import Vocab

from ..fuzz.fuzzyconfig import FuzzyConfig
from ..fuzz.fuzzysearch import FuzzySearch


class FuzzyMatcher(FuzzySearch):
    """spaCy-like matcher for finding fuzzy matches in Doc objects.

    Fuzzy matches added patterns against the Doc object it is called on.
    Accepts labeled fuzzy patterns in the form of Doc objects.

    Args:
        vocab: A spacy Vocab object.
            Purely for consistency between spaCy
            and spaczz matcher APIs for now.
            spaczz matchers are currently pure
            Python and do not share vocabulary
            with spacy pipelines.
        config: Provides the class with predefind fuzzy matching
            and span trimming functions.
            Uses the default config if "default", an empty config if "empty",
            or a custom config by passing a FuzzyConfig object.
            Default is "default".
        defaults: Keyword arguments that will
            be passed to the fuzzy matching function
            (the inherited multi_match() method).
            These arguments will become the new defaults for
            fuzzy matching in the created FuzzyMatcher instance.

    Attributes:
        name (str): Class attribute - the name of the matcher.
        defaults (Dict[str, Any]): Kwargs to be used as
            defualt fuzzy matching settings for the
            instance of FuzzyMatcher.
        _callbacks (Dict[str, Callable[[FuzzyMatcher, Doc, int, List], None]]):
            On match functions to modify Doc objects passed to the matcher.
            Can make use of the fuzzy matches identified.
        _config (FuzzyConfig): The FuzzyConfig object tied to an instance
            of FuzzyMatcher.
        _patterns (DefaultDict[str, DefaultDict[str,
            Union[List[Doc], List[Dict[str, Any]]]]]):
            Patterns added to the matcher. Contains patterns
            and kwargs that should be passed to matching function
            for each labels added.
    """

    name = "fuzzy_matcher"

    def __init__(
        self, vocab: Vocab, config: Union[str, FuzzyConfig] = "default", **defaults: Any
    ):
        super().__init__(config)
        self.defaults = defaults
        self._callbacks = {}
        self._patterns = defaultdict(lambda: defaultdict(list))

    def __call__(self, doc: Doc) -> Union[List[Tuple[str, int, int]], List]:
        """Find all sequences matching the supplied patterns in the Doc.

        Args:
            doc: The Doc object to match over.

        Returns:
            A list of (key, start, end) tuples, describing the matches.

        Example:
            >>> import spacy
            >>> from spaczz.matcher import FuzzyMatcher
            >>> nlp = spacy.blank("en")
            >>> fm = FuzzyMatcher(nlp.vocab)
            >>> doc = nlp("Ridly Scot was the director of Alien.")
            >>> fm.add("NAME", [nlp.make_doc("Ridley Scott")])
            >>> fm(doc)
            [("NAME", 0, 2)]
        """
        matches = set()
        for label, patterns in self._patterns.items():
            for pattern, kwargs in zip(patterns["patterns"], patterns["kwargs"]):
                if not kwargs:
                    kwargs = self.defaults
                matches_wo_label = self.multi_match(doc, pattern, **kwargs)
                if matches_wo_label:
                    matches_w_label = [
                        (label,) + match_wo_label[:2]
                        for match_wo_label in matches_wo_label
                    ]
                    for match in matches_w_label:
                        matches.add(match)
        matches = sorted(matches, key=lambda x: (x[1], -x[2] - x[1]))
        for i, (label, _start, _end) in enumerate(matches):
            on_match = self._callbacks.get(label)
            if on_match:
                on_match(self, doc, i, matches)
        return matches

    def __contains__(self, label: str) -> bool:
        """Whether the matcher contains patterns for a label."""
        return label in self._patterns

    def __len__(self) -> int:
        """The number of labels added to the matcher."""
        return len(self._patterns)

    @property
    def labels(self) -> Tuple[str, ...]:
        """All labels present in the matcher.

        Returns:
            The unique string labels as a tuple.

        Example:
            >>> import spacy
            >>> from spaczz.matcher import FuzzyMatcher
            >>> fm = FuzzyMatcher()
            >>> fm.add("AUTHOR", [nlp.make_doc("Kerouac")])
            >>> fm.labels
            ("AUTHOR",)
        """
        return tuple(self._patterns.keys())

    @property
    def patterns(self) -> List[Dict[str, Any]]:
        """Get all patterns and kwargs that were added to the matcher.

        Returns:
            The original patterns and kwargs,
            one dictionary for each combination.

        Example:
            >>> import spacy
            >>> from spaczz.matcher import FuzzyMatcher
            >>> fm = FuzzyMatcher()
            >>> fm.add("AUTHOR", [nlp.make_doc("Kerouac")],
                [{"case_sensitive": True}])
            >>> fm.patterns
            [
                {
                    "label": "AUTHOR",
                    "pattern": "Kerouac",
                    "type": "fuzzy",
                    "kwargs": {"case_sensitive": True}
                },
            ]
        """
        all_patterns = []
        for label, patterns in self._patterns.items():
            for pattern, kwargs in zip(patterns["patterns"], patterns["kwargs"]):
                p = {"label": label, "pattern": pattern.text, "type": "fuzzy"}
                if kwargs:
                    p["kwargs"] = kwargs
                all_patterns.append(p)
        return all_patterns

    def add(
        self,
        label: str,
        patterns: Iterable[Doc],
        kwargs: Optional[List[Dict[str, Any]]] = None,
        on_match: Optional[Callable[[FuzzyMatcher, Doc, int, List], None]] = None,
    ) -> None:
        """Add a rule to the matcher, consisting of a label and one or more patterns.

        Patterns must be a list of Doc object and if kwargs is not None,
        kwargs must be a list of dictionaries.

        Args:
            label: Name of the rule added to the matcher.
            patterns: Doc objects that will be fuzzy matched
                against the Doc object the matcher is called on.
            kwargs: Optional arguments to modify the behavior
                of the fuzzy matching. Default is None.
            on_match: Optional callback function to modify the
                Doc objec the matcher is called on after matching.
                Default is None.

        Returns:
            None

        Raises:
            TypeError: If patterns is not an iterable of Doc objects.
            TypeError: If kwargs is not an iterable dictionaries.

        Warnings:
            UserWarning: If there are more patterns than kwargs
                default fuzzy matching settings will be used
                for extra patterns.
            UserWarning: If there are more kwargs dicts than patterns,
                the extra kwargs will be ignored.

        Example:
            >>> import spacy
            >>> from spaczz.matcher import FuzzyMatcher
            >>> nlp = spacy.blank("en")
            >>> fm = FuzzyMatcher(nlp.vocab)
            >>> fm.add("SOUNDS", [nlp.make_doc("mooo")])
            >>> "SOUND" in fm
            True
        """
        if kwargs is None:
            kwargs = [{} for p in patterns]
        elif len(kwargs) < len(patterns):
            warnings.warn(
                (
                    "There are more patterns then there are kwargs.",
                    "Patterns not matched to a kwarg dict will have default settings.",
                )
            )
            kwargs.extend([{} for p in range(len(patterns) - len(kwargs))])
        elif len(kwargs) > len(patterns):
            warnings.warn(
                (
                    "There are more kwargs dicts than patterns.",
                    "The extra kwargs will be ignored.",
                )
            )
        for pattern, kwarg in zip(patterns, kwargs):
            if isinstance(pattern, Doc):
                self._patterns[label]["patterns"].append(pattern)
            else:
                raise TypeError("Patterns must be an iterable of Doc objects.")
            if isinstance(kwarg, dict):
                self._patterns[label]["kwargs"].append(kwarg)
            else:
                raise TypeError("Kwargs must be an iterable of dictionaries.")
        self._callbacks[label] = on_match

    def remove(self, label: str) -> None:
        """Remove a label and its respective patterns from the matcher.

        Args:
            label: Name of the rule added to the matcher.

        Returns:
            None

        Raises:
            ValueError: If label does not exist in the matcher.

        Example:
            >>> import spacy
            >>> from spaczz.matcher import FuzzyMatcher
            >>> nlp = spacy.blank("en")
            >>> fm = FuzzyMatcher(nlp.vocab)
            >>> fm.add("SOUND", [nlp.make_doc("mooo")])
            >>> fm.remove("SOUND")
            >>> "SOUNDS" in fm
            False
        """
        try:
            del self._patterns[label]
            del self._callbacks[label]
        except KeyError:
            raise ValueError(
                f"The label: {label} does not exist within the matcher rules."
            )

    def pipe(
        self,
        stream: Iterable[Doc],
        batch_size: int = 1000,
        return_matches: bool = False,
        as_tuples: bool = False,
    ) -> Generator[Any]:
        """Match a stream of Doc objects, yielding them in turn.

        Args:
            docs: A stream of Doc objects.
            batch_size: Number of documents to accumulate into a working set.
                Default is 1000.
            return_matches: Yield the match lists along with the docs,
                making results (doc, matches) tuples. Defualt is False.
            as_tuples: Interpret the input stream as (doc, context) tuples,
                and yield (result, context) tuples out.
                If both return_matches and as_tuples are True,
                the output will be a sequence of ((doc, matches), context) tuples.
                Default is False.

        Yields:
            Doc objects, in order.

        Example:
            >>> import spacy
            >>> from spaczz.matcher import FuzzyMatcher
            >>> fm = FuzzyMatcher()
            >>> doc_stream = (
                    nlp.make_doc("test doc1: Corvold"),
                    nlp.make_doc("test doc2: Prosh"),
                )
            >>> fm.add("DRAGON", [nlp.make_doc("Korvold"), nlp.make_doc("Prossh")])
            >>> output = fm.pipe(doc_stream, return_matches=True)
            >>> [entry[1] for entry in output]
            [[("DRAGON"), 4, 5], [("DRAGON"), 4, 5]]
        """
        if as_tuples:
            for doc, context in stream:
                matches = self(doc)
                if return_matches:
                    yield ((doc, matches), context)
                else:
                    yield (doc, context)
        else:
            for doc in stream:
                matches = self(doc)
                if return_matches:
                    yield (doc, matches)
                else:
                    yield doc
