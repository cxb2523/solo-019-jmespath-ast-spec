# Parser 无法从标准表达式生成的 AST 形状和分支

这里的“不可达”不是指 22 个节点类型中有类型完全不会出现：相反，22 种 `type` 都能由合法表达式生成。不可达的是某些 AST 挂载位置、子节点数量/类型组合，以及解析器中的报错分支。证据矩阵中的“解析器结构不变量”和“不可达入口现场验证”由 `python scripts/ast_evidence.py` 每次现场校验。

## 不可达的 AST 形状

| ID | 手工 AST 可以构造的形状 | 为什么标准表达式走不到 | 绕过工厂的方式 |
| --- | --- | --- | --- |
| U01 | 根节点是 `flatten`，或 `flatten` 不是某个 `projection` 的左子树 | `[]` 在 NUD 位置会立刻构造成 `projection(flatten(identity()), RHS)`；`foo[]` 在 LED 位置也先构造 `flatten(left)`，再立刻包成 `projection`。解析器没有只返回 `flatten` 的出口。 | `ast.flatten(ast.field('items'))` |
| U02 | 根节点或普通节点是裸露的 `slice` | `ast.slice(start,end,step)` 只在 `_parse_slice_expression()` 中调用，随后 `_project_if_slice()` 一定把它放入 `index_expression`，切片再由该 index expression 包成 `projection`。 | `ast.slice(0, 2, None)` |
| U03 | `key_val_pair` 出现在 `multi_select_dict` 外 | 该工厂只在 `_parse_multi_select_hash()` 中调用，构造后立即加入哈希节点的 `pairs`。访问者虽然能单独访问它，但 parser 不会生成这种树。 | `ast.key_val_pair('a', ast.field('a'))` |
| U04 | `index_expression` 不是“左值 + `index`/`slice`”，或只有一个 child | NUD 下标从 `identity` 开始，LED 下标从已有左表达式开始；进入函数的 right 只能是 `index` 或 `slice`。连续括号链通过同一个节点追加，因此不会产生空 child；普通字段也不会放进该节点。 | `ast.index_expression([ast.field('a')])` |
| U05 | `subexpression` 少于两个 child，或混入括号 index/slice child | 点号链第一次构造时至少有左右两个节点，后续点号只做 append；括号链走 `_token_led_lbracket()`，不会进入点号的 subexpression 追加路径。 | `ast.subexpression([ast.field('a')])` |
| U06 | 空的 `multi_select_dict` 或 `multi_select_list` | 两个解析循环都要求至少解析一个表达式，然后才匹配 `}` 或 `]`；`{}` 在等待键名时直接报 `ParseError`。 | `ast.multi_select_dict([])`、`ast.multi_select_list([])` |
| U07 | 不是严格二叉的 `pipe`、`projection`、`value_projection`、`filter_projection`、比较与逻辑节点 | 对应工厂虽然接收普通 list，但解析器总是传入固定数量的左右子树；`filter_projection` 还固定带一个 condition。 | 例如 `ast.pipe([ast.field('a')])` |
| U08 | `function_expression` 的名称不是未引号 field，或 args 中混入非表达式值 | 函数调用的 LED 分支要求左侧节点 `type == 'field'`；引号标识符后跟 `(` 在 NUD 阶段就报错。每个参数都来自 `_expression()`，而 `expref` 本身也会构造成 `expref` AST 节点。 | 手工调用 `ast.function_expression('f', [1])` |

## 解析器中的拒绝入口

| ID | 语法入口 | 现场结果 | 进不去的原因 |
| --- | --- | --- | --- |
| E01 | 空字符串 | `EmptyExpressionError` | lexer 初始化时显式拒绝空表达式，因此不会通过“什么都不解析”得到根 `identity`。 |
| E02 | `{}` | `ParseError` | 多选哈希循环必须先匹配 quoted/unquoted identifier；遇到 `}` 直接抛错，所以无法生成空哈希节点。 |
| E03 | 把 `[]` 当空多选列表 | 合法 flatten | lexer 把 `[]` 识别成单个 `flatten` token，而不是 `lbracket`/`rbracket` 两个 token；因此它永远不会进入 `_parse_multi_select_list()`。 |
| E04 | `.[0]` | `ParseError` | `_parse_dot_rhs()` 只允许点号后接标识符、`*`、多选列表或多选哈希；普通 index expression 不能直接以点号开头。 |
| E05 | `foo[]*` | `ParseError` | flatten 的 RHS 由 `_parse_projection_rhs()` 处理；裸 `star` 只允许对象值投影点号形式或 `[*]` 词法形式，不能作为这个分支的普通 token 流。 |
| E06 | `"f"()` | `ParseError` | 双引号标识符生成 field 后，parser 立即检查下一个 token；函数名必须是未引号标识符。 |

## 合法但容易误判的分支

- `[?condition][]` 是合法表达式。过滤投影看到下一个 token 为 `flatten` 时，会把 RHS 设为 `identity`；随后外层 flatten/projection 继续构造，因此这个 `identity` 分支不是死分支。
- `[?condition]` 也是合法表达式。过滤 token 在根位置由 `identity` 作为左值，RHS 在遇到低优先级 token 或 EOF 时为 `identity`。
- `*`、`[*]`、`[]` 中的 `identity` 均可达；它们是把当前对象、当前数组或当前 flatten 结果接入投影的内部节点。
- `slice` 的三个 child 不是 AST 节点而是 `start/end/step` 值；这是 AST 形状上的特例，但由所有合法切片稳定产生。
- 22 个 `type` 均有真实表达式覆盖；没有“整个节点类型不可达”。不可达性存在于节点上下文、子节点组合和报错分支中。
