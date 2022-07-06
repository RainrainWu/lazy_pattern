import asyncio
from collections import deque

import pytest

from lazy_pattern.object_pool import (
    AbstractRecyclable,
    ObjectPool,
    ObjectPoolConfig,
    ObjectPoolOverloadError,
    ScalingPolicy,
)


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
    finally:
        loop.close()


class TestObjectPool:
    class PoolMember(AbstractRecyclable):
        def set_up(self, *args, **kwargs) -> None:
            pass

        def clean_up(self, *args, **kwargs) -> None:
            pass

    class ObjectPoolUnitTest(ObjectPool[PoolMember]):
        pass

    @pytest.mark.asyncio
    async def test_aiter(self):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                retry_interval=1,
                cool_down=0,
            )
        )

        members = deque()
        async for member in object_pool:
            members.append(member)

        assert members == object_pool.idle

    @pytest.mark.asyncio
    async def test_cool_down(self):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                retry_interval=1,
            )
        )

        async with object_pool.lease():
            await object_pool.scale(-1)
            assert object_pool.is_cooling

        await asyncio.sleep(object_pool.config.cool_down * 1.2)
        assert not object_pool.is_cooling

    @pytest.mark.asyncio
    async def test_scale_cap(self):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                desired=10,
            )
        )

        async with object_pool.lease():
            assert object_pool.size == 3

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "amount, utilization",
        [
            pytest.param(0, 0.0),
            pytest.param(1, 0.2),
            pytest.param(2, 0.4),
            pytest.param(3, 0.6),
            pytest.param(4, 0.8),
            pytest.param(5, 1.0),
        ],
    )
    async def test_utilization_fixed(self, amount, utilization):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                policy=ScalingPolicy.FIXED,
                retry_interval=0,
                cool_down=0,
            )
        )

        for _ in range(amount):
            await object_pool.fetch()

        assert object_pool.utilization == utilization

    @pytest.mark.asyncio
    async def test_utilization_fixed_error(self):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                policy=ScalingPolicy.FIXED,
                retry_interval=0,
                cool_down=0,
            )
        )

        for _ in range(object_pool.config.desired):
            await object_pool.fetch()

        with pytest.raises(ObjectPoolOverloadError):
            await object_pool.fetch()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "amount, utilization",
        [
            pytest.param(0, 0.0),
            pytest.param(1, 0.33),
            pytest.param(2, 0.67),
            pytest.param(3, 0.6),
            pytest.param(4, 0.67),
            pytest.param(5, 0.62),
            pytest.param(6, 0.67),
            pytest.param(7, 0.7),
            pytest.param(8, 0.8),
            pytest.param(9, 0.9),
            pytest.param(10, 1.0),
        ],
    )
    async def test_utilization_adaptive(self, amount, utilization):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                retry_interval=0,
                cool_down=0,
            )
        )

        for _ in range(amount):
            await object_pool.fetch()

        assert object_pool.utilization == utilization

    @pytest.mark.asyncio
    async def test_utilization_adaptive_error(self):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                retry_interval=0,
                cool_down=0,
            )
        )

        for _ in range(object_pool.config.max_size):
            await object_pool.fetch()

        with pytest.raises(ObjectPoolOverloadError):
            await object_pool.fetch()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "amount, utilization",
        [
            pytest.param(0, 0.0),
            pytest.param(1, 0.33),
            pytest.param(2, 0.67),
            pytest.param(3, 0.6),
            pytest.param(4, 0.67),
            pytest.param(5, 0.62),
            pytest.param(6, 0.67),
            pytest.param(7, 0.64),
            pytest.param(8, 0.67),
            pytest.param(9, 0.69),
            pytest.param(10, 0.67),
        ],
    )
    async def test_utilization_unlimited(self, amount, utilization):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                policy=ScalingPolicy.UNLIMITED,
                retry_interval=0,
                cool_down=0,
            )
        )

        for _ in range(amount):
            await object_pool.fetch()

        assert object_pool.utilization == utilization

    @pytest.mark.asyncio
    async def test_fetch_remand(self):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                retry_interval=1,
                cool_down=0,
            )
        )

        pool_member = await object_pool.fetch()
        assert pool_member not in object_pool.idle
        assert pool_member in object_pool.busy

        await object_pool.remand(pool_member)
        assert pool_member in object_pool.idle
        assert pool_member not in object_pool.busy

    @pytest.mark.asyncio
    async def test_lease_context(self):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                retry_interval=1,
                cool_down=0,
            )
        )

        assert object_pool.utilization == 0

        async with object_pool.lease() as leased_object:
            assert len(object_pool.busy) == 1
            assert object_pool.busy[0] == leased_object

        assert object_pool.utilization == 0

    @pytest.mark.asyncio
    async def test_project(self):

        object_pool = self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
                retry_interval=1,
                cool_down=0,
            )
        )

        assert all(await object_pool.project(lambda x: x in object_pool.idle))
        assert not any(await object_pool.project(lambda x: x in object_pool.busy))
