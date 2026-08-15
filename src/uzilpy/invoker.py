import time
import asyncio

class Task:
	"""任務"""
	
	def __init__(self):
		# 剩餘生命
		self.life = -1
		# 延遲時間
		self.delay_time = 0
		# 目標時間(實際用來比較的)
		self.target_time = 0
		# 執行內容
		self.fn = None
		# 是否停止
		self.is_stop = False
		
	def keep(self):
		"""保留"""
		self.is_stop = False
	
	def stop(self):
		"""停止"""
		self.is_stop = True

class Signal:
	"""信號"""
	
	def __init__(self):
		# 結果
		self.result = None
		# 是否完成
		self.is_finished = False
		# 事件
		self._event = asyncio.Event()
	
	def emit(self, _result = None):
		"""發送"""
		if self.is_finished:
			return
		self.result = _result
		self.is_finished = True
		self._event.set()
	
	def reset(self):
		"""重設"""
		self.result = None
		self.is_finished = False
		self._event.clear()
		
	async def until(self):
		"""直到(非同步)"""
		await self._event.wait()
		return self.result

class Feeder:
	
	def __init__(self):
		self._is_finished = False
		self._queue = asyncio.Queue()
		self.on_stop = Signal()
	
	def feed(self, data=None):
		self._queue.put_nowait(data)
		
	def stop(self):
		self._is_finished = True
		self._queue.put_nowait(None)
		self.on_stop.emit()
	
	def __aiter__(self):
		return self

	async def __anext__(self):
		# 如果佇列空了，這裡會「非同步地掛起」等待，直到有資料被 feed
		data = await self._queue.get()
		
		# 檢查是否收到停止訊號
		if data is None and self._is_finished:
			raise StopAsyncIteration
		
		return data

class Invoker:

	def __init__(self):
		# 是否關閉 #
		self._is_close = False
		# 任務列表 #
		self._tasks = list()
		# 協程列表 #
		self._to_coros = list()
		# 下次推進完畢信號 #
		self._until_next_process_signals = list()
		# 此次時間差 #
		self.dt = -1
		# 幀率限制
		self._fps_cap_sec = 1 / 144

	#== public ============
	
	def fps_cap(self, fps):
		self._fps_cap_sec = 1 / fps
	
	def once(self, fn, delay):
		"""單次任務"""
		task = Task()
		task.life = 1
		task.delay_time = delay
		task.target_time = time.time() + delay
		task.fn = fn
		self._tasks.append(task)
	
	def interval(self, fn, interval = 0):
		"""間隔任務"""
		task = Task()
		task.life = -1
		task.delay_time = interval
		task.target_time = time.time()
		task.fn = fn
		self._tasks.append(task)
	
	def coroutine(self, coro, on_result=None, on_cancel=None):
		"""加入協程"""
		to_coro = {
			"coro": coro,
			"on_result": on_result,
			"on_cancel": on_cancel,
			"task": None,
		}
		self._to_coros.append(to_coro)
		return to_coro
	
	async def to_thread(self, fn, *args, **kwargs):
		"""以執行緒啟動"""
		return await asyncio.to_thread(fn, *args, **kwargs)
	
	async def until_next_process(self):
		"""直到下次推進結束 (非同步)"""
		signal = Signal()
		self._until_next_process_signals.append(signal)
		await signal.until()
	
	def start_loop(self):
		"""開始循環"""
		asyncio.create_task(self._coro_process())
	
	def close(self):
		"""關閉"""
		self._is_close = True
	
	async def until_close(self):
		"""直到關閉"""
		while not self._is_close: await asyncio.sleep(0)

	async def sleep(self):
		"""休止0幀"""
		return await asyncio.sleep(0)

	#== private ================
	
	async def _coro_process(self):
		"""推進"""

		last_time = time.time()

		while True:
			new_time = time.time()
			self.dt = new_time - last_time
			last_time = new_time

			# 每個任務
			tasks = self._tasks.copy()
			for task in tasks:

				# 若 當前時間 超過 任務目標時間
				if new_time > task.target_time:
					# 若 已經沒有剩餘生命 則 停止任務
					if task.life == 1:
						task.stop()
					else:
						# 若 任務存在有效生命 則 遞減生命
						if task.life > 1:
							task.life -= 1
						
						# 更新 倒數(下次時間)
						task.target_time = new_time + task.delay_time
					# 執行任務
					task.fn(task)
				
				# 若 任務已經停止 則 移除
				if task.is_stop:
					_tasks.remove(task)
			
			# 每個協程
			coros = self._to_coros.copy()
			self._to_coros.clear()
			for coro in coros:
				asyncio.create_task(self._do_coro(coro))

			# 每個下次推進信號 呼叫
			signals = self._until_next_process_signals.copy()
			self._until_next_process_signals.clear()
			for each in signals:
				each.emit()
			
			processed_time = time.time() - new_time
			sleep_time = max(self._fps_cap_sec - processed_time, 0)
			
			# 等待下一輪
			await asyncio.sleep(sleep_time)
	
	async def _do_coro(self, coro):
		"""執行協程"""
		res = None
		try:
			task = asyncio.create_task(coro["coro"])
			res = await task
		except asyncio.CancelledError:
			on_cancel = coro["on_cancel"]
			if on_cancel != None:
				on_cancel()
				return
		except Exception as e:
			print(e)
			return
		on_result = coro["on_result"]
		if on_result != None:
			on_result(res)

# 實例
_key_to_inst = {}

def inst(key=""):
	"""取得實例"""
	if key in _key_to_inst:
		return _key_to_inst[key]
	one = Invoker()
	_key_to_inst[key] = one
	return one