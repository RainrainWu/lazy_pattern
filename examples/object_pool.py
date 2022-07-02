import asyncio

from lazy_pattern.object_pool import ObjectPool, ObjectPoolConfig


class Splitter:
    def set_up(self, digest: str) -> None:

        self.digest = digest

    def clean_up(self) -> None:

        self.digest = None

    def show_items(self):

        print(" ".join([x.strip() for x in self.digest.split(",")]))


class PoolSplitter(ObjectPool):
    pass


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


asyncio.run(main())
