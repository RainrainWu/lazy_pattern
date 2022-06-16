from enum import Enum
from operator import or_
from typing import Dict

import pytest

from lazy_pattern.event_sourcer import EventSourcer


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


class TestEventSourcer:
    class EventSourceUnitTest(EventSourcer[EventLabel, OrderLabel, Dict]):
        pass

    LAYERS = {
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

        event_sourcer = self.EventSourceUnitTest(self.LAYERS, (), lambda: {}, or_)
        for order, event_labels in self.ORDERS.items():
            event_sourcer.register(order, event_labels)

        yield event_sourcer

    @pytest.mark.parametrize("key", [order for order in OrderLabel])
    def test_getitem(self, key, fixture_sourcer):

        assert fixture_sourcer[key] == self.ORDERS[key]

    def test_len(self, fixture_sourcer):

        assert len(fixture_sourcer) == len(self.ORDERS)

    def test_iter(self, fixture_sourcer):

        expected = {k: v for k, v in self.RESULTS.items()}
        assert {k: v for k, v in fixture_sourcer} == expected

    @pytest.mark.parametrize("order", [order for order in OrderLabel])
    def test_source(self, order, fixture_sourcer):

        assert fixture_sourcer.source_by_order(order) == self.RESULTS[order]
