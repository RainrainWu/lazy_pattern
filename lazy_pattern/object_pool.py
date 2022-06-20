from abc import ABC, abstractmethod
from asyncio import Lock
from collections import deque
from enum import Enum
from functools import wraps
from typing import Any, Callable, Generic, Iterable, TypeVar

from pydantic import BaseModel, Field, confloat, conint

from lazy_pattern.error import LazyPatternError

PoolMemberT = TypeVar("PoolMemberT")


class ObjectPoolOverloadError(LazyPatternError):
    pass


class ScalingPolicy(Enum):

    FIXED = "FIXED"
    ADAPTIVE = "ADAPTIVE"
    UNLIMITED = "UNLIMITED"


class AbstractRecyclable(ABC):
    @abstractmethod
    def set_up(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def clean_up(self, *args, **kwargs) -> None:
        pass


class ObjectPoolConfig(BaseModel, Generic[PoolMemberT]):

    func_produce: Callable[[], PoolMemberT]

    policy: ScalingPolicy = Field(default=ScalingPolicy.ADAPTIVE)
    utilization: confloat(strict=True, ge=0, le=1) = Field(default=0.7)
    scale_cap: confloat(strict=True, ge=0, le=1) = Field(default=0.3)
    cool_down: conint(strict=True, ge=0) = Field(default=1)

    desired: conint(strict=True, ge=0) = Field(default=10)
    min_size: conint(strict=True, ge=0) = Field(default=5)
    max_size: conint(strict=True, ge=0) = Field(default=20)


class ObjectPool(Generic[PoolMemberT]):
    def __init__(self, config: ObjectPoolConfig, /) -> None:

        self.lock = Lock()
        self.idle = deque()
        self.busy = deque()
        self.config = config

        self.is_cooling = False

        self.scale(self.config.desired)

    def __len__(self) -> int:
        return self.size

    def __iter__(self) -> int:

        for member in self.idle + self.busy:
            yield member

    async def __aiter__(self) -> Iterable[PoolMemberT]:

        async with self.lock:
            for member in self.idle + self.busy:
                yield member

    @property
    def size(self) -> int:
        return len(self.idle + self.busy)

    @property
    def utilization(self) -> float:
        return self.calculate_utilization(len(self.busy), self.size)

    def async_lock(func: Callable, /) -> Any:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):

            async with self.lock:
                return await func(self, *args, **kwargs)

        return wrapper

    def regulate_factory(self, usage_delta: int) -> Callable[[Callable]]:
        def regulate(func: Callable, /) -> Any:
            @wraps(func)
            async def wrapper(self, *args, **kwargs):

                await self.scale(await self.plan(usage_delta))
                return await func(self, *args, **kwargs)

            return wrapper

        return regulate

    def calculate_utilization(self, usage: int, total: int, /) -> float:
        return round(usage / total, 2)

    @async_lock
    async def plan(self, delta: int) -> int:

        expected_usage, planned_scale = len(self.busy) + delta, 0

        while (
            self.calculate_utilization(expected_usage, self.size + planned_scale)
            >= self.config.utilization
        ):
            planned_scale += 1

        while (
            self.calculate_utilization(expected_usage, self.size + planned_scale - 1)
            >= self.config.utilization
        ):
            planned_scale -= 1

        if planned_scale > 0:
            return min(planned_scale, self.config.max_size - self.size)
        return max(planned_scale, self.config.min_size - self.size)

    @async_lock
    async def scale(self, size: int) -> None:

        if self.is_cooling or not size:
            return

        for _ in range(abs(size)):

            if size < 0:
                self.idle.popleft()

            else:
                produced = self.config.func_produce()
                produced.clean_up()
                self.idle.append(produced)


class PoolMember(AbstractRecyclable):
    def set_up(self, *args, **kwargs) -> None:
        pass

    def clean_up(self, *args, **kwargs) -> None:
        pass


x = ObjectPool[PoolMember](ObjectPoolConfig(func_produce=lambda: PoolMember()))
print(len(x))
x.scale(-3)
print(len(x))
