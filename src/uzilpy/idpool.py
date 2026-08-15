import asyncio

class IDPool:
	def __init__(self, max_id: int = 100):
		# 建立一個非同步隊列，並把可用的 ID 丟進去
		self._pool = asyncio.Queue()
		for i in range(1, max_id + 1):
			self._pool.put_nowait(i)

	async def get_id(self):
		"""領取號碼牌，如果抽屜空了會等待"""
		return await self._pool.get()

	async def release_id(self, tid: int):
		"""歸還號碼牌"""
		await self._pool.put(tid)