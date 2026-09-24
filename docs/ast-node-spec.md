# JMESPath AST 节点规格

本规格描述当前仓库的内部 AST，而不是稳定公开 API。编译链路是：

1. `jmespath/lexer.py` 把表达式切成 token。
2. `jmespath/parser.py` 用 Pratt parser 调 `jmespath/ast.py` 中的工厂函数生成普通 `dict` 节点。
3. `ParsedResult.search()` 创建 `jmespath/visitor.py` 的 `TreeInterpreter`，从根节点开始深度优先访问。

所有节点都有：

- `type`：字符串，节点类型。
- `children`：列表。绝大多数元素是 AST 节点；`slice` 的三个 child 是整数或 `null`。
- `value`：只在携带名称、字面量、运算符或下标的节点上出现。

下面严格按照 `jmespath/ast.py` 中工厂函数出现的源码顺序排列。每个例子都由 `scripts/ast_evidence.py` 在证据矩阵中真实编译和求值。

## 1. `comparator`

- 构造：`ast.comparator(name, first, second)`。
- 字段：`value` 是比较运算符；取值为 `eq`、`ne`、`gt`、`lt`、`gte`、`lte`。
- 子节点：`children[0]` 为左表达式，`children[1]` 为右表达式；工厂不限制二者类型，解析器分别从比较符两侧解析。
- 求值：先在同一当前值上求左右子节点。`eq`/`ne` 走 `_equals()`，数字 `0`/`1` 与布尔值永远不相等；`ne` 是相等结果取反。`gt`/`lt`/`gte`/`lte` 只接受实际数字或字符串，否则返回 `null`。
- 例子：`` `a == `1`` ``。

## 2. `current`

- 构造：`ast.current_node()`。
- 字段：无 `value`。
- 子节点：无。
- 求值：原样返回当前访问值。过滤条件和函数参数中的 `@` 表示当前元素，管道右值中的 `@` 表示管道左侧结果。
- 例子：`@`。

## 3. `expref`

- 构造：`ast.expref(expression)`。
- 字段：无 `value`。
- 子节点：`children[0]` 是被延迟求值的表达式。
- 求值：不计算子表达式，返回内部 `_Expression` 包装对象。内置函数如 `map()`、`sort_by()` 之后可通过它按元素访问表达式。
- 例子：`&n`。

## 4. `function_expression`

- 构造：`ast.function_expression(name, args)`。
- 字段：`value` 是未加引号的函数名。
- 子节点：`children` 是参数表达式列表；可为空。普通参数在调用前立即求值，`expref` 参数求值为 `_Expression` 对象。
- 求值：依次求出所有参数，然后交给当前 `Functions` 注册表按函数签名校验并调用。未知函数在求值期抛 `UnknownFunctionError`，类型或参数数量不匹配抛对应函数异常。
- 例子：`length(items)`。

## 5. `field`

- 构造：`ast.field(name)`。
- 字段：`value` 是未转义后的字段名字符串；未引号标识符和 JSON 双引号标识符最终都生成该节点。
- 子节点：无。
- 求值：对当前值调用 `.get(name)`；当前值没有 `get` 方法时返回 `null`。字段缺失时，Python dict 的 `.get()` 也返回 `None`。
- 例子：`a`。

## 6. `filter_projection`

- 构造：`ast.filter_projection(left, right, comparator)`。
- 字段：无 `value`。
- 子节点：`children[0]` 是待过滤数组来源；`children[1]` 是每个保留元素要执行的投影 RHS；`children[2]` 是过滤条件。
- 求值：先求左值；不是数组则返回 `null`。随后对每个元素求条件节点，按 JMESPath 真值规则判断；条件为真时再以该元素为当前值求 RHS，RHS 为 `null` 的结果被丢弃。
- 例子：`items[?ok].name`。

## 7. `flatten`

- 构造：`ast.flatten(node)`。
- 字段：无 `value`。
- 子节点：`children[0]` 是待压平值的来源。
- 求值：先求子节点；不是数组返回 `null`。遍历一层元素：元素本身是数组时用 `extend()` 合并，否则原样追加，因此只压平一层，深层嵌套数组保留。
- parser 形态：解析器不会生成独立根 `flatten`；它总是成为 `projection` 的左子树。
- 例子：`nested[]`。

## 8. `identity`

- 构造：`ast.identity()`。
- 字段：无 `value`。
- 子节点：无。
- 求值：原样返回当前值。
- parser 形态：作为根级 `*`、`[*]`、`[]`、切片/过滤等投影的左侧起点，或在低优先级运算符终止投影时作为投影 RHS。
- 例子：`[*]`。

## 9. `index`

- 构造：`ast.index(index)`。
- 字段：`value` 是词法阶段解析出的整数，可正可负。
- 子节点：无。
- 求值：当前值必须是数组；支持 Python 风格负数下标，越界返回 `null`，非数组返回 `null`。
- parser 形态：单独括号下标先与左侧值组合成 `index_expression`。
- 例子：`[0]`。

## 10. `index_expression`

- 构造：`ast.index_expression(children)`。
- 字段：无 `value`。
- 子节点：第一个 child 是数组或起点表达式，后续 child 是 `index` 或 `slice`；连续普通下标会在解析器中合并到同一个 `index_expression`。
- 求值：从当前值开始，按 child 顺序把上一节点结果传给下一节点。它和 `subexpression` 的访问方式相同，区别只在节点来源是括号链。
- 例子：`items[0]`。

## 11. `key_val_pair`

- 构造：`ast.key_val_pair(key_name, node)`。
- 字段：`value` 是多选哈希中的键名；重复键允许出现。
- 子节点：`children[0]` 是该键对应的值表达式。
- 求值：直接访问该节点时只返回值表达式的结果；`multi_select_dict` 访问它时读取其 `value` 作为结果对象的键。
- parser 形态：只作为 `multi_select_dict` 的直接 child。
- 例子：`{a: a}`。

## 12. `literal`

- 构造：`ast.literal(literal_value)`。
- 字段：`value` 是已经解析好的 JSON 值；单引号 raw string 会得到 Python 字符串。
- 子节点：无。
- 求值：忽略当前值，直接返回节点中保存的常量。
- 例子：`'x'`。

## 13. `multi_select_dict`

- 构造：`ast.multi_select_dict(nodes)`。
- 字段：无 `value`。
- 子节点：一个或多个 `key_val_pair` 节点。
- 求值：当前值为 `null` 时整体返回 `null`。否则创建 dict（默认 `dict`，可用 `Options.dict_cls` 替换），逐对求 key 节点并写入 `result[key] = value`；值为 `null` 也保留，重复键由后一个值覆盖。
- 例子：`{a: a, b: b}`。

## 14. `multi_select_list`

- 构造：`ast.multi_select_list(nodes)`。
- 字段：无 `value`。
- 子节点：一个或多个任意表达式节点，按源码顺序排列。
- 求值：当前值为 `null` 时整体返回 `null`；否则按顺序求每个表达式并追加到数组，表达式得到的 `null` 也保留。
- 例子：`[a, b]`。

## 15. `or_expression`

- 构造：`ast.or_expression(left, right)`。
- 字段：无 `value`。
- 子节点：`children[0]`、`children[1]` 分别为左右表达式。
- 求值：先求左值；当左值是 JMESPath false（`null`、`false`、空字符串、空数组、空对象）时求右值并返回，否则直接返回左值。数字 `0` 不属于 false。
- 例子：`absent || b`。

## 16. `and_expression`

- 构造：`ast.and_expression(left, right)`。
- 字段：无 `value`。
- 子节点：`children[0]`、`children[1]` 分别为左右表达式。
- 求值：先求左值；左值为 JMESPath false 时短路返回左值，否则求右值并返回右值。它返回原值而不是强制布尔值。
- 例子：`a && b`。

## 17. `not_expression`

- 构造：`ast.not_expression(expr)`。
- 字段：无 `value`。
- 子节点：`children[0]` 是要取反的表达式。
- 求值：先求子节点；实际数字 `0` 被明确处理为返回 `false`，其他值使用 Python 布尔取反。因此空字符串、空数组、空对象、`null`、`false` 得到 `true`。
- 例子：`!a`。

## 18. `pipe`

- 构造：`ast.pipe(left, right)`。
- 字段：无 `value`。
- 子节点：`children[0]` 是左侧表达式，`children[1]` 是右侧表达式。
- 求值：从原当前值求左节点，再把左节点结果作为新的当前值求右节点；右节点不会自动看到原始根数据。
- 例子：`items | length(@)`。

## 19. `projection`

- 构造：`ast.projection(left, right)`。
- 字段：无 `value`。
- 子节点：`children[0]` 是数组来源，通常由通配括号、切片或 `flatten` 产生；`children[1]` 是对每个元素执行的 RHS。
- 求值：先求左值；不是数组返回 `null`。对每个数组元素求 RHS，并丢弃结果为 `null` 的元素；RHS 自身返回数组时不会再自动压平。
- 例子：`items[*].name`。

## 20. `subexpression`

- 构造：`ast.subexpression(children)`。
- 字段：无 `value`。
- 子节点：点号链上的两个或更多表达式节点；连续点号会复用并追加到同一个 `subexpression`。
- 求值：从当前值开始，依次访问每个 child，并把上一节点结果传给下一节点；任一阶段得到 `null` 后通常继续传播为 `null`。
- 例子：`box.label`。

## 21. `slice`

- 构造：`ast.slice(start, end, step)`。
- 字段：无 `value`。
- 子节点：`children` 固定为 `[start, end, step]`；每项是整数或 `null`，不是 AST 节点。
- 求值：当前值必须是数组，然后构造 Python 内建 `slice(start, end, step)` 取值；省略边界和负数边界遵循 Python 语义。`step == 0` 会由 Python 抛 `ValueError`。
- parser 形态：解析器先把它放进 `index_expression`，再把整个 index expression 包成 `projection`；不存在 parser 生成的独立 `slice` 根节点。
- 例子：`items[0:2].name`。

## 22. `value_projection`

- 构造：`ast.value_projection(left, right)`。
- 字段：无 `value`。
- 子节点：`children[0]` 是对象来源；`children[1]` 是对每个对象 value 执行的 RHS。
- 求值：先求左值并调用 `.values()`；没有 `values()` 方法则返回 `null`。对每个 value 求 RHS，丢弃 RHS 为 `null` 的结果。遍历顺序由底层 dict 的值顺序决定。
- 例子：`obj.*.name`。

## 真值与空结果

- `or`、`and` 和过滤条件共用 `TreeInterpreter._is_false()` 的真值模型：`null`、`false`、空字符串、空数组、空对象为 false；数字 `0` 为 true。
- 普通字段访问、过滤 RHS、数组投影和对象投影会把单个缺失值表示为 `null` 或直接丢弃；多选列表和多选哈希则会保留其内部表达式产生的 `null`。
