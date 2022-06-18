# Lazy Patterns
Laziness makes outstanding software engineers, I will appreciate you if you donate me your implementation of useful design patterns.

## Overview

### Event Sourcer
1. Define your events
```python
class EventLabel(Enum):

    MORE_ICE = "more ice"
    LESS_ICE = "less ice"
    ICE_FREE = "ice-free"

    FULL_SUGAR = "full sugar"
    HALF_SUGAR = "half sugar"
    SUGAR_FREE = "sugar-free"
```

2. And the corresponding operations.
```python
EVENTS = {
    EventLabel.MORE_ICE: {"ice": "more ice"},
    EventLabel.LESS_ICE: {"ice": "less ice"},
    EventLabel.ICE_FREE: {"ice": "ice-free"},
    EventLabel.FULL_SUGAR: {"sugar": "full sugar"},
    EventLabel.HALF_SUGAR: {"sugar": "half sugar"},
    EventLabel.SUGAR_FREE: {"sugar": "sugar-free"},
}
```

3. Now source a cup of coffee for yourself!
```python
from operator import or_

sourcer = EventSourcer[EventLabel, dict](LAYERS)
sourcer.source((EventLabel.SUGAR_FREE, EventLabel.ICE_FREE))
```

4. And of course you can sort out all possibilities.
```python
for order, result in source.exhaustive():
    print(f"[{order}]\n{result}")
```

5. Or even filter out unreasonable recipes via constraints!
```python
CONSTRAINTS= {
    MutuallyExclusiveConstraint[EventLabel](
        {EventLabel.FULL_SUGAR, EventLabel.HALF_SUGAR, EventLabel.SUGAR_FREE},
    ),
    MutuallyExclusiveConstraint[EventLabel](
        {EventLabel.MORE_ICE, EventLabel.LESS_ICE, EventLabel.ICE_FREE},
    ),
}

sourcer = EventSourcer(LAYERS, CONSTRAINTS)
```