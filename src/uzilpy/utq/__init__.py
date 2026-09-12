from __future__ import annotations

from .cfg import Cfg, SearchType
from .executor import Executor
from .inst import Inst
from .queryer import Queryer
from .tag import Tag


class UTQ:
    """Uzil Tag Query."""

    Cfg = Cfg
    Tag = Tag
    Executor = Executor
    Queryer = Queryer
    Inst = Inst

    def __init__(self) -> None:
        self._key_to_inst: dict[str, Inst] = {}

    def inst(self, key: str = "_") -> Inst:
        if key in self._key_to_inst:
            return self._key_to_inst[key]
        inst = Inst(self)
        self._key_to_inst[key] = inst
        return inst

    def once(self, target_to_data: dict | None = None) -> Inst:
        inst = Inst(self)
        if target_to_data:
            for target, data in target_to_data.items():
                inst.set_data(target, data)
        return inst

    def tag(self, **kwargs: object) -> Tag:
        return Tag(
            scope=str(kwargs.get("scope", "")),
            val=str(kwargs.get("val", "")),
            attr=str(kwargs.get("attr", "")),
            search_type=int(kwargs.get("search_type", 0)),
        )


__all__ = ["Cfg", "Executor", "Inst", "Queryer", "SearchType", "Tag", "UTQ"]
