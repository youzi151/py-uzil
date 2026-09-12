---
name: uzilpy-modules
description: Describes concepts and behavior of src/uzilpy modules (BufferStreamer, IDPool, Invoker, config, UTQ). Use when explaining, documenting, or implementing against uzilpy, buffer streaming, stream_bdict, invoker loops, uzcfg, or tag query (UTQ).
---

# uzilpy modules

Package `src/uzilpy`. Public surface (`__init__.py`): `invoker`, `BufferStreamer`, `uzcfg` (`config` aliased), `utq`. `IDPool` is internal to streaming, not re-exported.

These modules are small building blocks: a framed binary stream, a bounded ID lease, a frame-timed callback loop, cached JSON config, and a tag query language. They do not form a full app runtime by themselves.

For UTQ syntax, matching, and `Inst`/`Queryer`/`Executor` behavior, see [utq.md](utq.md).

## `buffer_streamer.py` — `BufferStreamer`

High-throughput async sender for a bytes-like payload over an injected `sendfn` (typically `websocket.send_bytes`). Designed so a other peer can reassemble by reading little-endian headers, not by parsing text.

### Two layers

1. **`stream_data`** — transport: one payload, many packets, one transfer id.
2. **`stream_bdict`** — codec: flatten a dict into one payload, then call `stream_data`.

The receiver must understand both layers if the sender used `stream_bdict`.

### `stream_data` framing

Every packet is little-endian (`struct` format `<`).

| Type | Meaning | Layout |
|------|---------|--------|
| `0x01` | Start | `[u8 type][u32 tid][u64 total_size][u32 total_seqs]` |
| `0x02` | Chunk | `[u8 type][u32 tid][u32 seq]` + chunk bytes |

- `tid` comes from `IDPool(1000)` (ids `1..1000`). Concurrent in-flight streams on one `BufferStreamer` cannot exceed the pool; extra callers block on `get_id`.
- `tid` is released in `finally`, so it is reusable even if `sendfn` fails mid-stream. The peer must treat a reuse of `tid` as a new transfer, not a continuation.
- Empty payload still sends a start frame with `total_size=0`, `total_seqs=0`, then no `0x02` packets.
- Chunks are `memoryview` slices of the original buffer (no per-chunk `bytes` copy until `b"".join` builds the packet). Packet join is explicit so the result is real `bytes`, not a memoryview.
- Default `chunk_size` is 1 MiB.
- **Time-budget yield**: packing/sending can starve the event loop. After `yield_budget_ms` (default 10 ms) of wall time (`time.monotonic`), the loop `await asyncio.sleep(0)` then resets the deadline. Yield is not per-chunk; a fast `sendfn` may send many chunks before yielding.

### `stream_bdict` codec

Serializes a **flat** `dict[str, value]` into one binary blob:

```
[u32 count]
repeat count times:
  [u32 key_len][key utf-8][u64 val_len][val bytes]
```

Each **top-level** value is converted to a byte buffer independently:

| Python type | Encoding |
|-------------|----------|
| `bytes`, `bytearray`, `memoryview`, `numpy.ndarray` | raw buffer (`nbytes` for ndarray/memoryview) |
| `str` | UTF-8 |
| `int` | `<q` (int64) |
| `float` | `<d` (float64) |
| `list`, `dict` | `json.dumps(..., ensure_ascii=False)` then UTF-8 |
| other | `ValueError` |

There is no type tag on the wire. The peer must already know each key’s meaning (raw bytes vs JSON vs int64, etc.).

### Binary values must be top-level keys

`stream_bdict` only preserves raw bytes when they are **values of the outer dict**. Nested `dict` / `list` are JSON. JSON has no bytes type, so nested `bytes` cannot be transferred (typically `json.dumps` raises, or the value would be lost if coerced).

Put blobs as sibling keys; put structure in JSON-only keys:

```python
# binary intact
{"image": png_bytes, "meta": {"w": 64, "h": 64}}

# nested bytes are not transferable
{"image": {"data": png_bytes}}
{"chunks": [png_bytes]}
```

`bool` is a subclass of `int` in Python. The `int` branch runs first, so `True`/`False` are packed as `<q` (8 bytes), not the unused `<b` branch.

`stream_bdict` concatenates the whole dict before streaming. Large blobs still go through one contiguous payload plus chunked transport; they are not streamed key-by-key.

## `idpool.py` — `IDPool`

Async semaphore of integer tickets, not a generator of unique ids forever.

- Pre-fills `asyncio.Queue` with `1 .. max_id` (default 100). `0` is unused.
- `get_id` awaits if the queue is empty (backpressure).
- `release_id` puts the id back; the caller must not use it after release.
- No check that a released id was actually leased, or that it is in range.

`BufferStreamer` uses this so overlapping transfers can be demuxed on the wire without allocating unbounded ids.

## `invoker.py` — frame loop and primitives

A cooperative “loop” on asyncio: timed callbacks, queued coroutines, and a few sync primitives. Not a replacement for `asyncio.create_task` everywhere; it batches work onto a capped tick.

### `Invoker` tick (`start_loop` → `_coro_process`)

`start_loop` schedules `_coro_process` as an asyncio task. Each iteration:

1. Compute `dt` (`time.time()` delta since last tick).
2. Run due `Task` callbacks (sync `fn(task)`).
3. Drain `_to_coros` and spawn each via `_do_coro`.
4. Resolve everyone waiting on `until_next_process`.
5. Sleep the remainder of the FPS budget (`fps_cap`, default 144 Hz). If the tick overran, sleep is 0.

`close()` only sets `_is_close`. The process loop is `while True` and does **not** stop on close. `until_close` busy-yields until that flag is set. Use `close` as an app-level signal, not as loop shutdown.

`sleep()` is `asyncio.sleep(0)` (yield one scheduling point), not “wait one invoker frame”. For a frame barrier, use `until_next_process`.

### `Task`: `once` vs `interval`

| | `once(fn, delay)` | `interval(fn, interval=0)` |
|--|--|--|
| `life` | `1` | `-1` (infinite) |
| first fire | `now + delay` | `now` (due on the next tick that sees `now > target_time`) |
| after fire | `stop()` then `fn(task)` | reschedule `target_time = now + delay_time`, then `fn(task)` |

`fn` receives the `Task`. Cancel an interval by `task.stop()` inside or outside `fn`. `keep()` clears `is_stop`. `life > 1` is a finite-repeat path; public API only sets `1` or `-1`.

Callbacks run on the loop task; they must not block.

### Coroutines and threads

- `coroutine(coro, on_result=None, on_cancel=None)` queues an already-created coroutine object for the **next** tick, then `_do_coro` wraps it in `create_task` and awaits it. `on_result(res)` on success. `CancelledError` → `on_cancel()` if set. Any other exception is `print`ed and swallowed (no `on_result`).
- `to_thread` is `asyncio.to_thread` (blocking work off the loop).

### `Signal`

One-shot latch over `asyncio.Event`. `emit(result)` is ignored if already finished. `until()` waits and returns `result`. `reset()` clears result, finished flag, and the event so it can be reused.

### `Feeder`

Async iterator over an `asyncio.Queue`. `feed(data)` enqueues. `stop()` sets finished, enqueues `None`, and `on_stop.emit()`. Iteration ends only when it dequeues `None` **and** `_is_finished`. Feeding `None` before `stop()` yields `None` as a normal item.

### `inst(key="")`

Process-wide named singletons. Same key → same `Invoker`. Different keys are independent loops (each needs `start_loop`).

## `config.py` — `uzcfg`

JSON config load/save with a process-wide cache keyed by `name`. Paths are joined from module-level `root_dir` (default `"."`, cwd-relative). Missing files are skipped.

Default stack when `files` is omitted:

```
{root_dir}/config_default.json
{root_dir}/config_custom.json
{root_dir}/config_runtime.json
```

### `use(name="default", use_cached=True, files=None)`

Returns a merged dict. After every successful load, the result is stored in `_key_to_inst[name]`.

- `use_cached=True` and `name` already cached → return that dict; `files` is ignored.
- `use_cached=False` → reload from `files` (or the default stack) and overwrite the cache for `name`.
- `files=None` → the three default files above. Pass an explicit list to load only those paths.

### `save` / `load`

Both default `file_path` to `{root_dir}/config_runtime.json`.

- `save(file_path=None, cfg_dict={})` overwrites the file (`json.dump`, UTF-8, indent 4). Does **not** update the cache; reload with `use(..., use_cached=False)` if callers should see the write.
- `load(file_path=None)` reads one JSON object, or `{}` if the file is missing.

### `merge_dict(dict_a, dict_b)`

Deep merge used by `use`. Keys only in `dict_a` are **kept**. Nested dicts recurse; other types in `dict_b` replace. Files are loaded left-to-right: later files overlay earlier ones without dropping unspecified keys.

## `utq/` — `UTQ`

In-memory tag query. Named **targets** hold `Tag` lists (`scope:val`). `Inst.query` matches one tag expression; `Inst.search` combines expressions with `& | % >` and `()`.

Details (grammar, `SearchType` pass order, operators, `set_data`): [utq.md](utq.md).

## How they relate

```
uzcfg.use(...)          → static settings (cached dict)
invoker.inst(...).start_loop()  → timed/queued work
BufferStreamer.stream_bdict / stream_data(sendfn)
        → IDPool lease → framed packets → sendfn
UTQ().inst(key).set_data / .search / .query
        → Queryer match; Executor boolean-combines queries
```

`Invoker` does not drive `BufferStreamer`. Streaming is awaited in the caller’s coroutine; the invoker is optional for app ticks, delays, and background coroutines. UTQ is independent of streaming and the invoker.
