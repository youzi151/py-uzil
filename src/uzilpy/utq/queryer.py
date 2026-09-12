from __future__ import annotations

from typing import TYPE_CHECKING

from .cfg import SearchType
from .tag import Tag

if TYPE_CHECKING:
    from .inst import Inst


def _split(text: str, sep: str, allow_empty: bool, maxsplit: int = -1) -> list[str]:
    parts = text.split(sep, maxsplit) if maxsplit >= 0 else text.split(sep)
    if allow_empty:
        return parts
    return [part for part in parts if part != ""]


class Queryer:
    def __init__(self, inst: Inst) -> None:
        self._inst = inst

    def query(self, query_str: str) -> dict[str, bool]:
        query_request = self.parse_query_str(query_str)
        type_to_group_to_tags = query_request["type_to_group_to_tags"]
        result: dict[str, bool] = {}
        for target, target_tags in self._inst.target_to_data.items():
            if self.is_tags_pass(target_tags, type_to_group_to_tags):
                result[target] = True
        return result

    def get_clean_query_str(self, query_str: str) -> str:
        cfg = self._inst.cfg
        parts: list[str] = []
        last = 0
        for match in cfg.any_in_quotes_regex.finditer(query_str):
            inner_start, inner_end = match.span(1)
            parts.append(query_str[last:inner_start])
            parts.append(match.group(1).replace(" ", cfg.temp_space_char))
            last = inner_end
        parts.append(query_str[last:])
        query_str = "".join(parts)

        while True:
            matches = list(cfg.redundant_space_regex.finditer(query_str))
            pieces: list[str] = []
            last = 0
            changed = False
            for each in matches:
                raw = each.group(0)
                trimed = each.group(1)
                start, end = each.span(0)
                pieces.append(query_str[last:start])
                if raw != trimed:
                    pieces.append(trimed)
                    changed = True
                else:
                    pieces.append(raw)
                last = end
            pieces.append(query_str[last:])
            if not changed:
                break
            query_str = "".join(pieces)
        # GDScript only strips spaces after :/, so "role : tank" stays split.
        # Also drop spaces immediately before : and , so " - role : tank" is "-role:tank".
        query_str = cfg.space_before_sep_regex.sub(r"\1", query_str)
        return query_str

    def parse_query_str(self, query_str: str) -> dict:
        query_str = self.get_clean_query_str(query_str)
        cfg = self._inst.cfg
        bracket_positions: list[tuple[str, int, int, str]] = []
        for match in cfg.bracket_regex.finditer(query_str):
            start = match.start()
            prev = start - 1
            prefix = query_str[prev] if prev >= 0 else ""
            bracket_positions.append((prefix, start, match.end(), match.group(1)))

        type_to_group_to_tags: dict[int, list[list[Tag]]] = {}
        current_pos = 0
        for prefix, start, end, content in bracket_positions:
            if start > current_pos:
                before_text = query_str[current_pos:start]
                for part in _split(before_text, cfg.seperator_tag, False):
                    self._add_tag_datas_to(type_to_group_to_tags, self.parse_tags_str(part), False)
            tag_datas: list[Tag] = []
            for part in _split(content, cfg.seperator_tag, False):
                tag_datas.extend(self.parse_tags_str(prefix + part))
            self._add_tag_datas_to(type_to_group_to_tags, tag_datas, True)
            current_pos = end

        if current_pos < len(query_str):
            remaining_text = query_str[current_pos:]
            for part in _split(remaining_text, cfg.seperator_tag, False):
                self._add_tag_datas_to(type_to_group_to_tags, self.parse_tags_str(part), False)

        return {"type_to_group_to_tags": type_to_group_to_tags}

    def parse_tags_str(self, tags_str: str) -> list[Tag]:
        if not tags_str:
            return []

        cfg = self._inst.cfg
        scope = ""
        attr = ""
        search_type = SearchType.REQUIRED
        after_prefix_idx = -1

        prefix = tags_str[0]
        if prefix == cfg.prefix_without:
            if len(tags_str) > 1 and tags_str[1] == cfg.prefix_without:
                search_type = SearchType.EXCLUDE
                after_prefix_idx -= 1
            else:
                search_type = SearchType.WITHOUT
        elif prefix == cfg.prefix_tolerant:
            search_type = SearchType.TOLERANT
        elif prefix == cfg.prefix_anyone:
            search_type = SearchType.ANYONE

        if search_type != SearchType.REQUIRED:
            tags_str = tags_str[-after_prefix_idx:]

        parts = _split(tags_str, cfg.seperator_attr, True, 1)
        if len(parts) > 1:
            attr = parts[0]
            tags_str = parts[1]

        parts = _split(tags_str, cfg.seperator_scope, True)
        if len(parts) > 1:
            tags_str = parts.pop()
            scope = cfg.seperator_scope.join(parts)

        tags_str = tags_str.replace(cfg.temp_space_char, " ")
        sub_tags: list[str] = []
        if '"' in tags_str:
            for match in cfg.any_in_quotes_regex.finditer(tags_str):
                raw = match.group(0)
                inner = match.group(1)
                tags_str = tags_str.replace(raw, "")
                sub_tags.append(inner)

        for each in _split(tags_str, cfg.separator_tag_same_scope, False):
            sub_tags.append(each)

        tag_list: list[Tag] = []
        for each_tag in sub_tags:
            tag = Tag()
            val = each_tag
            if each_tag.startswith(cfg.wildcard_and_except):
                splited = _split(each_tag, cfg.wildcard_except, False)
                val = splited.pop(0) if splited else ""
                tag.wild_excepts = splited
            tag.val = val
            tag.scope = scope
            tag.attr = attr
            tag.search_type = search_type
            tag_list.append(tag)
        return tag_list

    def is_tags_pass(self, target_tags: list[Tag], type_to_group_to_tags: dict) -> bool:
        if SearchType.EXCLUDE in type_to_group_to_tags:
            for exclude_tags in type_to_group_to_tags[SearchType.EXCLUDE]:
                if not exclude_tags:
                    continue
                for tag in exclude_tags:
                    if self.has_matching_tag(target_tags, tag):
                        return False

        if SearchType.TOLERANT in type_to_group_to_tags:
            for tolerant_tags in type_to_group_to_tags[SearchType.TOLERANT]:
                if not tolerant_tags:
                    continue
                for tag in tolerant_tags:
                    if self.has_matching_tag(target_tags, tag):
                        return True

        if SearchType.WITHOUT in type_to_group_to_tags:
            for without_tags in type_to_group_to_tags[SearchType.WITHOUT]:
                if not without_tags:
                    continue
                for tag in without_tags:
                    if self.has_matching_tag(target_tags, tag):
                        return False

        if SearchType.REQUIRED in type_to_group_to_tags:
            for required_tags in type_to_group_to_tags[SearchType.REQUIRED]:
                if not required_tags:
                    continue
                for tag in required_tags:
                    if not self.has_matching_tag(target_tags, tag):
                        return False

        if SearchType.ANYONE in type_to_group_to_tags:
            for anyone_tags in type_to_group_to_tags[SearchType.ANYONE]:
                if not anyone_tags:
                    continue
                if not any(self.has_matching_tag(target_tags, tag) for tag in anyone_tags):
                    return False

        return True

    def has_matching_tag(self, tag_datas: list[Tag], request_tag_data: Tag) -> bool:
        cfg = self._inst.cfg
        for each in tag_datas:
            if request_tag_data.scope:
                if request_tag_data.scope != cfg.wildcard:
                    if each.scope != request_tag_data.scope:
                        continue
            if request_tag_data.val != cfg.wildcard:
                if each.val != request_tag_data.val:
                    continue
            elif each.val in request_tag_data.wild_excepts:
                continue
            return True
        return False

    def _add_tag_datas_to(
        self,
        type_to_group_to_tags: dict[int, list[list[Tag]]],
        tag_datas: list[Tag],
        is_group: bool,
    ) -> None:
        if is_group:
            tmp_typed_to_cur_group_tags: dict[int, list[Tag]] = {}
            for tag_data in tag_datas:
                if tag_data.search_type in tmp_typed_to_cur_group_tags:
                    tmp_typed_to_cur_group_tags[tag_data.search_type].append(tag_data)
                    continue
                group_tags = [tag_data]
                if tag_data.search_type not in type_to_group_to_tags:
                    type_to_group_to_tags[tag_data.search_type] = [[], group_tags]
                else:
                    type_to_group_to_tags[tag_data.search_type].append(group_tags)
                tmp_typed_to_cur_group_tags[tag_data.search_type] = group_tags
            return

        for tag_data in tag_datas:
            if tag_data.search_type not in type_to_group_to_tags:
                type_to_group_to_tags[tag_data.search_type] = [[tag_data]]
            else:
                type_to_group_to_tags[tag_data.search_type][0].append(tag_data)
