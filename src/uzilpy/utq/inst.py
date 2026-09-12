from __future__ import annotations

from typing import TYPE_CHECKING

from .cfg import Cfg, SearchType
from .executor import Executor
from .queryer import Queryer
from .tag import Tag

if TYPE_CHECKING:
    from . import UTQ


class Inst:
    def __init__(self, utq: UTQ) -> None:
        self.UTQ = utq
        self.target_to_data: dict[str, list[Tag]] = {}
        self.cfg = Cfg()
        self.executor = Executor(self)
        self.queryer = Queryer(self)
        self.is_debug = False

    def clear_datas(self) -> None:
        self.target_to_data.clear()

    def set_data(self, target: str, tags_str_or_tag: str | Tag | list[str | Tag]) -> None:
        if target in self.target_to_data:
            target_tags = self.target_to_data[target]
            target_tags.clear()
        else:
            target_tags = []
            self.target_to_data[target] = target_tags

        tags = tags_str_or_tag if isinstance(tags_str_or_tag, list) else [tags_str_or_tag]
        for tag in tags:
            if isinstance(tag, Tag):
                target_tags.append(tag)
            elif isinstance(tag, str):
                query_request = self.queryer.parse_query_str(tag)
                type_to_group_to_tags = query_request["type_to_group_to_tags"]
                if SearchType.REQUIRED in type_to_group_to_tags:
                    target_tags.extend(type_to_group_to_tags[SearchType.REQUIRED][0])

    def has_data(self, target: str) -> bool:
        return target in self.target_to_data

    def get_data(self, target: str) -> list[Tag] | None:
        return self.target_to_data.get(target)

    def search(self, search_str: str) -> dict[str, bool]:
        return self.executor.search(search_str)

    def query(self, query_str: str) -> dict[str, bool]:
        return self.queryer.query(query_str)
