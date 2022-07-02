import asyncio
from abc import ABC, abstractmethod
from asyncio import Lock
from collections import deque
from contextlib import asynccontextmanager
from enum import Enum
from functools import wraps
from math import ceil, floor
from typing import Any, Callable, Generic, Iterable, TypeVar

from pydantic import BaseModel, Field, confloat, conint

from lazy_pattern.error import LazyPatternError

PoolMemberT = TypeVar("PoolMemberT")


class ObjectPoolOverloadError(LazyPatternError):
    pass


class ObjectPoolOperationError(LazyPatternError):
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
    scale_cap: confloat(strict=True, ge=0, le=1) = Field(default=0.5)
    cool_down: conint(strict=True, ge=0) = Field(default=1)

    desired: conint(strict=True, ge=0) = Field(default=5)
    min_size: conint(strict=True, ge=0) = Field(default=3)
    max_size: conint(strict=True, ge=0) = Field(default=10)

    retry_times: conint(strict=True, ge=0) = Field(default=5)
    retry_interval: conint(strict=True, ge=0) = Field(default=1)
    retry_exp: conint(strict=True, ge=0) = Field(default=2)


class ObjectPool(Generic[PoolMemberT]):
    def __init__(self, config: ObjectPoolConfig, /) -> None:

        self.lock = Lock()
        self.idle = deque()
        self.busy = deque()
        self.config = config

        self.is_cooling = False

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

    def regulate(usage_delta: int) -> Callable[[Callable], Any]:
        def regulate_wrapper(func: Callable, /) -> Any:
            @wraps(func)
            async def wrapper(self, *args, **kwargs):

                await self.scale(await self.plan(usage_delta))
                return await func(self, *args, **kwargs)

            return wrapper

        return regulate_wrapper

    def calculate_utilization(self, usage: int, total: int, /) -> float:
        if not total:
            return 0.0
        return round(usage / total, 2)

    async def prewarm(self) -> None:

        await self.scale(self.config.desired)

    async def cool_down(self) -> None:

        await asyncio.sleep(self.config.cool_down)
        self.is_cooling = False

    @async_lock
    async def plan(self, delta: int, /) -> int:

        if self.config.policy == ScalingPolicy.FIXED:
            return 0

        expected_usage, planned_scale = len(self.busy) + delta, 0

        while (
            self.calculate_utilization(expected_usage, self.size + planned_scale)
            >= self.config.utilization
        ):
            planned_scale += 1

        while (
            self.size + planned_scale > 0
            and self.calculate_utilization(
                expected_usage, self.size + planned_scale - 1
            )
            < self.config.utilization
        ):
            planned_scale -= 1

        if planned_scale > 0:
            return (
                planned_scale
                if self.config.policy == ScalingPolicy.UNLIMITED
                else min(
                    planned_scale,
                    self.config.max_size - self.size,
                    ceil(self.size * self.config.scale_cap),
                )
            )
        return max(
            planned_scale,
            self.config.min_size - self.size,
            -floor(self.size * self.config.scale_cap),
        )

    async def scale(self, size: int, /) -> None:

        if self.is_cooling or not size:
            return

        if size < 0 and self.config.cool_down:
            self.is_cooling = True
            asyncio.create_task(self.cool_down())

        for _ in range(abs(size)):

            if size < 0:
                self.idle.popleft()

            else:
                produced = self.config.func_produce()
                produced.clean_up()
                self.idle.append(produced)

    @asynccontextmanager
    async def lease(self):

        leased_object = await self.fetch()
        try:
            yield leased_object
        finally:
            await self.remand(leased_object)

    @regulate(1)
    async def fetch(self):

        retry_count, retry_interval = (0, self.config.retry_interval)
        while retry_count < self.config.retry_times:

            async with self.lock:
                if self.idle:
                    pick = self.idle.popleft()
                    self.busy.append(pick)
                    return pick

            if retry_count < self.config.retry_times - 1:
                await asyncio.sleep(retry_interval)

            retry_count += 1
            retry_interval *= self.config.retry_exp

        raise ObjectPoolOverloadError

    @regulate(-1)
    async def remand(self, pool_member: PoolMemberT, /):

        if pool_member not in self.busy:
            raise ObjectPoolOperationError

        async with self.lock:
            pool_member.clean_up()
            self.busy.remove(pool_member)
            self.idle.append(pool_member)

    async def project(self, func_project: Callable[[PoolMemberT], Any], /):

        return list(map(func_project, self.idle + self.busy))
