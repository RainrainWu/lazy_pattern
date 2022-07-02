from enum import Enum
from functools import reduce
from itertools import combinations
from operator import add, or_
from random import choice, randint, shuffle
from typing import Dict

import pytest

from lazy_pattern.event_sourcer import (
    DependencyConstraint,
    EventSourcer,
    EventSourcingConstraintError,
    MutuallyExclusiveConstraint,
    OccurrenceConstraint,
)


class EventLabel(Enum):

    MORE_ICE = "more ice"
    LESS_ICE = "less ice"
    ICE_FREE = "ice-free"

    FULL_SUGAR = "full sugar"
    HALF_SUGAR = "half sugar"
    SUGAR_FREE = "sugar-free"

    SHORT = "short"
    TALL = "tall"
    GRANDE = "grande"


class OrderLabel(Enum):

    RECOMMEND = "recommend"
    POPULAR = "popular"


class TestSourcingConstraint:

    SIZE_EVENTS = {EventLabel.SHORT, EventLabel.TALL, EventLabel.GRANDE}
    NON_SIZE_EVENTS = set(EventLabel) - SIZE_EVENTS

    @pytest.fixture(scope="class", autouse=True)
    def fixture_mutually_exclusive_constraint(self):

        yield MutuallyExclusiveConstraint(EventLabel)

    @pytest.fixture(scope="class", autouse=True)
    def fixture_occurrence_constraint(self):

        yield OccurrenceConstraint(EventLabel, min_times=1, max_times=2)

    @pytest.fixture(scope="class", autouse=True)
    def fixture_dependency_constraint(self):

        yield DependencyConstraint(self.SIZE_EVENTS, self.NON_SIZE_EVENTS)

    @pytest.mark.parametrize(
        "event_labels",
        reduce(add, [list(combinations(EventLabel, x)) for x in range(2)]),
    )
    def test_mutually_exclusive(
        self, event_labels, fixture_mutually_exclusive_constraint
    ):

        fixture_mutually_exclusive_constraint.constrain(event_labels)

    @pytest.mark.parametrize(
        "event_labels",
        reduce(add, [list(combinations(EventLabel, x)) for x in range(2, 3)]),
    )
    def test_mutually_exclusive_invalid(
        self, event_labels, fixture_mutually_exclusive_constraint
    ):

        with pytest.raises(EventSourcingConstraintError):
            fixture_mutually_exclusive_constraint.constrain(event_labels)

    @pytest.mark.parametrize(
        "event_labels",
        reduce(add, [list(combinations(EventLabel, x)) for x in range(1, 3)]),
    )
    def test_occurrence(self, event_labels, fixture_occurrence_constraint):

        fixture_occurrence_constraint.constrain(event_labels)

    @pytest.mark.parametrize(
        "event_labels",
        reduce(add, [list(combinations(EventLabel, x)) for x in {0, 3}]),
    )
    def test_occurrence_invalid(self, event_labels, fixture_occurrence_constraint):

        with pytest.raises(EventSourcingConstraintError):
            fixture_occurrence_constraint.constrain(event_labels)

    def test_dependency(self, fixture_dependency_constraint):

        size_event = choice(tuple(self.SIZE_EVENTS))

        event_labels = list(self.NON_SIZE_EVENTS)
        shuffle(event_labels)
        event_labels.insert(0, size_event)

        fixture_dependency_constraint.constrain(event_labels)

    def test_dependency_invalid(self, fixture_dependency_constraint):

        size_event = choice(tuple(self.SIZE_EVENTS))

        event_labels = list(self.NON_SIZE_EVENTS)
        shuffle(event_labels)
        event_labels.insert(randint(1, len(event_labels)), size_event)

        with pytest.raises(EventSourcingConstraintError):
            fixture_dependency_constraint.constrain(event_labels)

    def test_dependency_intersect(self):

        with pytest.raises(EventSourcingConstraintError):
            DependencyConstraint(self.SIZE_EVENTS, EventLabel)


class TestEventSourcer:
    class EventSourcerUnitTest(EventSourcer[EventLabel, Dict]):
        pass

    EVENTS = {
        EventLabel.MORE_ICE: {"ice": "more ice"},
        EventLabel.LESS_ICE: {"ice": "less ice"},
        EventLabel.ICE_FREE: {"ice": "ice-free"},
        EventLabel.FULL_SUGAR: {"sugar": "full sugar"},
        EventLabel.HALF_SUGAR: {"sugar": "half sugar"},
        EventLabel.SUGAR_FREE: {"sugar": "sugar-free"},
        EventLabel.SHORT: {"size": "short"},
        EventLabel.TALL: {"size": "tall"},
        EventLabel.GRANDE: {"size": "grande"},
    }

    ORDERS = {
        OrderLabel.RECOMMEND: [
            EventLabel.LESS_ICE,
            EventLabel.SUGAR_FREE,
            EventLabel.TALL,
        ],
        OrderLabel.POPULAR: [
            EventLabel.ICE_FREE,
            EventLabel.HALF_SUGAR,
            EventLabel.TALL,
        ],
    }

    RESULTS = {
        OrderLabel.RECOMMEND: {
            "ice": "less ice",
            "sugar": "sugar-free",
            "size": "tall",
        },
        OrderLabel.POPULAR: {
            "ice": "ice-free",
            "sugar": "half sugar",
            "size": "tall",
        },
    }

    @pytest.fixture(scope="class", autouse=True)
    def fixture_sourcer(self):

        yield self.EventSourcerUnitTest(self.EVENTS, (), or_)

    @pytest.mark.parametrize("key", [event for event in EventLabel])
    def test_getitem(self, key, fixture_sourcer):

        assert fixture_sourcer[key] == self.EVENTS[key]

    def test_len(self, fixture_sourcer):

        assert len(fixture_sourcer) == len(self.EVENTS)

    def test_iter(self, fixture_sourcer):

        expected = {k: v for k, v in self.EVENTS.items()}
        assert {k: v for k, v in fixture_sourcer} == expected

    @pytest.mark.parametrize("order", [order for order in OrderLabel])
    def test_source(self, order, fixture_sourcer):

        assert fixture_sourcer.source(self.ORDERS[order]) == self.RESULTS[order]
