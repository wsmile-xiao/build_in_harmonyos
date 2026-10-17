# E543（草稿）: conan self.run 传 -D宏='带引号 C 字符串' 时引号被 shell 吞/转义错乱

## 基本信息
- **严重度**: 2
- **类别**: build-system, quoting, shell, conan
- **作者**: choose-mirror 2.137 适配子任务
- **来源 PR**: (本 PR)
- **来源 commit**: (待提交后回填)

## 错误特征
```
use of undeclared identifier 'aarch64'|expanded from here.*-DARCH_TEXT aarch64|missing terminating '"' character.*-Winvalid-pp-token
```

## 根因分析
conan 的 `ConanFile.run(shell=True)` 经 `/bin/sh -c` 执行，命令字符串**先被 shell
解析一次**再交给编译器。当 `-D` 宏值本身需要是一个 C 字符串字面量（即要传递字面
双引号给预处理器，例如 Makefile 里的 `-DARCH_TEXT='"$(DEB_HOST_ARCH)"'`）时：

1. **裸双引号** `-DARCH_TEXT="aarch64"`：shell 把这对双引号当作引号定界符剥离，
   编译器收到 `#define ARCH_TEXT aarch64`（裸标识符）→ `use of undeclared
   identifier 'aarch64'`。
2. **反斜杠转义**（Python 层 `\\\"`）：需要在 Python 字符串层与 shell 层**同时**
   转义正确，层数错一位就退化成 `\"` 原样进编译器 → `missing terminating '"'`
   （choose-mirror 2.137 实测）。脆弱、难审计。
3. **单引号壳** `-DARCH_TEXT='"aarch64"'`：POSIX/OHOS `/system/bin/sh` 下单引号
   内一切字符原样保留，shell 剥掉外层单引号后，编译器恰好收到带 C 引号的
   `"aarch64"`。**唯一稳健形态。**

## 推荐方案
**方法**: single-quote-shell-wrap-cstring-macro

**说明**: 在 conanfile `build()` 的编译命令里，把含 C 字符串字面量的 `-D` 宏值用
**单引号壳**包住。Python 源码写作：
```python
cflags += " -DARCH_TEXT='\"aarch64\"'"   # 外层 Python 双引号、中层 shell 单引号、内层 C 双引号
```
shell 剥单引号 → 编译器收到 `-DARCH_TEXT="aarch64"`（带 C 引号）。

**验证/命令**:
```
# 命中本模式的证据（conan create 日志）
grep -nE "use of undeclared identifier|missing terminating" <conan-create.log>
# 正确形态自检：编译器收到的是带引号字面量
clang -DARCH_TEXT='"aarch64"' -E -x c /dev/null >/dev/null   # 无错即形态正确
```

## 关键词
conan self.run, /bin/sh -c, shell quoting, -D 宏, C 字符串字面量, 双引号被吞,
单引号壳保护, use of undeclared identifier, missing terminating, invalid-pp-token,
ARCH_TEXT, Makefile -D 宏传参, 交叉编译

## 实测记录（choose-mirror 2.137, OHOS aarch64）
- `-DARCH_TEXT="aarch64"`（裸）→ `error: use of undeclared identifier 'aarch64'`
- `-DARCH_TEXT=\\\"aarch64\\\"`（反斜杠，Python 层 `\\\\\\\"`）→ `warning: missing terminating '"' character` / `#define ARCH_TEXT \"aarch64\"`
- `-DARCH_TEXT='"aarch64"'`（单引号壳）→ 编译通过，ARCH_TEXT 正确展开为 C 字符串

---
*与 DRAFT-E551 的区分：E551 聚焦 bash/libtool 复杂命令的多重转义；本条聚焦单个
`-D` 宏 C 字符串字面量的单层引号保护，是更常见、更独立的触发形态。*
