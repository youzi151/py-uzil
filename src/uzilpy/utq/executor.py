from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .inst import Inst

Token = list[Any]


class Executor:
    def __init__(self, inst: Inst) -> None:
        self._inst = inst

    def search(self, search_str: str) -> dict[str, bool]:
        parsed_tokens = self.parse_search_str(search_str)
        return self._execute_tokens(parsed_tokens)

    def parse_search_str(self, search_str: str) -> list[Token]:
        tokens = self._tokenize_str(search_str)
        return self._parse_tokens(tokens)

    def _tokenize_str(self, search_str: str) -> list[Token]:
        tokens: list[Token] = []
        token_start = 0
        token_end = 0
        in_quotes = False
        operators = set(self._inst.cfg.operators)

        for idx, char in enumerate(search_str):
            is_symbol = char in "()" or char in operators
            if char in {'"', "'"}:
                in_quotes = not in_quotes
                token_end = idx + 1
            elif not in_quotes and is_symbol:
                token_content = search_str[token_start:token_end].strip()
                if token_content:
                    tokens.append(["s", token_content])
                tokens.append(["o", char])
                token_start = idx + 1
                token_end = idx + 1
            else:
                token_end = idx + 1

        token_content = search_str[token_start:token_end].strip()
        if token_content:
            tokens.append(["s", token_content])
        return tokens

    def _parse_tokens(
        self,
        tokens: list[Token],
        start_idx: int = 0,
        is_bracket: bool = False,
    ) -> list[Token] | list[Any]:
        result: list[Token] = []
        idx = start_idx
        depth = 1 if is_bracket else 0
        operators = set(self._inst.cfg.operators)

        while idx < len(tokens) and (not is_bracket or depth > 0):
            token = tokens[idx]
            kind = token[0]
            if kind == "o":
                content = token[1]
                if content == "(":
                    depth += 1
                    nested_result = self._parse_tokens(tokens, idx + 1, True)
                    result.append(nested_result[0])
                    idx = nested_result[1] - 1
                elif content == ")":
                    depth -= 1
                elif content in operators:
                    result.append(token)
            elif kind == "s":
                result.append(token)
            idx += 1

        if is_bracket:
            idx -= 1
            return [["g", result], idx]
        return result

    def _execute_tokens(self, tokens: list[Token]) -> dict[str, bool]:
        results: dict[str, bool] = {}
        current_operator = ""
        cfg = self._inst.cfg

        for token in tokens:
            kind = token[0]
            if kind == "o":
                current_operator = token[1]
                continue
            if kind == "g":
                bracket_result = self._execute_tokens(token[1])
                if not current_operator:
                    results = bracket_result
                else:
                    results = self._apply_operator(results, bracket_result, "", current_operator)
                continue
            if kind == "s":
                if not results:
                    results = self._inst.queryer.query(token[1])
                elif current_operator:
                    if current_operator == cfg.operator_fallback:
                        results = self._apply_operator(results, {}, token[1], current_operator)
                    else:
                        results = self._apply_operator(
                            results,
                            self._inst.queryer.query(token[1]),
                            "",
                            current_operator,
                        )
        return results

    def _apply_operator(
        self,
        left_results: dict[str, bool],
        right_results: dict[str, bool],
        right_str: str,
        operator: str,
    ) -> dict[str, bool]:
        cfg = self._inst.cfg
        if operator == cfg.operator_fallback:
            if left_results:
                return left_results
            if right_str:
                right_results = self._inst.queryer.query(right_str)
            return right_results
        if operator == cfg.operator_union:
            return self._union(left_results, right_results)
        if operator == cfg.operator_intersection:
            return self._intersection(left_results, right_results)
        if operator == cfg.operator_symmetric_difference:
            return self._symmetric_difference(left_results, right_results)
        return left_results

    def _union(self, left_results: dict[str, bool], right_results: dict[str, bool]) -> dict[str, bool]:
        result = dict(left_results)
        for item in right_results:
            if item not in result:
                result[item] = True
        return result

    def _intersection(self, left_results: dict[str, bool], right_results: dict[str, bool]) -> dict[str, bool]:
        result: dict[str, bool] = {}
        less, more = (
            (left_results, right_results)
            if len(left_results) <= len(right_results)
            else (right_results, left_results)
        )
        for each in less:
            if each in more:
                result[each] = True
        return result

    def _symmetric_difference(self, left: dict[str, bool], right: dict[str, bool]) -> dict[str, bool]:
        result: dict[str, bool] = {}
        seen: dict[str, bool] = {}
        for item in left:
            seen[item] = True
            result[item] = True
        for item in right:
            if item not in seen:
                seen[item] = True
                result[item] = True
            else:
                result.pop(item, None)
        return result
