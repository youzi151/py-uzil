from __future__ import annotations

from .cfg import SearchType


class Tag:
    def __init__(
        self,
        scope: str = "",
        val: str = "",
        attr: str = "",
        search_type: int = 0,
        wild_excepts: list[str] | None = None,
    ) -> None:
        self.scope = scope
        self.val = val
        self.attr = attr
        self.search_type = int(search_type)
        self.wild_excepts: list[str] = list(wild_excepts or [])
        self._string_cache = ""

    def to_stored_string(self) -> str:
        if not self.val:
            return ""
        out = self.attr
        if self.scope:
            out += f"{self.scope}:"
        out += self.val
        if self.wild_excepts:
            out += "^" + "^".join(self.wild_excepts)
        return out

    def __str__(self) -> str:
        if not self._string_cache:
            self._string_cache = self._build_string()
        return self._string_cache

    def __repr__(self) -> str:
        return self.__str__()

    def _build_string(self) -> str:
        if not self.val:
            return "<invalid tag>"
        prefix = {
            -2: "--",
            -1: "-",
            0: "*",
            1: "+",
            2: "",
            SearchType.EXCLUDE: "--",
            SearchType.WITHOUT: "-",
            SearchType.TOLERANT: "*",
            SearchType.ANYONE: "+",
            SearchType.REQUIRED: "",
        }.get(self.search_type, "")
        body = f"<{prefix}{self.attr}"
        if self.scope:
            body += f"{self.scope}:"
        body += self.val
        if self.wild_excepts:
            body += "^" + "^".join(self.wild_excepts)
        return body + ">"
