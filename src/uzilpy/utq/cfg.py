from __future__ import annotations

import re
from enum import IntEnum


class SearchType(IntEnum):
    EXCLUDE = 0
    WITHOUT = 1
    TOLERANT = 2
    ANYONE = 3
    REQUIRED = 4


class Cfg:
    separator_tag_same_scope = ","
    seperator_tag = " "
    seperator_scope = ":"
    seperator_attr = "/"

    operator_intersection = "&"
    operator_symmetric_difference = "%"
    operator_union = "|"
    operator_fallback = ">"

    prefix_without = "-"
    prefix_anyone = "+"
    prefix_tolerant = "*"

    attr_conflict = "!"
    attr_required = "@"
    attr_hidden = "#"

    wildcard = "."
    wildcard_except = "^"

    default_group = "default"
    temp_space_char = "\ufffe"

    tag_string_group_regex_pattern = r"[^,\"]+"
    any_in_quotes_regex_pattern = r"\"([^\"]*)\""
    redundant_space_regex_pattern = r"([+\-^\*:,\ ]) *"
    space_before_sep_regex_pattern = r" +([:,])"
    bracket_regex_pattern = r"\[(.*?)\]"

    def __init__(self) -> None:
        self.operators = [
            self.operator_intersection,
            self.operator_symmetric_difference,
            self.operator_union,
            self.operator_fallback,
        ]
        self.wildcard_and_except = self.wildcard + self.wildcard_except
        self.compile_regex()

    def compile_regex(self) -> None:
        self.tag_string_group_regex = re.compile(self.tag_string_group_regex_pattern)
        self.any_in_quotes_regex = re.compile(self.any_in_quotes_regex_pattern)
        self.redundant_space_regex = re.compile(self.redundant_space_regex_pattern)
        self.space_before_sep_regex = re.compile(self.space_before_sep_regex_pattern)
        self.bracket_regex = re.compile(self.bracket_regex_pattern)
