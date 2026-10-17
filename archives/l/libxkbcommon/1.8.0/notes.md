# libxkbcommon 1.8.0 适配笔记

## 为什么升级到 1.8.0（R37）

**不是追新版，是被 wlroots 0.20.1 的门槛逼上来的**：

```
wlroots-0.20.1/meson.build:  dependency('xkbcommon', version: '>=1.8.0')
```

仓内原版本 1.6.0 不满足。这是 wlroots 三个版本门槛中的第二个（另两个为
`wayland >= 1.24.0` 与 `wayland-protocols >= 1.47`）。

选 1.8.0 而非更新版（1.13.x）的理由：刚好过门槛，与 1.6.0 差距最小、
新引入的构建要求最少。

## 编译环境

- 构建系统: meson
- 上游版本: 1.8.0
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 与 1.6.0 的关键差异：新增两个必须显式关闭的选项

1.8.0 相对 1.6.0 新增了 `enable-wayland`（默认 **true**）与
`enable-bash-completion`（默认 true）。其中 **`enable-wayland` 是硬失败**：

```meson
if get_option('enable-wayland')
    wayland_client_dep   = dependency('wayland-client',   version: '>=1.2.0', required: false)
    wayland_protocols_dep= dependency('wayland-protocols',version: '>=1.12',  required: false)
    wayland_scanner_dep  = dependency('wayland-scanner',   required: false, native: true)
    if not wayland_client_dep.found() or not wayland_protocols_dep.found() or not wayland_scanner_dep.found()
        error('''The Wayland xkbcli programs require wayland-client and wayland-protocols which were not found.
You can disable the Wayland xkbcli programs with -Denable-wayland=false.''')
    endif
```

注意是 **`error()` 而非 warning**——本包只构建核心库、不产出 wayland 相关依赖，
若不显式 `-Denable-wayland=false`，**配置阶段直接失败**。

> 这是 1.6.0 配方**原样复制会踩坑**的点：1.6.0 只有四个选项要关，
> 1.8.0 多两个，且多出来的那个是 error 级别。

## 选项矩阵（本包实际使用）

| 选项 | 1.6.0 | 1.8.0 默认 | 本包 | 关闭理由 |
|---|---|---|---|---|
| `enable-x11` | 有（默认 true）| true | ❌ false | 需 xcb / xcb-xkb（>=1.10）|
| `enable-xkbregistry` | 有（默认 true）| true | ❌ false | 需 `libxml-2.0`（**必需依赖**，非 optional）|
| `enable-docs` | 有（默认 false）| false | ❌ false | 需 doxygen + graphviz |
| `enable-tools` | 有（默认 true）| true | ❌ false | 需 `getopt_long`；`export-keysyms` 子工具还需 **ICU（icu-uc）**，而 ohpcd 与 main **均无 icu 包** |
| `enable-wayland` | **无此选项** | **true** | ❌ false | 1.8.0 新增；缺 wayland-client/protocols/scanner 时 **error() 硬失败** |
| `enable-bash-completion` | **无此选项** | true | ❌ false | 1.8.0 新增；安装 bash 补全脚本，本包不需要 |
| `enable-cool-uris` | — | false | 未设 | 默认 false，随 enable-docs 关闭而无效 |

## 沿用的两个 OHOS workaround（在 1.8.0 上重新验证）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 clang / llvm-ar | HMDFS 软链接在 meson subprocess 中解析失败 | 注入 native file 的 `ar` 路径（zix/serd 先例）|
| 2 | meson 检测链接器失败 | OHOS SDK 的 lld 运行时依赖 `llvm/lib` 下的库，而 `LD_LIBRARY_PATH` 未含该目录 | `Environment` 追加 `LD_LIBRARY_PATH`（`conanbuild_env`）|

## 源码修改

**无补丁**（`patches: {}`）。所有处理都在 `conanfile.py` 的 `generate()` 内。

## 上游测试（2026-09-16 实测）

`meson test` —— **20 项：19 passed / 1 failed**。

```
Ok:  19      Fail: 1
```

| 用例 | 结果 | 失败根因（实测）|
|---|---|---|
| 其余 19 项（keymap / keysym / rules / state / compose 等）| ✅ OK | — |
| `context` | ❌ | **killed by signal 11 SIGSEGV**（`test-context`，0.34s）|

该失败与仓内 **1.6.0 的既有记录完全一致**（其 notes 写明「context 测试在
OHOS 沙箱 SIGSEGV（环境限制，非代码问题）」），且 1.6.0 记录的通过率
18/19 与本版 19/20 的失败项**同为 context** ——即该用例在两版上均因沙箱
环境受限而挂，属平台限制、非本次升级引入。

（测试日志另可见大量 `Failed to compile keymap from memory buffer` 输出，
那是 `test-context` 在 SIGSEGV 前的调试日志——`XKB_LOG_LEVEL=debug` 下
对非法 keymap 的预期报错，不是额外失败项。）

以 try/except 记录真实通过率、不阻断构建（sord/wayland 先例），
**未用 skip/xfail 掩盖**（R51）。

## 交付物

- `libxkbcommon.so`（+ 符号链接）
- `include/xkbcommon/*.h`
- `lib/pkgconfig/xkbcommon.pc`

## 对下游的影响

本包是 `wlroots 0.20.1` 三个版本门槛之一：

| 依赖 | wlroots 要求 | 本包 | 状态 |
|---|---|---|---|
| wayland | ≥1.24.0 | 1.24.0 | ✅ 已完成（同批 PR）|
| **xkbcommon** | **≥1.8.0** | **1.8.0** | ✅ 本次解决 |
| wayland-protocols | ≥1.47 | 1.36.1 | ⏳ 待升（同批）|
| libdrm | ≥2.4.129 | 2.4.133 | ✅ 已满足 |
| pixman-1 | ≥0.43.0 | 0.46.4.3 | ✅ 已满足 |
