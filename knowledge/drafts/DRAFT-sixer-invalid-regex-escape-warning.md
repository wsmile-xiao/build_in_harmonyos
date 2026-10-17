# Python 新版的无效转义警告会让旧版 stderr 测试失败

## 问题

在 HarmonyOS PC 随附的 Python 3.14 上运行 `sixer 1.6` 上游测试，44 个 unittest 中有 3 个失败。失败测试本身的转换结果正确，失败原因是子进程启动时把解释器的 `SyntaxWarning` 写入标准错误，而上游测试明确要求 `stderr == ''`。

改动前的真机日志：

```text
SyntaxWarning: "\." is an invalid escape sequence. Such sequences will not work in the future.
FAIL: test_nonexistent_operation
FAIL: test_patch_dir
FAIL: test_patch_file
Ran 44 tests
FAILED (failures=3)
```

触发位置是 `sixer.py` 的 `XRANGE_REGEX`：正则表达式写在普通字符串中，包含 `\.` 与 `\(`。新解释器在正则引擎处理字符串之前，就会在 Python 字面量解析阶段发出警告。

## 根因

Python 源码字符串字面量与正则表达式是两层解析。`"\."` 希望把反斜杠交给正则表达式，但普通字符串中的 `\.` 不是 Python 认可的转义。较新的 Python 会针对这类无效转义发出 `SyntaxWarning`。

`sixer` 的三个失败用例都会启动新的 Python 子进程运行 `sixer.py`，随后断言标准错误为空。模块导入时的语法警告因此成为测试可见输出，测试把它判为失败。只在父进程测试模块导入前编译一次，不能覆盖这三个新子进程。

## 最小解决与边界

把正则字面量改为原始字符串：

```python
XRANGE_REGEX = re.compile(r"(?<!moves\.)xrange *\(")
```

前缀 `r` 令 Python 将反斜杠原样交给正则引擎。正则引擎收到的字符序列与原作者意图相同，匹配规则不变；Python 词法层不再把 `\.` 当成无效字符串转义，也就不再污染子进程的 `stderr`。

修复后以 `-Werror::SyntaxWarning` 编译模块，并重新运行全部上游测试。配方只在 `conandata.yml` 中声明此最小源码补丁，不关闭测试、不删除标准错误断言，也不设置全局忽略警告环境变量。

适用边界：仅适用于普通 Python 字符串中含有正则反斜杠、解释器因此发出语法警告，且警告会影响测试或运行行为的情况。不是所有反斜杠都应机械替换为原始字符串；若字符串本来需要 Python 解释 `\n`、`\t` 等转义，则应按其语义逐个判断。若 stderr 断言与警告无关，或警告来自第三方依赖，本文方案不能代替根因定位。

## 验证

改动前真机命令与结果：

```sh
python3 tests.py
# Ran 44 tests in 23.221s
# FAILED (failures=3)
```

应用补丁后的真机验证：

```sh
python3 -Werror::SyntaxWarning -m py_compile sixer.py
# 退出码 0
python3 tests.py
# Ran 44 tests in 22.998s
# OK
```

消费者测试还验证了 Conan 包内模块导入、命令可执行权限，以及 `bin/sixer --help` 返回码和帮助文本、失败退出码传递（`--write xrange <缺失文件>` 返回非零）；4 项全部通过。用 `-Werror` 而非忽略警告，能够证明问题来自源码字面量解析且已消失。

## 查重表与适用边界

| 相关知识 | 已覆盖内容 | 本条新增边界与反证 |
|---|---|---|
| E319 | 纯 Python noarch 包的安装目录、`PYTHONPATH` 和受限网络导入问题 | 不涉及 Python 语法警告或测试子进程 stderr；本问题可在不改包目录布局的情况下复现。 |
| E241、E255 | 纯数据包和资源包的 Conan 打包与验证 | `sixer` 是有 Python 模块与命令入口的工具，不是纯数据或纯资源包；这些条目不解释此次失败。 |

在 `origin/main` 提交 `cc02beaa531cbc3227000ae5132dc2fbd14e65bd` 的 `knowledge/graph/` 与 `knowledge/doc/` 中检索 `SyntaxWarning`、`invalid escape sequence`、`无效转义` 和 Python 正则字面量告警，命中 **0 个文件**。反证命令：

```sh
git grep -in -E 'SyntaxWarning|invalid escape sequence|无效转义|invalid.*escape' origin/main -- knowledge/graph knowledge/doc
```

独立复现点是 Python 解释器对源码字面量发出的告警：上游子进程把该告警写入 stderr，而 unittest 只在三个程序级测试中因空 stderr 断言失败。通过修改正则字面量后，44 项完整上游测试均通过，消费者测试另有 4/4 通过。

## 元信息

- 贡献者：`iKalous_OscarP`
- 贡献路径：Path B 知识草稿，随 `sixer 1.6` Conan 配方与最小上游补丁提交。
- 草稿状态：`draft: true`；正式知识图谱与索引由主编审核后维护。
- 关联 PR：#13550。
