from enum import Enum
from functools import reduce
from typing import Callable, Generic, Iterable, TypeVar

EnumStackLayerT = TypeVar("EnumStackLayerT", bound=Enum)
EnumStackOrderT = TypeVar("EnumStackOrderT", bound=Enum)
StackableT = TypeVar("StackableT")


class Stacker(Generic[EnumStackLayerT, EnumStackOrderT, StackableT]):
    def __init__(
        self,
        layers: dict[EnumStackLayerT, StackableT],
        orders: dict[EnumStackOrderT, tuple[EnumStackLayerT]],
        func_get_base: Callable[[], StackableT],
        func_stack: Callable[[StackableT, StackableT], StackableT],
        /,
        *,
        order_modifier: Callable[[EnumStackOrderT], str] = lambda e: e.value,
    ) -> None:

        self.__layers = layers
        self.__orders = orders
        self.__func_get_base = func_get_base
        self.__func_stack = func_stack
        self.__order_modifier = order_modifier

    def __getitem__(self, key: EnumStackOrderT) -> tuple[EnumStackLayerT]:

        return self.__orders[key]

    def __len__(self) -> int:

        return len(self.__orders)

    def __iter__(self) -> Iterable[tuple[str, StackableT]]:

        for order in self.__orders:
            yield self.__order_modifier(order), self.stack(order)

    def stack(self, order: EnumStackOrderT, /) -> StackableT:

        return reduce(
            self.__func_stack,
            [self.__func_get_base()]
            + [self.__layers[layer] for layer in self.__orders[order]],
        )
