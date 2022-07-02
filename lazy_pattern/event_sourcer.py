import os
from abc import ABC, abstractmethod
from collections import Counter
from enum import Enum
from functools import lru_cache, reduce
from itertools import permutations
from operator import itemgetter, or_
from typing import Callable, Generic, Iterable, TypeVar

from lazy_pattern.error import LazyPatternError

EVENT_SOURCER_CACHE_SIZE = os.environ.get("EVENT_SOURCER_CACHE_SIZE", 1024)

EventLabelT = TypeVar("EventLabelT", bound=Enum)
SourceableT = TypeVar("SourceableT")


class EventSourcingConstraintError(LazyPatternError):
    pass


class ConstrainMode(Enum):

    MUTUALLY_EXCLUSIVE = "mutually_exclusive"
    OCCURRENCE = "occurrence"
    DEPENDENCY = "dependency"


class AbstractConstrainable(ABC, Generic[EventLabelT]):
    @abstractmethod
    def constrain(self, event_labels: tuple[EventLabelT, ...]) -> None:
        pass


class SourcingConstraint(AbstractConstrainable):

    pass


class MutuallyExclusiveConstraint(SourcingConstraint, Generic[EventLabelT]):
    def __init__(
        self,
        events_constrained: Iterable[EventLabelT],
        /,
    ) -> None:

        self.__events_constrained = set(events_constrained)

    def constrain(self, event_labels: tuple[EventLabelT, ...], /) -> None:

        catch_events = self.__events_constrained.intersection(set(event_labels))
        if len(catch_events) > 1:
            raise EventSourcingConstraintError(
                f"constrain error due to mutually exclusive events {catch_events}"
            )


class OccurrenceConstraint(SourcingConstraint, Generic[EventLabelT]):
    def __init__(
        self,
        events_constrained: Iterable[EventLabelT],
        /,
        *,
        min_times: int = 0,
        max_times: int = 1,
    ) -> None:

        self.events_constrained = set(events_constrained)

        self.min_times = min_times
        self.max_times = max_times

    def constrain(self, event_labels: tuple[EventLabelT, ...], /) -> None:

        event_counter = Counter(event_labels)
        event_occurred = self.events_constrained.intersection(set(event_labels))

        try:
            counts = itemgetter(*event_occurred)(event_counter)
            occurrence = counts if isinstance(counts, int) else sum(counts)
        except TypeError:
            occurrence = 0

        if not (self.min_times <= occurrence <= self.max_times):
            raise EventSourcingConstraintError(
                f"constrain error due to occurrence times {occurrence}"
            )


class DependencyConstraint(SourcingConstraint, Generic[EventLabelT]):
    def __init__(
        self,
        events_constrained: Iterable[EventLabelT],
        events_constraints: Iterable[EventLabelT] = set(),
        /,
    ) -> None:

        self.events_constrained = set(events_constrained)
        self.events_constraints = set(events_constraints)

        if intersection := self.events_constrained.intersection(
            self.events_constraints
        ):
            raise EventSourcingConstraintError(
                f"invalid dependency with intersection {intersection}"
            )

    def constrain(self, event_labels: tuple[EventLabelT, ...], /) -> None:

        constraints_found = None
        for event in event_labels:
            if event in self.events_constrained and constraints_found:
                raise EventSourcingConstraintError(
                    f"constrain error due to invalid dependency {constraints_found} -> {event}"
                )
            if event in self.events_constraints:
                constraints_found = event


class EventSourcer(Generic[EventLabelT, SourceableT]):
    def __init__(
        self,
        events: dict[EventLabelT, SourceableT],
        constraints: tuple[()] | tuple[AbstractConstrainable] = (),
        func_source: Callable[[SourceableT, SourceableT], SourceableT] = or_,
        /,
    ) -> None:

        self.events = events
        self.constraints = constraints
        self.func_source = func_source

    def __getitem__(self, key: EventLabelT) -> SourceableT:

        return self.events[key]

    def __len__(self) -> int:

        return len(self.events)

    def __iter__(self) -> Iterable[tuple[EventLabelT, SourceableT]]:

        for key, val in self.events.items():
            yield key, val

    def exhaustive(self) -> Iterable[tuple[tuple[EventLabelT, ...], SourceableT]]:

        for length in range(len(self.events) + 1):
            for candidate in permutations(self.events, length):
                try:
                    self.validate(candidate)
                    yield candidate, self.source(candidate)
                except EventSourcingConstraintError:
                    continue

    def validate(self, event_labels: tuple[EventLabelT, ...]) -> None:

        for constraint in self.constraints:
            constraint.constrain(event_labels)

    def source(self, event_labels: tuple[EventLabelT, ...]):

        self.validate(event_labels)

        return self._source(tuple(event_labels))

    @lru_cache(maxsize=EVENT_SOURCER_CACHE_SIZE)
    def _source(self, event_labels: tuple[EventLabelT, ...]) -> SourceableT:

        if not event_labels:
            raise EventSourcingConstraintError(
                "at least one event label should be provided"
            )

        if len(event_labels) == 1:
            return self.events[event_labels[0]]

        previous = tuple(list(event_labels)[:-1])
        return self.func_source(self._source(previous), self.events[event_labels[-1]])
