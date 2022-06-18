from enum import Enum

from lazy_pattern.event_sourcer import (
    DependencyConstraint,
    EventSourcer,
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


LAYERS = {
    EventLabel.SHORT: {"size": "short"},
    EventLabel.TALL: {"size": "tall"},
    EventLabel.GRANDE: {"size": "grande"},
    EventLabel.FULL_SUGAR: {"sugar": "full sugar"},
    EventLabel.HALF_SUGAR: {"sugar": "half sugar"},
    EventLabel.SUGAR_FREE: {"sugar": "sugar-free"},
    EventLabel.MORE_ICE: {"ice": "more ice"},
    EventLabel.LESS_ICE: {"ice": "less ice"},
    EventLabel.ICE_FREE: {"ice": "ice-free"},
}

CONSTRAINTS = (
    OccurrenceConstraint[EventLabel](
        {EventLabel.SHORT, EventLabel.TALL, EventLabel.GRANDE},
    ),
    OccurrenceConstraint[EventLabel](
        {EventLabel.FULL_SUGAR, EventLabel.HALF_SUGAR, EventLabel.SUGAR_FREE},
        min_times=1,
    ),
    OccurrenceConstraint[EventLabel](
        {EventLabel.MORE_ICE, EventLabel.LESS_ICE, EventLabel.ICE_FREE},
        min_times=1,
    ),
    MutuallyExclusiveConstraint[EventLabel](
        {EventLabel.SHORT, EventLabel.TALL, EventLabel.GRANDE},
    ),
    MutuallyExclusiveConstraint[EventLabel](
        {EventLabel.FULL_SUGAR, EventLabel.HALF_SUGAR, EventLabel.SUGAR_FREE},
    ),
    MutuallyExclusiveConstraint[EventLabel](
        {EventLabel.MORE_ICE, EventLabel.LESS_ICE, EventLabel.ICE_FREE},
    ),
    DependencyConstraint[EventLabel](
        {EventLabel.SHORT, EventLabel.TALL, EventLabel.GRANDE},
        {EventLabel.FULL_SUGAR, EventLabel.HALF_SUGAR, EventLabel.SUGAR_FREE},
    ),
    DependencyConstraint[EventLabel](
        {EventLabel.FULL_SUGAR, EventLabel.HALF_SUGAR, EventLabel.SUGAR_FREE},
        {EventLabel.MORE_ICE, EventLabel.LESS_ICE, EventLabel.ICE_FREE},
    ),
)


class EventSourcerExample(EventSourcer[EventLabel, dict]):

    pass


sourcer = EventSourcerExample(LAYERS, CONSTRAINTS)
for order, result in sourcer.exhaustive():
    print(f"[{order}]\n{result}")
