from abc import ABC, abstractmethod
from enum import Enum
from functools import reduce
from operator import itemgetter
from typing import Callable, Counter, Dict, Generic, Iterable, Tuple, TypeVar

EventLabelT = TypeVar("EventLabelT", bound=Enum)
OrderLabelT = TypeVar("OrderLabelT", bound=Enum)
SourceableT = TypeVar("SourceableT")


class LazyPatternError(Exception):
    pass


class EventSourcingConstraintError(LazyPatternError):
    pass


class ConstrainMode(Enum):

    MUTUALLY_EXCLUSIVE = "mutually_exclusive"
    OCCURRENCE = "occurrence"
    DEPENDENCY = "dependency"


class AbstractConstrainable(ABC, Generic[EventLabelT]):
    @abstractmethod
    def constrain(self, event_labels: tuple[EventLabelT]) -> None:
        pass


class SourcingConstraint(AbstractConstrainable):

    pass


class MutuallyExclusiveConstraint(SourcingConstraint):
    def __init__(
        self,
        events_constrained: set[EventLabelT],
        /,
    ) -> None:

        self.__events_constrained = events_constrained

    def constrain(self, event_labels: tuple[EventLabelT], /) -> None:

        catch_events = self.__events_constrained.intersection(set(event_labels))
        if len(catch_events) > 1:
            raise EventSourcingConstraintError(
                f"constrain error due to mutually exclusive events {catch_events}"
            )


class OccurrenceConstraint(SourcingConstraint, Generic[EventLabelT]):
    def __init__(
        self,
        events_constrained: set[EventLabelT],
        /,
        *,
        min_times: int = 0,
        max_times: int = 1,
    ) -> None:

        self.events_constrained = events_constrained
        self.min_times = min_times
        self.max_times = max_times

    def constrain(self, event_labels: tuple[EventLabelT], /) -> None:

        event_counter = Counter(event_labels)
        event_occurred = self.events_constrained.intersection(set(event_labels))
        occurrence = sum(itemgetter(*event_occurred)(event_counter))
        if not (self.min_times < occurrence < self.max_times):
            raise EventSourcingConstraintError(
                f"constrain error due to occurrence times {occurrence}"
            )


class DependencyConstraint(SourcingConstraint, Generic[EventLabelT]):
    def __init__(
        self,
        events_constrained: set[EventLabelT],
        events_constraints: set[EventLabelT] = set(),
        /,
    ) -> None:

        if intersection := events_constrained.intersection(events_constraints):
            raise EventSourcingConstraintError(
                f"invalid dependency with intersection {intersection}"
            )

        self.events_constrained = events_constrained
        self.events_constraints = events_constraints

    def constrain(self, event_labels: tuple[EventLabelT], /) -> None:

        constraints_found = None
        for event in event_labels:
            if event in self.events_constrained and constraints_found:
                raise EventSourcingConstraintError(
                    f"constrain error due to invalid dependency {constraints_found} -> {event}"
                )
            if event in self.events_constraints:
                constraints_found = event


class EventSourcer(Generic[EventLabelT, OrderLabelT, SourceableT]):
    def __init__(
        self,
        events: dict[EventLabelT, SourceableT],
        constraints: tuple[SourcingConstraint],
        func_get_base: Callable[[], SourceableT],
        func_source: Callable[[SourceableT, SourceableT], SourceableT],
        /,
    ) -> None:

        self.events = events
        self.constraints = constraints
        self.func_get_base = func_get_base
        self.func_source = func_source

        self.registered_orders: Dict[OrderLabelT, tuple[EventLabelT]] = {}

    def __getitem__(self, key: OrderLabelT) -> tuple[EventLabelT]:

        return self.registered_orders[key]

    def __len__(self) -> int:

        return len(self.registered_orders)

    def __iter__(self) -> Iterable[tuple[OrderLabelT, SourceableT]]:

        for order in self.registered_orders:
            yield order, self.source_by_order(order)

    def register(self, order: OrderLabelT, event_labels: tuple[EventLabelT], /):

        self.registered_orders[order] = event_labels

    def source(self, event_labels: tuple[EventLabelT]):

        return reduce(
            self.func_source,
            [self.func_get_base()] + [self.events[label] for label in event_labels],
        )

    def source_by_order(self, order: OrderLabelT, /) -> SourceableT:

        return self.source(self.registered_orders[order])
