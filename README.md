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

### Object Pool

1. Implement the abstract methods on your class
.
```python
class Splitter(AbstractRecyclable):
    def set_up(self, digest: str) -> None:

        self.digest = digest

    def clean_up(self) -> None:

        self.digest = None

    def show_items(self):

        print(" ".join([x.strip() for x in self.digest.split(",")]))
```

2. Inherit from the base object pool.
```python
class PoolSplitter(ObjectPool):
    pass
```

3. Prewarm your object pool and enjoy the managed instances!
```python
async def main():

    pool_splitter = PoolSplitter(ObjectPoolConfig(func_produce=lambda: Splitter()))
    await pool_splitter.prewarm()

    splitter = await pool_splitter.fetch()
    splitter.set_up("hello, world")
    splitter.show_items()
    await pool_splitter.remand(splitter)

    async with pool_splitter.lease() as splitter:
        splitter.set_up("hello, world, again")
        splitter.show_items()
```