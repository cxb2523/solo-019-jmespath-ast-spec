# JMESPath AST 证据矩阵

本文件由 `python scripts/ast_evidence.py` 现场生成；脚本编译真实表达式、执行真实求值，并将结果写回本文件。

- 节点证据：22/22 PASS
- 行为证据：52/52 PASS
- 解析器不变量：4/4 PASS
- 不可达入口证据：6/6 PASS
- 总体状态：PASS

## 22 个节点的编译与求值证据

| 节点 | 真实表达式 | 现场 AST | 实测值 | 状态 |
| --- | --- | --- | --- | --- |
| comparator | `` a == `1` `` | `comparator(eq)[field('a'), literal(1)]` | `true` | PASS |
| current | `@` | `current[]` | `["one", "two"]` | PASS |
| expref | `&n` | `expref[field('n')]` | `{"__actual_type__": "expref", "ast": "field#n"}` | PASS |
| function_expression | `length(items)` | `function_expression('length')[field('items')]` | `3` | PASS |
| field | `a` | `field('a')` | `1` | PASS |
| filter_projection | `items[?ok].name` | `filter_projection[field('items'), field('name'), field('ok')]` | `["one", "three"]` | PASS |
| flatten | `nested[]` | `projection[flatten[field('nested')], identity[]]` | `[1, 2, 3, [4], 5]` | PASS |
| identity | `[*]` | `projection[identity[], identity[]]` | `["x", "y"]` | PASS |
| index | `[0]` | `index_expression[identity[], index(0)]` | `"x"` | PASS |
| index_expression | `items[0]` | `index_expression[field('items'), index(0)]` | `{"n": 1, "name": "one", "ok": true, "refs": [10], "tags": ["x", "y"]}` | PASS |
| key_val_pair | `{a: a}` | `multi_select_dict[key_val_pair('a')[field('a')]]` | `{"a": 1}` | PASS |
| literal | `'x'` | `literal("x")` | `"x"` | PASS |
| multi_select_dict | `{a: a, b: b}` | `multi_select_dict[key_val_pair('a')[field('a')], key_val_pair('b')[field('b')]]` | `{"a": 1, "b": 2}` | PASS |
| multi_select_list | `[a, b]` | `multi_select_list[field('a'), field('b')]` | `[1, 2]` | PASS |
| or_expression | `absent || b` | `or_expression[field('absent'), field('b')]` | `2` | PASS |
| and_expression | `a && b` | `and_expression[field('a'), field('b')]` | `2` | PASS |
| not_expression | `!a` | `not_expression[field('a')]` | `false` | PASS |
| pipe | `items | length(@)` | `pipe[field('items'), function_expression('length')[current[]]]` | `3` | PASS |
| projection | `items[*].name` | `projection[field('items'), field('name')]` | `["one", "two", "three"]` | PASS |
| subexpression | `box.label` | `subexpression[field('box'), field('label')]` | `"deep"` | PASS |
| slice | `items[0:2].name` | `projection[index_expression[field('items'), slice(0,2,None)], field('name')]` | `["one", "two"]` | PASS |
| value_projection | `obj.*.name` | `value_projection[field('obj'), field('name')]` | `["A", "B"]` | PASS |

## 求值行为证据

| ID | 分类 | 规格结论 | 真实表达式 | 现场 AST | 实测值 | 预期 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P01 | 投影 | 通配投影逐元素求值 RHS。 | `items[*].name` | `projection[field('items'), field('name')]` | `["one", "two", "three"]` | `["one", "two", "three"]` | PASS |
| P02 | 投影 | 左值不是数组时返回 null。 | `absent[*]` | `projection[field('absent'), identity[]]` | `null` | `null` | PASS |
| P03 | 投影 | RHS 为 null 的元素会被丢弃。 | `items[*].absent` | `projection[field('items'), field('absent')]` | `[]` | `[]` | PASS |
| P04 | 投影 | 投影不会自动压平 RHS 产生的数组。 | `items[*].refs` | `projection[field('items'), field('refs')]` | `[[10], [], [30, 31]]` | `[[10], [], [30, 31]]` | PASS |
| P05 | 投影 | flatten 只合并一层数组。 | `nested[]` | `projection[flatten[field('nested')], identity[]]` | `[1, 2, 3, [4], 5]` | `[1, 2, 3, [4], 5]` | PASS |
| P06 | 投影 | flatten 左值不是数组时返回 null。 | `a[]` | `projection[flatten[field('a')], identity[]]` | `null` | `null` | PASS |
| P07 | 投影 | 过滤投影只保留条件为 JMESPath true 的元素。 | `` items[?n > `1`].name `` | `filter_projection[field('items'), field('name'), comparator(gt)[field('n'), literal(1)]]` | `["two", "three"]` | `["two", "three"]` | PASS |
| P08 | 投影 | 过滤投影左值不是数组时返回 null。 | `absent[?ok]` | `filter_projection[field('absent'), identity[], field('ok')]` | `null` | `null` | PASS |
| P09 | 投影 | 过滤投影会丢弃 RHS 为 null 的结果。 | `items[?ok].absent` | `filter_projection[field('items'), field('absent'), field('ok')]` | `[]` | `[]` | PASS |
| P10 | 投影 | 根过滤表达式以 identity 为左值。 | `[?ok]` | `filter_projection[identity[], identity[], field('ok')]` | `[{"n": 1, "name": "one", "ok": true, "refs": [10], "tags": ["x", "y"]}, {"n": 3, "name": "three", "ok": true, "refs": [30, 31], "tags": []}]` | `[{"n": 1, "name": "one", "ok": true, "refs": [10], "tags": ["x", "y"]}, {"n": 3, "name": "three", "ok": true, "refs": [30, 31], "tags": []}]` | PASS |
| P11 | 投影 | 对象投影遍历 dict.values()。 | `obj.*.name` | `value_projection[field('obj'), field('name')]` | `["A", "B"]` | `["A", "B"]` | PASS |
| P12 | 投影 | 对象投影左值不是对象时返回 null。 | `a.*` | `value_projection[field('a'), identity[]]` | `null` | `null` | PASS |
| P13 | 投影 | 对象投影同样丢弃 RHS 为 null 的结果。 | `obj.*.absent` | `value_projection[field('obj'), field('absent')]` | `[]` | `[]` | PASS |
| S01 | 切片 | 省略 end 时截到末尾。 | `nums[1:]` | `projection[index_expression[field('nums'), slice(1,None,None)], identity[]]` | `[1, 2]` | `[1, 2]` | PASS |
| S02 | 切片 | 负数 end 按 Python 切片归一化。 | `nums[:-1]` | `projection[index_expression[field('nums'), slice(None,-1,None)], identity[]]` | `[3, 1]` | `[3, 1]` | PASS |
| S03 | 切片 | 负 step 反转序列。 | `nums[::-1]` | `projection[index_expression[field('nums'), slice(None,None,-1)], identity[]]` | `[2, 1, 3]` | `[2, 1, 3]` | PASS |
| S04 | 切片 | 切片左值不是数组时返回 null。 | `a[0:1]` | `projection[index_expression[field('a'), slice(0,1,None)], identity[]]` | `null` | `null` | PASS |
| S05 | 切片 | step 为 0 时底层 Python slice 抛 ValueError。 | `nums[::0]` | `projection[index_expression[field('nums'), slice(None,None,0)], identity[]]` | `ValueError()` | `ValueError()` | PASS |
| Q01 | 管道 | 管道把左值结果作为右值当前值。 | `items | length(@)` | `pipe[field('items'), function_expression('length')[current[]]]` | `3` | `3` | PASS |
| Q02 | 管道 | 管道不会在右值重新回到根数据。 | `missing | b` | `pipe[field('missing'), field('b')]` | `null` | `null` | PASS |
| Q03 | 管道 | 管道优先级低于后续点号/括号链。 | `items | [0].name` | `pipe[field('items'), subexpression[index_expression[identity[], index(0)], field('name')]]` | `"one"` | `"one"` | PASS |
| H01 | 多选哈希 | 哈希会保留表达式产生的 null 值。 | `{x: absent, y: a}` | `multi_select_dict[key_val_pair('x')[field('absent')], key_val_pair('y')[field('a')]]` | `{"x": null, "y": 1}` | `{"x": null, "y": 1}` | PASS |
| H02 | 多选哈希 | 当前值为 null 时整个多选哈希为 null。 | `` `null` | {a: a} `` | `pipe[literal(null), multi_select_dict[key_val_pair('a')[field('a')]]]` | `null` | `null` | PASS |
| H03 | 多选哈希 | 重复键由后一个值覆盖。 | `{a: a, a: b}` | `multi_select_dict[key_val_pair('a')[field('a')], key_val_pair('a')[field('b')]]` | `{"a": 2}` | `{"a": 2}` | PASS |
| L01 | 多选列表 | 列表会保留表达式产生的 null 值。 | `[absent, a]` | `multi_select_list[field('absent'), field('a')]` | `[null, 1]` | `[null, 1]` | PASS |
| L02 | 多选列表 | 当前值为 null 时整个多选列表为 null。 | `` `null` | [a] `` | `pipe[literal(null), multi_select_list[field('a')]]` | `null` | `null` | PASS |
| F01 | 函数调用 | expref 参数保持不求值，由函数按需访问。 | `map(&n, items)` | `function_expression('map')[expref[field('n')], field('items')]` | `[1, 2, 3]` | `[1, 2, 3]` | PASS |
| F02 | 函数调用 | 普通参数在调用函数前完成求值。 | `not_null(absent, a)` | `function_expression('not_null')[field('absent'), field('a')]` | `1` | `1` | PASS |
| F03 | 函数调用 | 未知函数名在求值期报错。 | `nosuch()` | `function_expression('nosuch')[]` | `UnknownFunctionError()` | `UnknownFunctionError()` | PASS |
| F04 | 函数调用 | 内置函数按签名做类型检查。 | `length(a)` | `function_expression('length')[field('a')]` | `JMESPathTypeError()` | `JMESPathTypeError()` | PASS |
| C01 | 比较 | eq 比较两个已求值子节点。 | `` a == `1` `` | `comparator(eq)[field('a'), literal(1)]` | `true` | `true` | PASS |
| C02 | 比较 | eq 不等时返回 false。 | `a == b` | `comparator(eq)[field('a'), field('b')]` | `false` | `false` | PASS |
| C03 | 比较 | ne 是 eq 结果的逻辑取反。 | `a != b` | `comparator(ne)[field('a'), field('b')]` | `true` | `true` | PASS |
| C04 | 比较 | gt 使用数值顺序。 | `b > a` | `comparator(gt)[field('b'), field('a')]` | `true` | `true` | PASS |
| C05 | 比较 | 本实现也允许字符串顺序比较。 | `` `"a"` < `"b"` `` | `comparator(lt)[literal("a"), literal("b")]` | `true` | `true` | PASS |
| C06 | 比较 | 顺序比较遇到不可比较类型返回 null。 | `absent < a` | `comparator(lt)[field('absent'), field('a')]` | `null` | `null` | PASS |
| C07 | 比较 | 数字 0 不等于布尔 false。 | `` `0` == `false` `` | `comparator(eq)[literal(0), literal(false)]` | `false` | `false` | PASS |
| C08 | 比较 | 数字 1 不等于布尔 true。 | `` `1` == `true` `` | `comparator(eq)[literal(1), literal(true)]` | `false` | `false` | PASS |
| C09 | 比较 | eq 支持结构化值相等。 | `` [a] == [`1`] `` | `comparator(eq)[multi_select_list[field('a')], multi_select_list[literal(1)]]` | `true` | `true` | PASS |
| B01 | 逻辑 | or 在左值为 JMESPath false 时返回右值。 | `` `""` || b `` | `or_expression[literal(""), field('b')]` | `2` | `2` | PASS |
| B02 | 逻辑 | 数字 0 在 JMESPath 中为 true。 | `` `0` || b `` | `or_expression[literal(0), field('b')]` | `0` | `0` | PASS |
| B03 | 逻辑 | and 在左值 false 时短路返回左值。 | `absent && b` | `and_expression[field('absent'), field('b')]` | `null` | `null` | PASS |
| B04 | 逻辑 | and 在左值 true 时返回右值。 | `a && b` | `and_expression[field('a'), field('b')]` | `2` | `2` | PASS |
| B05 | 逻辑 | not 对数字 0 明确返回 false。 | `` !`0` `` | `not_expression[literal(0)]` | `false` | `false` | PASS |
| B06 | 逻辑 | not false 返回 true。 | `` !`false` `` | `not_expression[literal(false)]` | `true` | `true` | PASS |
| B07 | 逻辑 | not 空字符串返回 true。 | `` !`""` `` | `not_expression[literal("")]` | `true` | `true` | PASS |
| X01 | 其他节点 | field 在非对象上返回 null。 | `a` | `field('a')` | `null` | `null` | PASS |
| X02 | 其他节点 | index 支持负数下标。 | `[-1]` | `index_expression[identity[], index(-1)]` | `2` | `2` | PASS |
| X03 | 其他节点 | index 越界返回 null。 | `[9]` | `index_expression[identity[], index(9)]` | `null` | `null` | PASS |
| X04 | 其他节点 | index 左值不是数组时返回 null。 | `a[0]` | `index_expression[field('a'), index(0)]` | `null` | `null` | PASS |
| X05 | 其他节点 | subexpression 沿链传递 null。 | `absent.deep` | `subexpression[field('absent'), field('deep')]` | `null` | `null` | PASS |
| X06 | 其他节点 | current 在过滤条件中指向当前元素。 | `` items[?@.n > `1`].name `` | `filter_projection[field('items'), field('name'), comparator(gt)[subexpression[current[], field('n')], literal(1)]]` | `["two", "three"]` | `["two", "three"]` | PASS |

## 解析器结构不变量

| 不变量 | 现场结果 |
| --- | --- |
| 所有 parser 生成的 flatten 都是 projection 左子树 | PASS |
| 所有 parser 生成的 slice 先被 index_expression 包装 | PASS |
| key_val_pair 只作为 multi_select_dict 的直接子节点 | PASS |
| 22 个 AST 节点全部由标准表达式证据覆盖 | PASS |

## 不可达入口现场验证

| ID | 不可达入口 | 表达式 | 现场结果 | 状态 |
| --- | --- | --- | --- | --- |
| E01 | 空表达式不能产生根 identity。 | （空串） | `EmptyExpressionError()` | PASS |
| E02 | {} 不是空多选哈希。 | `{}` | `ParseError()` | PASS |
| E03 | [] 是 flatten，不是空多选列表。 | `[]` | `[]` | PASS |
| E04 | 不允许直接紧跟点号的多选列表索引。 | `.[0]` | `ParseError()` | PASS |
| E05 | 裸星号不能作为函数参数之外的括号投影 RHS。 | `foo[]*` | `ParseError()` | PASS |
| E06 | 双引号标识符不能充当函数名。 | `"f"()` | `ParseError()` | PASS |
