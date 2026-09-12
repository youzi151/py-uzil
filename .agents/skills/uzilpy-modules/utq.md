# `utq/` — Uzil Tag Query (UTQ)

Tag query over named targets. Each target holds a list of `Tag`. A query string is parsed into typed tag groups; a search string combines queries with `& | % >` and `()`.

Import: `from uzilpy import utq` then `utq.UTQ`, or `from uzilpy.utq import UTQ, Tag, SearchType`.

## Objects

```
UTQ
  inst(key="_")     → cached Inst (same key → same instance)
  once(data?)       → throwaway Inst (optional target→tags dict)
  tag(**kwargs)     → Tag (defaults search_type=REQUIRED)

Inst
  set_data / get_data / has_data / clear_datas
  query(str)        → Queryer.query   (one tag expression)
  search(str)       → Executor.search (expressions + operators)

Queryer  parse + match
Executor tokenize + boolean combine of query results
Cfg      separators, prefixes, operators, regex
Tag      scope, val, attr, search_type, wild_excepts
```

`search` / `query` return `dict[str, bool]` keyed by **target name**. Insertion order is `target_to_data` order. Values are always `True` for hits.

## `Tag`

| Field | Role |
|-------|------|
| `scope` | Namespace (`role` in `role:tank`). Empty = ignore scope when matching. |
| `val` | Value (`tank`). `.` is wildcard. |
| `attr` | Stored prefix before `/` in `attr/scope:val`. **Not used in matching.** |
| `search_type` | How this tag participates in a query (see below). |
| `wild_excepts` | When `val` is `.`, skip target tags whose `val` is in this list. |

`to_stored_string()` rebuilds `attr` + `scope:` + `val` + `^excepts` (no search prefix). `__str__` is a debug form `<prefix attr scope:val>`.

## Query string (one `Queryer` expression)

Cleaned first: quoted `"..."` keep inner spaces; other spaces after `+ - ^ * : ,` and spaces before `: ,` are stripped. `" - role : tank"` → `-role:tank`.

### Tag grammar

```
[prefix][attr/][scope:]val[,val...]
```

| Prefix | `SearchType` | Meaning when matching a target |
|--------|--------------|--------------------------------|
| (none) | `REQUIRED` (4) | Target must have this tag |
| `-` | `WITHOUT` (1) | Fail if target has this tag |
| `--` | `EXCLUDE` (0) | Fail if target has this tag (checked first) |
| `*` | `TOLERANT` (2) | If target has this tag, **pass immediately** |
| `+` | `ANYONE` (3) | Within a group, at least one must match |

Space-separated tags are separate clauses. Comma-separated `val`s share the same scope/prefix: `role:sup,tank` → two tags `role:sup` and `role:tank`.

`[a b]` is a **group**. The character immediately before `[` (if any) is prepended to each inner part: `+[類型:劍, 斧]` → `+類型:劍` and `+斧`. Ungrouped tags go in slot `0` of that type; each `[...]` appends another group.

Quotes: `"ice frost"` is one `val` (spaces restored after clean).

Wildcard: `屬性:.` matches any tag in that scope. `屬性:.^火` is wildcard except `val == "火"`.

### Match pass order (`is_tags_pass`)

1. **EXCLUDE** — any match → fail
2. **TOLERANT** — any match → **success** (skips remaining types)
3. **WITHOUT** — any match → fail
4. **REQUIRED** — every tag in every non-empty group must match
5. **ANYONE** — each non-empty group needs ≥1 matching tag
6. otherwise pass (empty query matches every target)

`has_matching_tag`: skip if request `scope` is set and not `.` and differs; skip if request `val` is not `.` and differs; skip if request `val` is `.` and target `val` is in `wild_excepts`. **`attr` is ignored.** Empty request scope matches any scope.

## Search string (`Executor`)

Tokenize on `() & % | >` outside quotes. Adjacent text with no operator is **one** query token (`+` is a tag prefix, not an operator).

| Op | Behavior |
|----|----------|
| (first token / after `(`) | `queryer.query(text)` |
| `\|` | union of target-name keys |
| `&` | intersection |
| `%` | symmetric difference |
| `>` | if left dict is non-empty, keep left; else query the right string |

`>` does not query the right side unless the left result is empty.

Parentheses recurse as a nested execute, then combine with the current operator. Unbalanced `(` / `)` → `search` returns `{}` (no exception). Nested parse that never sees `)` must not rewind onto the opening `(`.

No operator precedence: `A | B & C` is left-folded `(A|B) & C`.

An empty left-hand set is still a set. `role:missing & role:tank` stays `{}` (do not treat `{}` as “no query yet”). Leading `& role:tank` is also `{}`. `|` / `%` with empty left look like the right side; `>` with empty left takes the right side.

`search("")` → no tokens → `{}`. `query("")` → no constraints → every target. Apps that want “empty q means all” must special-case that themselves.

Juxtaposition of two query tokens **without** an operator: the second `"s"` token is ignored once a left-hand set exists. Use `&` for AND of two expressions.

## `set_data`

Replaces that target’s list. Accepts `str`, `Tag`, or a list of those.

String values are parsed with `parse_query_str`. **Only `REQUIRED` tags are stored** (`type_to_group_to_tags[REQUIRED][0]`). Prefixes like `-role:dps` in stored data are dropped. Use `Tag(...)` objects to store non-required types (usually unnecessary; prefixes belong on the query).

`UTQ.once({target: data, ...})` calls `set_data` for each pair.

## Quirks

- `Cfg.separator_tag_same_scope` vs `seperator_*` spelling is as in code.
- `attr_conflict` `!`, `attr_required` `@`, `attr_hidden` `#` are stored/config only; `has_matching_tag` does not interpret them (external use).
- Quote toggling in the executor treats `"` and `'` as the same in/out flag (mixed quotes can mis-tokenize).
- Query clean uses match spans so a quoted inner is not `str.replace`d elsewhere in the string.
