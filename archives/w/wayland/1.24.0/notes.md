# wayland 1.24.0 适配笔记

## 为什么升到 1.24.0（R37）

**不是追新版，是被 wlroots 0.20.1 的门槛逼上来的**：

```
wlroots-0.20.1/meson.build:  dependency('wayland-server', version: '>=1.24.0')
```

仓内原版本 1.22.0.1 不满足，且 libdrm/xkbcommon/pixman 三个门槛中
wayland 是**最难的一个**（wlroots 的顶层必需依赖）。实测确认：

```
$ meson setup build wlroots-0.20.1     # 用 1.22.0.1 的真实 .pc
Dependency wayland-server found: NO. Found 1.22.0.1 but need: '>=1.24.0'
```

## 编译环境

- 构建系统: meson
- 上游版本: 1.24.0
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 与 1.22.0.1 的差异（1.24.0 源码侧变化）

| 项 | 1.22.0 | 1.24.0 |
|---|---|---|
| 依赖 | libffi / expat / libxml2 | **相同**（无新增依赖）|
| meson 选项 | libraries / scanner / tests / documentation / dtd_validation / icon_directory | **相同**（无改名、无删除）|
| `b_ndebug` | 需强制 false（测试依赖 assert）| **同上** |
| 测试数 | 23 | 23 |

即 1.24.0 的**构建契约与 1.22.0 完全一致**，配方逻辑可整体沿用，无需新增 workaround。
这是版本升级里最好的情形——差异全在源码内部，不在构建界面。

## 沿用的三个 OHOS workaround（均在新版本上重新验证）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 clang / llvm-ar | HMDFS 软链接在 meson subprocess 中解析失败 | 注入 native file 的 `ar` 路径（zix/serd 先例）|
| 2 | `ffi.h` / `expat.h` / `libxml2` 头找不到 | 制品仓依赖的 `.pc` 里 `prefix` 指向 **build 目录**（`/conan2/p/b/libff…/p`），实际装在 `/conan2/p/libff…/p` | 复制 `.pc` 到 `fixed_pkgconfig/` 正则改写 `prefix` 并置顶 `PKG_CONFIG_PATH`（hyprutils/pixman 同款）|
| 3 | 测试 SIGABRT（mkdtemp failed）| `test-runner.c` 需 `XDG_RUNTIME_DIR`；未设时回退 `/tmp`，OHOS 沙箱不可写 | `build()` 内显式 `export XDG_RUNTIME_DIR=<TMPDIR>` |
| 4 | `documentation=true` 失败 | 沙箱无 Graphviz `dot` | `-Ddocumentation=false` |
| 5 | 测试断言失效 | conan 按 Release 生成 `b_ndebug='true'`（built-in options 覆盖 project options），`assert()` 被 NDEBUG 关掉 | 直接改写 native file 里 `b_ndebug = 'true'` → `'false'` |

> 第 5 条容易被忽略：`b_ndebug` 若只设 project_options 会被 conan 的 built-in
> options 覆盖，必须落到 native file 才生效。1.22.0.1 已踩过，本版沿用。

## 源码修改

**无补丁**（`patches: {}`）。所有修改都在 `conanfile.py` 的 `generate()` 内处理
（`.pc` prefix 修正 + native file 注入）。

## 依赖版本

- libffi/3.4.4
- expat/2.8.2
- libxml2/2.15.3

（三者均已在 ohpcd 发布，`conan download --only-recipe` 实测确认。）

## 上游测试（2026-09-16 实测）

`meson test` —— **26 项：18 passed / 8 failed**。

```
Ok:  18      Fail: 8
```

| # | 用例 | 结果 | 失败根因（实测）|
|---|------|------|------|
| 1-16 | wayland-egl abi check / cpp-compile / array / client / fixed / interface / list / map / signal / event-loop / resources / message / newsignal / headers / enum-validator / wayland-egl symbols | ✅ OK | — |
| 17 | `protocol-logger-test` | ❌ | `bind() Operation not permitted` → signal 11 |
| 18 | `proxy-test` | ❌ | `bind() EPERM` → `Assertion failed: socket`（proxy-test.c:103）|
| 19 | `socket-test` | ❌ | `bind() EPERM` |
| 20 | `compositor-introspection-test` | ❌ | `bind() EPERM` → `client != NULL` 断言（:118）|
| 21 | `connection-test` | ❌ | `data.value.h >= 0` 断言（:526）—— 该用例用**硬编码 `/tmp`** 做 `mkstemp`，而 OHOS 沙箱 `/tmp` 只读（实测 `OSError [Errno 30] Read-only file system`）|
| 22 | `queue-test` | ❌ | `bind() EPERM` → `Failed adding socket`（test-compositor.c:377）|
| 23 | `display-test` | ❌ | `bind() EPERM` |
| 24 | `sanity-test` | ❌ | `bind() EPERM` |
| 25 | `scanner-test` | ✅ OK | — |
| 26 | `os-wrappers-test` | ✅ OK | — |

**8 项失败全部是平台环境限制，非代码缺陷**，两类根因均已独立实测复现：

1. **AF_UNIX `bind()` 被拒**（7 项）——OHOS 沙箱对 Unix socket 绑定返回
   `PermissionError: [Errno 1] Operation not permitted`（用 3 行 Python 独立复现）；
2. **`/tmp` 只读**（1 项）——`connection-test.c:525` 硬编码
   `char f[] = "/tmp/wayland-tests-XXXXXX"` 后 `mkstemp`，实测该路径
   `OSError [Errno 30] Read-only file system`；`TMPDIR` 已设为可写目录，
   但该用例**不读 TMPDIR**，属上游硬编码。

以 try/except 记录真实通过率、不阻断构建（sord 先例），**未用 skip/xfail
掩盖**（R51）。

> 与 1.22.0.1 的差异：1.22.0.1 记录为 23 项（16 passed / 7 failed），
> 1.24.0 为 26 项（18 passed / 8 failed）。新增用例（`proxy-test`、
> `enum-validator-test`、`newsignal-test` 等）中的 `enum-validator-test`
> 通过，其余失败项与既有同类同因。

## 交付物

- libwayland-server.so
- libwayland-client.so
- libwayland-cursor.so
- libwayland-egl.so
- wayland-scanner（可执行）
- `wayland-client.pc` / `wayland-server.pc` / `wayland-cursor.pc` / `wayland-egl.pc`

## 注意事项

- `.pc` prefix 修正是**必需**步骤，不是优化——不改则头文件路径全错。
- native file 注入 `ar` 路径是**必需**步骤（meson subprocess 里 HMDFS 软链接不可用）。
- `b_ndebug=false` 必须落到 native file（仅设 project_options 无效）。
- `XDG_RUNTIME_DIR` 必须设为可写目录，否则测试 SIGABRT。

## 对下游的影响

本包是 `wlroots 0.20.1` 三个版本门槛之一：

| 依赖 | wlroots 要求 | 本包 | 状态 |
|---|---|---|---|
| **wayland** | **≥1.24.0** | **1.24.0** | ✅ 本次解决 |
| xkbcommon | ≥1.8.0 | 1.6.0 | ⏳ 待升（libxkbcommon 1.8.0）|
| wayland-protocols | ≥1.47 | 1.36.1 | ⏳ 待升（1.47）|
| libdrm | ≥2.4.129 | 2.4.133 | ✅ 已满足 |
| pixman-1 | ≥0.43.0 | 0.46.4.3 | ✅ 已满足 |
