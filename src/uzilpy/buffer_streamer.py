import numpy
import asyncio
import json
import math
import struct
import time
from typing import Callable, Coroutine, Any

from .idpool import IDPool

class BufferStreamer:
	"""
	高效能非同步緩衝傳輸類別
	利用 memoryview 處理切片，並採用 struct 打包標頭與時間預算式讓步機制提升效能。
	"""

	def __init__(self, chunk_size: int = 1048576, yield_budget_ms: float = 10.0):
		"""
		:param chunk_size: 每個分段的大小 (bytes)
		:param yield_budget_ms: 每次協程讓步前的持續執行時間上限 (毫秒)
		"""
		self.chunk_size = chunk_size
		self.id_pool = IDPool(1000)
		self.yield_budget = yield_budget_ms / 1000.0 # 轉換為秒

	async def stream_data(self, data: bytes, sendfn: Callable[[bytes], Coroutine[Any, Any, None]]):
		"""
		將 bytes 資料分段送出。
		
		:param data: 原始 bytes 資料 (支援任何 bytes-like object)
		:param sendfn: 傳送 bytes 的非同步函式 (例如 websocket.send_bytes)
		"""

		# 0. 領取連線識別 ID (tid)
		tid = await self.id_pool.get_id()

		# 使用 memoryview 避免切片時產生新的 bytes 物件複本
		mv = memoryview(data)
		total_size = len(mv)
		total_seqs = math.ceil(total_size / self.chunk_size) if total_size > 0 else 0
		# print(f"total_size: {total_size}, total_seqs: {total_seqs}")

		# 1. 送出開始 Header 與總資訊 (傳輸 ID, 總長度, 總分段數)
		# 格式: [Type(1 byte)][ID(4 bytes)][TotalSize(8 bytes)][TotalSeqs(4 bytes)]
		# \x01 代表 Start Frame
		start_packet = struct.pack("<B I Q I", 0x01, tid, total_size, total_seqs)
		await sendfn(start_packet)

		try:
			offset = 0
			seq = 0
			
			# 預先計算標頭的前綴部分
			header_prefix = struct.pack("<B I", 0x02, tid)
			
			# 設定最初的讓步期限
			deadline = time.monotonic() + self.yield_budget
			
			while offset < total_size:
				# 取得當前 Chunk 的 slice (memoryview)
				chunk = mv[offset : offset + self.chunk_size]
				
				# 2. 封裝封包
				# 格式: [Type(1 byte)][ID(4 bytes)][SEQ(4 bytes)] + [Chunk Data]
				# 使用 b"".join 組合 header_prefix, seq 標頭與數據段，確保輸出為 bytes 以相容 Godot
				packet = b"".join([header_prefix, struct.pack("<I", seq), chunk])
				
				await sendfn(packet)
				
				offset += self.chunk_size
				seq += 1
				
				# 3. 時間預算式讓步：若連續執行耗時超出閾值，則讓出執行權
				if time.monotonic() > deadline:
					await asyncio.sleep(0)
					deadline = time.monotonic() + self.yield_budget

		finally:
			# 4. 歸還 ID
			await self.id_pool.release_id(tid)
	
	async def stream_bdict(self, bdict: dict, sendfn: Callable[[bytes], Coroutine[Any, Any, None]]):
		"""
		將 dict 資料 依序組成 bytes 後，透過 stream_data 送出。
		
		序列化格式:
		[項目數量 (4 bytes, uint32)]
		[Key 長度 (4 bytes, uint32)][Key 內容 (UTF-8)][Value 長度 (8 bytes, uint64)][Value 內容 (Bytes)]
		... (重複項目數量次)

		:param bdict: 原始 dict 資料 (對應 key: string, val: bytes )
		:param sendfn: 傳送 bytes 的非同步函式 (例如 websocket.send_bytes)
		"""
		
		# 1. 序列化字典
		parts = []
		# 項目數量
		parts.append(struct.pack("<I", len(bdict)))
		
		for key, val in bdict.items():
			# 處理各種資料型別並轉換為 bytes-like
			if isinstance(val, (bytes, bytearray, memoryview, numpy.ndarray)):
				pass
			elif isinstance(val, str):
				val = val.encode("utf-8")
			elif isinstance(val, int):
				val = struct.pack("<q", val)
			elif isinstance(val, float):
				val = struct.pack("<d", val)
			elif isinstance(val, bool):
				val = struct.pack("<b", 1 if val else 0)
			elif isinstance(val, (list, dict)):
				val = json.dumps(val, ensure_ascii=False).encode("utf-8")
			else:
				raise ValueError(f"Value for key '{key}' must be bytes-like, but got {type(val)}")
			
			key_bytes = key.encode("utf-8")
			val_len = val.nbytes if isinstance(val, (numpy.ndarray, memoryview)) else len(val)

			# [Key 長度][Key][Value 長度][Value]
			parts.append(struct.pack("<I", len(key_bytes)))
			parts.append(key_bytes)
			parts.append(struct.pack("<Q", val_len))
			parts.append(val)
			# print(f"key: {key}, val_bytes: {val_bytes}, val: {val}")
			
		# 2. 組合為單一 bytes 並發送
		await self.stream_data(b"".join(parts), sendfn)
