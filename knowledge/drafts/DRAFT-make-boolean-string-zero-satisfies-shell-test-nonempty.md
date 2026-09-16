# DRAFT-make-boolean-string-zero-satisfies-shell-test-nonempty — Make 以字符串 `"0"` 传布尔开关给 shell 脚本时 `test -n "$VAR"` 恒为真

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: 🟡 medium | **Category**: make / shell / testing / upstream

## 症状

手写 Makefile 调用 shell 测试脚本、以 `$(VAR)` 传布尔开关时，**未启用**的可选组件分支照样执行，通常表现为去加载一个不存在的插件：

```
dd_rescue: (fatal): Could not load plugin ./libddr_lzo.so
                    (No such file or directory)
make[1]: *** [Makefile:828: check_crypt] Error 1
make: *** [Makefile:666: check] Error 2
```

Makefile 侧这样传：

```make
check_crypt: $(TARGETS) test_aes
	HAVE_LZMA=$(HAVE_LZMA) HAVE_LZO=$(HAVE_LZO) HAVE_OPENSSL=$(HAVE_OPENSSL) \
	HAVE_AES=$(HAVE_AES) ./test_crypt.sh
```

脚本侧守卫这样写（`test_crypt.sh:128`）：

```sh
if test -n "$HAVE_LZO"; then
```

**此时即便 LZO 完全未启用（`HAVE_LZO=0`），该分支依然进入。**

## 根因：值语义被误当存在性语义

Make 变量展开后是**文本**。`HAVE_LZO=0` 传给 shell，得到字符串 `"0"` —— 它**非空**。

| 侧 | 写法 | 该侧的理解 |
|----|------|-----------|
| Make | `HAVE_LZO=0` | "关闭 LZO"（**值语义**）|
| shell | `test -n "$HAVE_LZO"` | "变量是否有值"（**存在性语义**）|

`test -n` 只看"字符串长度 > 0"，`"0"` 长度为 1 ⇒ **真**。于是 `false` 被当成 `true`。

```sh
$ HAVE_LZO=0 sh -c 'if test -n "$HAVE_LZO"; then echo TRUE; else echo FALSE; fi'
TRUE                       # ← 错误
$ HAVE_LZO=0 sh -c 'if test "$HAVE_LZO" = "1"; then echo TRUE; else echo FALSE; fi'
FALSE                      # ← 正确
```

### 为什么容易被忽略

**同一工程里两种写法并存**，而 Makefile 侧那种是"对"的：

```make
# Makefile:646 —— 按值比较，正确
if test $(HAVE_LZO) = 1; then $(MAKE) check_lzo; fi
```

```sh
# test_crypt.sh:128 —— 按存在性判定，错误
if test -n "$HAVE_LZO"; then
```

Makefile 侧写得对，会让人默认"这个工程的布尔开关处理是可靠的"，从而不去看 shell 侧。

## 修复：守卫按**值**比较

```sh
if test "$HAVE_LZO" = "1"; then      # ✅
if test -n "$HAVE_LZO"; then         # ❌ "0" 也为真
```

修的是**守卫**，不是"顺手把选项打开来绕过" —— 后者会把"未启用"变成"已启用"，**改变交付物内容**。

## ⚠️ 关键边界：不能一刀切

同一脚本里还有两处 `test -n`，**语义正确、不能改**：

```sh
# test_crypt.sh:286/289
HAVE_AESNI=`grep " sse4" /proc/cpuinfo | grep " aes "`     # 来自探测命令
HAVE_AESARM=`grep " pmull " /proc/cpuinfo`
...
if test -n "$HAVE_AESNI"; then ...
```

**判据是变量的来源**：

| 变量来源 | 正确语义 | 判定方式 |
|---------|---------|---------|
| 由 Make `$(VAR)` 传入（如 `HAVE_LZO`）| **值语义**（0/1 表示开关）| `test "$VAR" = "1"` |
| 由探测命令得出（如 `/proc/cpuinfo` grep）| **存在性语义**（非空=具备该能力）| `test -n "$VAR"` ✅ |

对第二类改用 `= "1"` 反而是错的（探测得到的是内容片段，不是 `1`）。

## 排查方法

```sh
# 找出所有"存在性判定"的守卫，逐个核对变量来源
grep -n 'test -n "\$HAVE_\|test -n "\$[A-Z_]*"' test_*.sh
# 与被调用的 Makefile 规则对照，看哪些变量是 $(VAR) 传进来的
grep -n '\$(HAVE_[A-Z_]*)\|=\$(HAVE_' Makefile
```

## 实证

**dd_rescue 1.99.22**（`feat/dd_rescue-1.99.22`）：

1. `make check` 首跑停在 `check_crypt`、`Error 126`（另一独立问题：6 个 `test_*.sh` 的 `#!/bin/bash` 在 OHOS 不存在）；修 shebang 后变为 `Error 1`；
2. 定位 `test_crypt.sh:128/150` 守卫 `test -n "$HAVE_LZO"`，而 `Makefile:828` 以 `HAVE_LZO=$(HAVE_LZO)` 传入字符串 `"0"`；
3. 反例验证：`HAVE_LZO=0 sh -c 'test -n "$HAVE_LZO"'` 退出码 0（为真）；
4. 改为 `= "1"` 后单跑 `make check_crypt` **rc=0**；完整 `make check` **rc=0、Error 数 0、10 个子套件全部通过**。

## 与既有条目的差异

| 既有条目 | 关系 |
|---------|------|
| `DRAFT-pkgm4-preset-nonempty-gate`（`test -n "$VAR_CFLAGS"` 空串=未预置）| **方向相反**：那条讲"空串被判假"（存在性语义正确，只是与"预置"意图不符）；本条讲"**非空但为假值 `"0"`** 被判真" —— 是**跨语言值语义/存在性语义错配** |
| `DRAFT-libpfm-4.13.0-make-sys-linux-gate` | 同为"Make 门控在 OHOS 失效"，但那条是 **`ifeq ($(OS),Linux)` 平台门控静默不成立**（Make 内部比较），本条是 **Make→shell 传参的布尔语义错配**（跨进程边界）|
| `DRAFT-makefile-origin-guard-dep-injection` | 讲探测失败后用 Make 变量注入，未涉及 `test -n` 语义 |

> 查重（2026-09-12）：`test -n "$HAVE` = **0**；`HAVE_LZO` = **0**；字符串 `"0"` 判定相关 = **0**。

## 禁止

- ❌ **"把选项打开就能过"** —— 用启用 LZO 绕开该失败，会改变交付物（多出插件与依赖），掩盖真正的问题
- ❌ **一刀切把所有 `test -n "$VAR"` 改成 `= "1"`** —— 会破坏来自探测命令的变量（`HAVE_AESNI`/`HAVE_AESARM`），须先判断变量来源
