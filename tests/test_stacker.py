from enum import Enum
from operator import or_
from typing import Dict

import pytest

from lazy_pattern.stacker import Stacker


class EnumLayer(Enum):

    MORE_ICE = "more ice"
    LESS_ICE = "less ice"
    ICE_FREE = "ice-free"

    FULL_SUGAR = "full sugar"
    HALF_SUGAR = "half sugar"
    SUGAR_FREE = "sugar-free"

    SHORT = "short"
    TALL = "tall"
    GRANDE = "grande"


class EnumOrder(Enum):

    RECOMMEND = "recommend"
    POPULAR = "popular"


class TestStacker:
    class StackerUnitTest(Stacker[EnumLayer, EnumOrder, Dict]):
        pass

    LAYERS = {
        EnumLayer.MORE_ICE: {"ice": "more ice"},
        EnumLayer.LESS_ICE: {"ice": "less ice"},
        EnumLayer.ICE_FREE: {"ice": "ice-free"},
        EnumLayer.FULL_SUGAR: {"sugar": "full sugar"},
        EnumLayer.HALF_SUGAR: {"sugar": "half sugar"},
        EnumLayer.SUGAR_FREE: {"sugar": "sugar-free"},
        EnumLayer.SHORT: {"size": "short"},
        EnumLayer.TALL: {"size": "tall"},
        EnumLayer.GRANDE: {"size": "grande"},
    }

    ORDERS = {
        EnumOrder.RECOMMEND: [EnumLayer.LESS_ICE, EnumLayer.SUGAR_FREE, EnumLayer.TALL],
        EnumOrder.POPULAR: [EnumLayer.ICE_FREE, EnumLayer.HALF_SUGAR, EnumLayer.TALL],
    }

    RESULTS = {
        EnumOrder.RECOMMEND: {
            "ice": "less ice",
            "sugar": "sugar-free",
            "size": "tall",
        },
        EnumOrder.POPULAR: {
            "ice": "ice-free",
            "sugar": "half sugar",
            "size": "tall",
        },
    }

    @pytest.fixture(scope="class", autouse=True)
    def fixture_stacker(self):

        yield TestStacker.StackerUnitTest(
            TestStacker.LAYERS,
            TestStacker.ORDERS,
            lambda: {},
            or_,
            order_modifier=lambda e: f"coffee {e.value}",
        )

    @pytest.mark.parametrize("key", [order for order in EnumOrder])
    def test_getitem(self, key, fixture_stacker):

        assert fixture_stacker[key] == self.ORDERS[key]

    def test_len(self, fixture_stacker):

        assert len(fixture_stacker) == len(self.ORDERS)

    def test_iter(self, fixture_stacker):

        expected = {f"coffee {k.value}": v for k, v in self.RESULTS.items()}
        assert {k: v for k, v in fixture_stacker} == expected

    @pytest.mark.parametrize("order", [order for order in EnumOrder])
    def test_stack(self, order, fixture_stacker):

        assert fixture_stacker.stack(order) == self.RESULTS[order]
