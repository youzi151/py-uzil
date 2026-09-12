# uzilpy

Small Python utilities (`src/uzilpy`). They are independent building blocks, not an application runtime.

Requires Python 3.11+. MIT licensed.

## Install

```bash
uv sync
```

## Modules

| Import | Role |
|--------|------|
| `uzilpy.BufferStreamer` | Async chunked binary send (`stream_data` / `stream_bdict`) |
| `uzilpy.invoker` | Frame-capped callback loop, delayed tasks, signals |
| `uzilpy.uzcfg` | Cached JSON config merge (`config` aliased as `uzcfg`) |
| `uzilpy.utq` | Tag query (`UTQ`): store `scope:val` tags on named targets, then `query` / `search` |

`IDPool` backs `BufferStreamer` and is not re-exported.

```python
from uzilpy import BufferStreamer, invoker, uzcfg, utq
```

## Example (UTQ)

```python
from uzilpy.utq import UTQ

inst = UTQ().once()
inst.set_data("Aman", ["role:dps", "gender:male"])
inst.set_data("Cman", ["role:sup", "gender:male"])
inst.search("-role:dps gender:male")  # {"Cman": True}
```

## Tests

```bash
uv run pytest
```
