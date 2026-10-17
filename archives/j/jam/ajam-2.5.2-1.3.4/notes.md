# jam ajam-2.5.2-1.3.4 适配笔记

## 编译环境
- 目标：aarch64-unknown-linux-ohos（conan profile `ohos-aarch64`，host=build）
- 构建系统：纯 C 单文件构建（无 configure 外部库依赖）
- 编译器：clang 15.0.4（aarch64-unknown-linux-ohos，来自 /data/service/hnp/bin）
- 来源：方式二（依赖库）—— 供 argyll-cms 作为构建工具使用

## 关键适配决策

### 上游自举链在 OHOS 沙箱下不可用 → 改用直接链接

上游顶层 Makefile 的 `all` 目标走自举链：

```make
all: jam0
	chmod a+w jambase.c
	./jam0        # jam0 会派生子进程 clang 来编译各 .o
```

问题：在 OHOS 沙箱下，**新鲜编译出来的用户态二进制在派生子进程时无法成功运行 clang-15**（clang-15 以该二进制为父进程时静默 `exit 1`，无任何输出；而预装系统二进制如 `make` 可正常派生 clang）。因此 `./jam0` 调用的 `Cc` 动作全部报 failed。

诊断证据：
- `clang --version` 在交互 shell 里正常（exit 0）
- 由任何新编译 C 程序 `fork+execvp` 出的 clang-15 均 `exit 1`（静默）
- 预装 `/data/service/hnp/bin/make` 走 `make → /bin/sh → clang` 正常

### 解决：绕开自举链，直接链接成单个 jam

```python
# 1) 用 argyll Jambase 重新生成 jambase.c（mkjambase 是纯 C，不派生 clang，可执行）
clang -O2 -o mkjambase mkjambase.c
./mkjambase jambase.c Jambase
# 2) 把所有 C 源一次链接成单个 jam（无任何子进程 clang 调用）
clang -O2 -o jam builtins.c ... variable.c
```

产物 `jam` 可正常执行 `jam -v`（输出 `Argyll-Jam 2.5.2 ... Argyll JAMBASE 1.3.3`），并能执行 shell 动作（`actions echo_hello { echo ... }` 等已验证）。

### 编译告警（不影响构建）

- 大量 `-Wparentheses`（`if( x = y )` 老式写法）—— 仅告警，不作为错误
- 少量隐式声明（`vfork`/`execvp`/`wait` 等）—— libc 提供符号，链接正常
- `mkjambase.c` 的 `main` 缺类型说明 —— 仅告警

不修改源码（除非必要），保持与上游行为一致。

## 版本号说明

| 来源 | 版本 |
|------|------|
| Argyll 官方要求 | "Jam 2.5" |
| 定制包版本 | ajam-2.5.2-1.3.4（patchlevel `VERSION 2.5.2`，`JAMBASE_VERSION 1.3.3`） |
| conan 包版本 | ajam-2.5.2-1.3.4（与定制包一致） |

## 依赖版本

无第三方依赖（仅 C 标准库）。

## 验证结果

```bash
$ ./jam -v
Argyll-Jam 2.5.2. OS=LINUX. Argyll JAMBASE 1.3.3.
(C) 1993-2003 Christopher Seiwald, see www.freetype.org/jam/

$ file bin/jam
bin/jam: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/jam | Argyll-Jam 构建工具可执行文件（约 215KB，PIE，musl） |
