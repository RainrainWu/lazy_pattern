import pytest

from lazy_pattern.object_pool import AbstractRecyclable, ObjectPool, ObjectPoolConfig


class TestObjectPool:
    class PoolMember(AbstractRecyclable):
        def set_up(self, *args, **kwargs) -> None:
            pass

        def clean_up(self, *args, **kwargs) -> None:
            pass

    class ObjectPoolUnitTest(ObjectPool[PoolMember]):
        pass

    @pytest.fixture(scope="class", autouse=True)
    def fixture_object_pool(self):

        yield self.ObjectPoolUnitTest(
            ObjectPoolConfig(
                func_produce=lambda: self.PoolMember(),
            )
        )

    @pytest.mark.asyncio
    async def test_fetch_remand(self, fixture_object_pool):

        pool_member = await fixture_object_pool.fetch()
        assert pool_member not in fixture_object_pool.idle
        assert pool_member in fixture_object_pool.busy

        await fixture_object_pool.remand(pool_member)
        assert pool_member in fixture_object_pool.idle
        assert pool_member not in fixture_object_pool.busy

    @pytest.mark.asyncio
    async def test_lease_context(self, fixture_object_pool):

        assert fixture_object_pool.utilization == 0

        async with fixture_object_pool.lease() as leased_object:
            assert len(fixture_object_pool.busy) == 1
            assert fixture_object_pool.busy[0] == leased_object

        assert fixture_object_pool.utilization == 0
