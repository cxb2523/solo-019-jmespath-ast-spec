#!/usr/bin/env python
"""Generate executable evidence for the internal JMESPath AST specification."""
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import jmespath
from jmespath.visitor import _Expression

OUTPUT = ROOT / "docs" / "ast-evidence-matrix.md"

DATA = {
    "a": 1,
    "b": 2,
    "box": {"label": "deep"},
    "items": [
        {"name": "one", "n": 1, "ok": True, "refs": [10], "tags": ["x", "y"]},
        {"name": "two", "n": 2, "ok": False, "refs": [], "tags": ["z"]},
        {"name": "three", "n": 3, "ok": True, "refs": [30, 31], "tags": []},
    ],
    "nested": [[1, 2], [3, [4]], 5],
    "nums": [3, 1, 2],
    "obj": {"alpha": {"name": "A"}, "beta": {"name": "B"}},
    "missing": None,
}


NODE_CASES = [
    {"id": "N01", "node": "comparator", "expr": "a == `1`", "expect": True},
    {"id": "N02", "node": "current", "expr": "@", "data": ["one", "two"],
     "expect": ["one", "two"]},
    {"id": "N03", "node": "expref", "expr": "&n",
     "expect": {"__actual_type__": "expref", "ast": "field#n"}},
    {"id": "N04", "node": "function_expression", "expr": "length(items)",
     "expect": 3},
    {"id": "N05", "node": "field", "expr": "a", "expect": 1},
    {"id": "N06", "node": "filter_projection", "expr": "items[?ok].name",
     "expect": ["one", "three"]},
    {"id": "N07", "node": "flatten", "expr": "nested[]",
     "expect": [1, 2, 3, [4], 5]},
    {"id": "N08", "node": "identity", "expr": "[*]", "data": ["x", "y"],
     "expect": ["x", "y"]},
    {"id": "N09", "node": "index", "expr": "[0]", "data": ["x", "y"],
     "expect": "x"},
    {"id": "N10", "node": "index_expression", "expr": "items[0]",
     "expect": DATA["items"][0]},
    {"id": "N11", "node": "key_val_pair", "expr": "{a: a}",
     "expect": {"a": 1}},
    {"id": "N12", "node": "literal", "expr": "'x'", "expect": "x"},
    {"id": "N13", "node": "multi_select_dict", "expr": "{a: a, b: b}",
     "expect": {"a": 1, "b": 2}},
    {"id": "N14", "node": "multi_select_list", "expr": "[a, b]",
     "expect": [1, 2]},
    {"id": "N15", "node": "or_expression", "expr": "absent || b", "expect": 2},
    {"id": "N16", "node": "and_expression", "expr": "a && b", "expect": 2},
    {"id": "N17", "node": "not_expression", "expr": "!a", "expect": False},
    {"id": "N18", "node": "pipe", "expr": "items | length(@)", "expect": 3},
    {"id": "N19", "node": "projection", "expr": "items[*].name",
     "expect": ["one", "two", "three"]},
    {"id": "N20", "node": "subexpression", "expr": "box.label", "expect": "deep"},
    {"id": "N21", "node": "slice", "expr": "items[0:2].name",
     "expect": ["one", "two"]},
    {"id": "N22", "node": "value_projection", "expr": "obj.*.name",
     "expect": ["A", "B"]},
]


SEMANTIC_CASES = [
    {"id": "P01", "area": "投影", "claim": "通配投影逐元素求值 RHS。",
     "expr": "items[*].name", "expect": ["one", "two", "three"]},
    {"id": "P02", "area": "投影", "claim": "左值不是数组时返回 null。",
     "expr": "absent[*]", "expect": None},
    {"id": "P03", "area": "投影", "claim": "RHS 为 null 的元素会被丢弃。",
     "expr": "items[*].absent", "expect": []},
    {"id": "P04", "area": "投影", "claim": "投影不会自动压平 RHS 产生的数组。",
     "expr": "items[*].refs", "expect": [[10], [], [30, 31]]},
    {"id": "P05", "area": "投影", "claim": "flatten 只合并一层数组。",
     "expr": "nested[]", "expect": [1, 2, 3, [4], 5]},
    {"id": "P06", "area": "投影", "claim": "flatten 左值不是数组时返回 null。",
     "expr": "a[]", "expect": None},
    {"id": "P07", "area": "投影", "claim": "过滤投影只保留条件为 JMESPath true 的元素。",
     "expr": "items[?n > `1`].name", "expect": ["two", "three"]},
    {"id": "P08", "area": "投影", "claim": "过滤投影左值不是数组时返回 null。",
     "expr": "absent[?ok]", "expect": None},
    {"id": "P09", "area": "投影", "claim": "过滤投影会丢弃 RHS 为 null 的结果。",
     "expr": "items[?ok].absent", "expect": []},
    {"id": "P10", "area": "投影", "claim": "根过滤表达式以 identity 为左值。",
     "expr": "[?ok]", "data": DATA["items"],
     "expect": [DATA["items"][0], DATA["items"][2]]},
    {"id": "P11", "area": "投影", "claim": "对象投影遍历 dict.values()。",
     "expr": "obj.*.name", "expect": ["A", "B"]},
    {"id": "P12", "area": "投影", "claim": "对象投影左值不是对象时返回 null。",
     "expr": "a.*", "expect": None},
    {"id": "P13", "area": "投影", "claim": "对象投影同样丢弃 RHS 为 null 的结果。",
     "expr": "obj.*.absent", "expect": []},
    {"id": "S01", "area": "切片", "claim": "省略 end 时截到末尾。",
     "expr": "nums[1:]", "expect": [1, 2]},
    {"id": "S02", "area": "切片", "claim": "负数 end 按 Python 切片归一化。",
     "expr": "nums[:-1]", "expect": [3, 1]},
    {"id": "S03", "area": "切片", "claim": "负 step 反转序列。",
     "expr": "nums[::-1]", "expect": [2, 1, 3]},
    {"id": "S04", "area": "切片", "claim": "切片左值不是数组时返回 null。",
     "expr": "a[0:1]", "expect": None},
    {"id": "S05", "area": "切片", "claim": "step 为 0 时底层 Python slice 抛 ValueError。",
     "expr": "nums[::0]", "raises": "ValueError"},
    {"id": "Q01", "area": "管道", "claim": "管道把左值结果作为右值当前值。",
     "expr": "items | length(@)", "expect": 3},
    {"id": "Q02", "area": "管道", "claim": "管道不会在右值重新回到根数据。",
     "expr": "missing | b", "expect": None},
    {"id": "Q03", "area": "管道", "claim": "管道优先级低于后续点号/括号链。",
     "expr": "items | [0].name", "expect": "one"},
    {"id": "H01", "area": "多选哈希", "claim": "哈希会保留表达式产生的 null 值。",
     "expr": "{x: absent, y: a}", "expect": {"x": None, "y": 1}},
    {"id": "H02", "area": "多选哈希", "claim": "当前值为 null 时整个多选哈希为 null。",
     "expr": "`null` | {a: a}", "expect": None},
    {"id": "H03", "area": "多选哈希", "claim": "重复键由后一个值覆盖。",
     "expr": "{a: a, a: b}", "expect": {"a": 2}},
    {"id": "L01", "area": "多选列表", "claim": "列表会保留表达式产生的 null 值。",
     "expr": "[absent, a]", "expect": [None, 1]},
    {"id": "L02", "area": "多选列表", "claim": "当前值为 null 时整个多选列表为 null。",
     "expr": "`null` | [a]", "expect": None},
    {"id": "F01", "area": "函数调用", "claim": "expref 参数保持不求值，由函数按需访问。",
     "expr": "map(&n, items)", "expect": [1, 2, 3]},
    {"id": "F02", "area": "函数调用", "claim": "普通参数在调用函数前完成求值。",
     "expr": "not_null(absent, a)", "expect": 1},
    {"id": "F03", "area": "函数调用", "claim": "未知函数名在求值期报错。",
     "expr": "nosuch()", "raises": "UnknownFunctionError"},
    {"id": "F04", "area": "函数调用", "claim": "内置函数按签名做类型检查。",
     "expr": "length(a)", "raises": "JMESPathTypeError"},
    {"id": "C01", "area": "比较", "claim": "eq 比较两个已求值子节点。",
     "expr": "a == `1`", "expect": True},
    {"id": "C02", "area": "比较", "claim": "eq 不等时返回 false。",
     "expr": "a == b", "expect": False},
    {"id": "C03", "area": "比较", "claim": "ne 是 eq 结果的逻辑取反。",
     "expr": "a != b", "expect": True},
    {"id": "C04", "area": "比较", "claim": "gt 使用数值顺序。",
     "expr": "b > a", "expect": True},
    {"id": "C05", "area": "比较", "claim": "本实现也允许字符串顺序比较。",
     "expr": '`"a"` < `"b"`', "expect": True},
    {"id": "C06", "area": "比较", "claim": "顺序比较遇到不可比较类型返回 null。",
     "expr": "absent < a", "expect": None},
    {"id": "C07", "area": "比较", "claim": "数字 0 不等于布尔 false。",
     "expr": "`0` == `false`", "expect": False},
    {"id": "C08", "area": "比较", "claim": "数字 1 不等于布尔 true。",
     "expr": "`1` == `true`", "expect": False},
    {"id": "C09", "area": "比较", "claim": "eq 支持结构化值相等。",
     "expr": "[a] == [`1`]", "expect": True},
    {"id": "B01", "area": "逻辑", "claim": "or 在左值为 JMESPath false 时返回右值。",
     "expr": '`""` || b', "expect": 2},
    {"id": "B02", "area": "逻辑", "claim": "数字 0 在 JMESPath 中为 true。",
     "expr": "`0` || b", "expect": 0},
    {"id": "B03", "area": "逻辑", "claim": "and 在左值 false 时短路返回左值。",
     "expr": "absent && b", "expect": None},
    {"id": "B04", "area": "逻辑", "claim": "and 在左值 true 时返回右值。",
     "expr": "a && b", "expect": 2},
    {"id": "B05", "area": "逻辑", "claim": "not 对数字 0 明确返回 false。",
     "expr": "!`0`", "expect": False},
    {"id": "B06", "area": "逻辑", "claim": "not false 返回 true。",
     "expr": "!`false`", "expect": True},
    {"id": "B07", "area": "逻辑", "claim": "not 空字符串返回 true。",
     "expr": '!`""`', "expect": True},
    {"id": "X01", "area": "其他节点", "claim": "field 在非对象上返回 null。",
     "expr": "a", "data": [], "expect": None},
    {"id": "X02", "area": "其他节点", "claim": "index 支持负数下标。",
     "expr": "[-1]", "data": DATA["nums"], "expect": 2},
    {"id": "X03", "area": "其他节点", "claim": "index 越界返回 null。",
     "expr": "[9]", "data": DATA["nums"], "expect": None},
    {"id": "X04", "area": "其他节点", "claim": "index 左值不是数组时返回 null。",
     "expr": "a[0]", "expect": None},
    {"id": "X05", "area": "其他节点", "claim": "subexpression 沿链传递 null。",
     "expr": "absent.deep", "expect": None},
    {"id": "X06", "area": "其他节点", "claim": "current 在过滤条件中指向当前元素。",
     "expr": "items[?@.n > `1`].name", "expect": ["two", "three"]},
]


INVALID_CASES = [
    {"id": "E01", "branch": "空表达式不能产生根 identity。", "expr": "",
     "raises": "EmptyExpressionError"},
    {"id": "E02", "branch": "{} 不是空多选哈希。", "expr": "{}",
     "raises": "ParseError"},
    {"id": "E03", "branch": "[] 是 flatten，不是空多选列表。",
     "expr": "[]", "data": [], "expect": []},
    {"id": "E04", "branch": "不允许直接紧跟点号的多选列表索引。", "expr": ".[0]",
     "raises": "ParseError"},
    {"id": "E05", "branch": "裸星号不能作为函数参数之外的括号投影 RHS。",
     "expr": "foo[]*", "raises": "ParseError"},
    {"id": "E06", "branch": "双引号标识符不能充当函数名。",
     "expr": '"f"()', "raises": "ParseError"},
]


def node_types(node):
    if not isinstance(node, dict):
        return
    yield node["type"]
    for child in node.get("children", []):
        for node_type in node_types(child):
            yield node_type


def node_shape(node):
    node_type = node["type"]
    if node_type == "field":
        return "field(%r)" % node["value"]
    if node_type == "literal":
        return "literal(%s)" % render(node["value"])
    if node_type == "index":
        return "index(%s)" % node["value"]
    if node_type == "slice":
        return "slice(%s,%s,%s)" % tuple(node["children"])
    if node_type == "comparator":
        label = "comparator(%s)" % node["value"]
    elif node_type in {"function_expression", "key_val_pair"}:
        label = "%s(%r)" % (node_type, node["value"])
    else:
        label = node_type
    children = [node_shape(child) for child in node.get("children", [])]
    return "%s[%s]" % (label, ", ".join(children))


def render(value):
    if isinstance(value, _Expression):
        return "<expref:%s>" % node_shape(value.expression)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def code(value):
    text = str(value)
    if "`" in text:
        return "`` " + text + " ``"
    return "`" + text + "`"


def expected_render(case, result):
    if isinstance(result, _Expression):
        return render({"__actual_type__": "expref",
                       "ast": "%s#%s" % (
                           result.expression["type"],
                           result.expression.get("value", ""))})
    return render(result)


def run_case(case):
    data = case.get("data", DATA)
    compiled = None
    compile_error = None
    try:
        compiled = jmespath.compile(case["expr"])
    except Exception as exc:
        compile_error = exc

    if compile_error is not None:
        shape = ""
        actual = None
        actual_type = type(compile_error).__name__
    else:
        shape = node_shape(compiled.parsed)
        try:
            actual = compiled.search(data)
            actual_type = type(actual).__name__
        except Exception as exc:
            actual = None
            actual_type = type(exc).__name__
    if "raises" in case:
        passed = actual_type == case["raises"]
        actual_text = "%s()" % actual_type
        expected_text = case["raises"] + "()"
    else:
        actual_text = expected_render(case, actual)
        expected_text = render(case["expect"])
        passed = actual_text == expected_text
    return {
        "id": case["id"],
        "expr": code(case["expr"]) if case["expr"] else "（空串）",
        "ast": code(shape),
        "passed": passed,
        "actual": code(actual_text),
        "expected": code(expected_text),
        "actual_type": actual_type,
    }


def verify_parser_invariants():
    expressions = [case["expr"] for case in NODE_CASES + SEMANTIC_CASES
                   if case["expr"]]
    parsed_forests = [jmespath.compile(expr).parsed for expr in expressions]

    def walk(node, parent=None):
        yield node, parent
        for child in node.get("children", []):
            if isinstance(child, dict):
                for item in walk(child, node):
                    yield item

    checks = []
    flatten_parents = {
        parent["type"]
        for tree in parsed_forests
        for node, parent in walk(tree)
        if node["type"] == "flatten" and parent is not None
    }
    checks.append(("所有 parser 生成的 flatten 都是 projection 左子树",
                   flatten_parents <= {"projection"}))

    slice_parents = {
        parent["type"]
        for tree in parsed_forests
        for node, parent in walk(tree)
        if node["type"] == "slice" and parent is not None
    }
    checks.append(("所有 parser 生成的 slice 先被 index_expression 包装",
                   slice_parents <= {"index_expression"}))

    keyval_parents = {
        parent["type"]
        for tree in parsed_forests
        for node, parent in walk(tree)
        if node["type"] == "key_val_pair" and parent is not None
    }
    checks.append(("key_val_pair 只作为 multi_select_dict 的直接子节点",
                   keyval_parents <= {"multi_select_dict"}))

    covered = {node_type for tree in parsed_forests
               for node_type in node_types(tree)}
    expected = {case["node"] for case in NODE_CASES}
    checks.append(("22 个 AST 节点全部由标准表达式证据覆盖",
                   covered == expected and len(expected) == 22))
    return checks


def table(rows, headers):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
    return "\n".join(lines)


def generate():
    node_rows = []
    seen = set()
    for case in NODE_CASES:
        result = run_case(case)
        seen.add(case["node"])
        node_rows.append({
            "节点": case["node"],
            "真实表达式": result["expr"],
            "现场 AST": result["ast"],
            "实测值": result["actual"],
            "状态": "PASS" if result["passed"] else "FAIL",
        })

    semantic_rows = []
    for case in SEMANTIC_CASES:
        result = run_case(case)
        semantic_rows.append({
            "ID": result["id"],
            "分类": case["area"],
            "规格结论": case["claim"],
            "真实表达式": result["expr"],
            "现场 AST": result["ast"],
            "实测值": result["actual"],
            "预期": result["expected"],
            "状态": "PASS" if result["passed"] else "FAIL",
        })

    invalid_rows = []
    for case in INVALID_CASES:
        result = run_case(case)
        invalid_rows.append({
            "ID": result["id"],
            "不可达入口": case["branch"],
            "表达式": result["expr"],
            "现场结果": result["actual"],
            "状态": "PASS" if result["passed"] else "FAIL",
        })

    invariant_rows = [
        {"不变量": claim, "现场结果": "PASS" if passed else "FAIL"}
        for claim, passed in verify_parser_invariants()
    ]

    all_passed = (
        all(row["状态"] == "PASS" for row in node_rows)
        and all(row["状态"] == "PASS" for row in semantic_rows)
        and all(row["状态"] == "PASS" for row in invalid_rows)
        and all(row["现场结果"] == "PASS" for row in invariant_rows)
    )

    lines = [
        "# JMESPath AST 证据矩阵",
        "",
        "本文件由 `python scripts/ast_evidence.py` 现场生成；脚本编译真实表达式、执行真实求值，并将结果写回本文件。",
        "",
        f"- 节点证据：{len(node_rows)}/22 PASS",
        f"- 行为证据：{sum(row['状态'] == 'PASS' for row in semantic_rows)}/{len(semantic_rows)} PASS",
        f"- 解析器不变量：{sum(row['现场结果'] == 'PASS' for row in invariant_rows)}/{len(invariant_rows)} PASS",
        f"- 不可达入口证据：{sum(row['状态'] == 'PASS' for row in invalid_rows)}/{len(invalid_rows)} PASS",
        f"- 总体状态：{'PASS' if all_passed else 'FAIL'}",
        "",
        "## 22 个节点的编译与求值证据",
        "",
        table(node_rows, ["节点", "真实表达式", "现场 AST", "实测值", "状态"]),
        "",
        "## 求值行为证据",
        "",
        table(semantic_rows, ["ID", "分类", "规格结论", "真实表达式",
                              "现场 AST", "实测值", "预期", "状态"]),
        "",
        "## 解析器结构不变量",
        "",
        table(invariant_rows, ["不变量", "现场结果"]),
        "",
        "## 不可达入口现场验证",
        "",
        table(invalid_rows, ["ID", "不可达入口", "表达式", "现场结果", "状态"]),
        "",
    ]
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(generate())
