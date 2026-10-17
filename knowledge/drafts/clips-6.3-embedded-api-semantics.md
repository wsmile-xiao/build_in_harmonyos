# clips 6.3 嵌入式 C API 语义（草稿）

- **来源**：clips 6.3（上游 6.30）适配，真机 test_package 首轮 5/8 FAIL 排障
- **日期**：2026-09-08
- **证据**：`archives/c/clips/6.3/notes.md`、`archives/c/clips/6.3/test_package/test.c`

## 语义 1：EnvBuild 每次只解析一个 construct

`EnvBuild`（`core/strngfun.c`）的实现是"读 `(` → 读 construct 类型名 →
`ParseConstruct` 一次 → 关闭 router → 返回"，**没有多构造循环**。

把多个构造拼进一个字符串传入只会定义第一个 construct 并返回 TRUE。后续
构造静默缺失，典型表现：

- `EnvRun` 返回 0（规则根本没定义）
- 规则副作用事实不在事实列表
- 依赖后定义构造的调用报 `No function ... exists for external call`

**正确用法**：每个 deftemplate/defrule/deffunction 单独调用一次 EnvBuild。
（CLI 不受影响：CommandLoop 逐命令解析。）

## 语义 2：EnvFunctionCall 返回 TRUE=出错 / FALSE=成功

`EnvFunctionCall` → `FunctionCall2`（`core/evaluatn.c`）返回的是**错误状态**：
`TRUE(1)` = 出错（函数不存在也返回 TRUE 并打印错误），`FALSE(0)` = 求值成功。

结果值从传入的 `DATA_OBJECT` 读取：`GetpType(&rv)`、`ValueToLong(GetpValue(&rv))`、
`ValueToString(GetpValue(&rv))`（SYMBOL/STRING 通用）。

## 验证

真机（OHOS aarch64）`conan create` test_package：test.c 按上述语义编写的
10 项断言全部 PASS；错误写法（拼接串 + `==1` 断言）在首轮复现了上述两类
失败，修复后全绿。
