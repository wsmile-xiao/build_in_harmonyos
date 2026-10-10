# DRAFT：Conan 配方生成 shell 文本时禁用 str.format()（${VAR:-…} 与 Python 占位符冲突）

## 使用说明

**何时用**：在 `conanfile.py` 的 `package()`/`build()` 里以 Python 生成任何将被写盘的
shell 文本——bin wrapper 脚本、launcher、env 文件、modulefile、测试脚本——且文本中含有
shell 参数展开（`${VAR}`、`${VAR:-default}`、`$(cmd)`）时，套用本条的生成规则。

**为什么**：Python 的 `str.format()` 会把文本中所有 `{...}` 解析为占位符。shell 的
`${TS_HOME:-$(dirname "$0")}` 恰好形如 `{...}`（去掉 `$` 后的部分被当作字段名），
典型后果二选一：

1. `KeyError: 'TS_HOME'` —— package() 中途抛异常，bin/ 目录**静默为空**（makedirs 已执行、
   循环体首行即抛错时一个文件都写不出来）；
2. 更隐蔽的**内容损坏** —— 部分场景不抛错而是产出 `TS_HOME=""`、`exec node "/dist/bin.js"`
   这类残缺脚本，真机上 wrapper 必然运行失败。

**自检动作**（W4 提交前，适用于任何配方）：

```bash
grep -n '\.format(' conanfile.py
grep -n 'self\.run' conanfile.py | grep '\${'      # CI L0 同类检查 shell_env_var_in_run
```

凡 `grep '\.format('` 有命中且同文件含 `${`，逐处确认不在生成 shell 文本的路径上。

## 适用范围

- ✅ `package()` 写 bin wrapper / launcher / `*.sh` / env 文件 / modulefile
- ✅ `build()` 生成临时脚本再 `self.run("sh ...")`
- ✅ test_package 生成测试脚本
- ✅ 任何「Python 字符串模板 → 落盘为 shell 文本」的场合，与具体库名无关
- ❌ 不适用于：纯 CMake/Autotools 配方（无 Python 生成文本）；不含 `{...}` 的文本

## 输入输出定义

- **输入**：目标文本 `T`（含 shell 展开 `${...}`）＋ 需注入的 Python 变量集 `V`
  （如 `entry="dist/bin.js"`、`pkg="ts"`）。
- **输出**：落盘文件内容与 `T` 逐字节一致，仅 `V` 注入处被替换；文件权限 0o755。
- **判定**：生成的脚本在 `sh -n`（语法检查）下通过，且 `grep '${' 落盘文件` 能看到
  完整的 shell 展开原文。

## 示例

❌ 错误写法（实证：ts/10.9.2 适配中 bin/ 静默为空）：

```python
wrapper = (
    "#!/bin/sh\n"
    'TS_HOME="${TS_HOME:-$(dirname "$(dirname "$0")")/share/ts}"\n'
    'exec node "$TS_HOME/{entry}" "$@"\n'
).format(entry=entry)          # KeyError: 'TS_HOME'（或静默产出损坏内容）
```

✅ 正确写法（纯拼接，占位只在拼接点）：

```python
wrapper = (
    "#!/bin/sh\n"
    'TS_HOME="${TS_HOME:-$(dirname "$(dirname "$0")")/share/ts}"\n'
    'exec node "$TS_HOME/' + entry + '" "$@"\n'
)
```

✅ 等价替代（确需模板时，先转义再 format）：

```python
wrapper = (
    "#!/bin/sh\n"
    'TS_HOME="${{TS_HOME:-$(dirname "$(dirname "$0")")}}/share/ts}"\n'   # {{ }} 转义
    'exec node "$TS_HOME/{entry}" "$@"\n'
).format(entry=entry)
```

✅ 验证（本机 Windows 用 Git Bash 等价验证 wrapper）：

```sh
export PATH="/c/Program Files/nodejs:/usr/bin:$PATH"
"$PKG/bin/ts-node" --version        # 期望输出版本号而非空输出/127
```

## 关联

- 实证来源：ts 10.9.2（上游 ts-node）适配，见
  `DRAFT-ts-10.9.2-npm-peer-deps-pruned`（同轮次实证记录）。
- CI 关联：L0 的 `shell_env_var_in_run` 检查 `self.run()` 内 `${`；本条是其「写文件」
  侧的姊妹坑——CI 只查 run()，查不到 format() 生成的文件内容，必须 W4 自检。
