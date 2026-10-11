# DRAFT 知识条目（md 成对版）— test_package 里别用 str.format 拼 shell 命令：`${VAR:-default}` 会被当成格式字段

> Status: DRAFT | 来源: tetraproc/0.9.2 真机 shadow CI 2026-10-04（r2 第 7 轮）

## 使用说明

test_package / 配方的 `self.run()` 里拼 shell 命令时，只要字符串含
`${VAR}`、`${VAR:-default}` 这类 shell 参数展开，**禁止 `str.format()`/
f-string**：花括号会被 Python 当格式字段解析，运行期抛
`KeyError: 'CONFIG_SHELL'`（或 IndexError/ValueError），失败点在 conanfile
的行号，与真实 shell 语义无关。用字符串拼接或 `%` 格式化。

## 适用范围

- 所有 `self.run(...)` 内嵌 shell 语法的场景：test_package、build()/package()
  中的环境变量默认值、`$(...)` 之外的 `${...}` 展开。
- 典型：OHOS 上 `CONFIG_SHELL="${CONFIG_SHELL:-/data/service/hnp/bin/bash}"`。

## 输入 / 输出

- 输入：含 `${...}` 的命令模板 + `.format()`/f-string。
- 输出：失败指纹 `KeyError: '<变量名>'`（变量名恰好是 shell 变量名）→ 改拼接。

## 失败指纹与修复

```text
ERROR: <pkg>/<ver> (test package): Error in test() method, line NN
	'CONFIG_SHELL="{...}" TETRAFILE="{tf}" ...'.format(
	KeyError: 'CONFIG_SHELL'
```

```python
# ❌ 错: format 把 ${CONFIG_SHELL:-...} 当字段
self.run('CONFIG_SHELL="${CONFIG_SHELL:-/data/.../bash}" TETRAFILE="{tf}"'.format(tf=f))

# ✅ 对: 纯拼接（或 %s）
self.run('CONFIG_SHELL="${CONFIG_SHELL:-/data/.../bash}" TETRAFILE="'
         + str(tetrafile) + '" bash "' + script + '"', env="conanrun")
```

## 示例（本次实证）

tetraproc/0.9.2 真机第 7 轮：`KeyError: 'CONFIG_SHELL'` → 改拼接后该步通过。

## 查重边界

`DRAFT-windows-cross-host-ohc-toolchain-binsh-and-shlex-quoting` 讲 Windows
宿主下 bin/sh 与 shlex 的**引号传递**；本条讲 Python 格式化语法与 shell 参数
展开的**花括号冲突**，失效面不同。全库无既有条目覆盖。
