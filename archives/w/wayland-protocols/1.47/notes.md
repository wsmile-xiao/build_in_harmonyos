# wayland-protocols 1.47 适配笔记

## 为什么升级到 1.47（R37）

**不是追新版，是被 wlroots 0.20.1 的门槛逼上来的**：

```
wlroots-0.20.1/meson.build:  dependency('wayland-protocols', version: '>=1.47')
```

仓内原版本 1.36.1 不满足。这是 wlroots 三个版本门槛中的第三个
（另两个为 `wayland >= 1.24.0`、`xkbcommon >= 1.8.0`，均同批解决）。

## 关键变更：内嵌静态 scanner 必须换成 wayland 1.24.0 源码

1.36.1 的配方从 **wayland 1.22.0** 源码编译静态 `wayland-scanner`。
**1.47 不能沿用 1.22.0**，因为它在启用测试时对 scanner 有硬性版本要求：

```meson
# wayland-protocols-1.47/meson.build:11
dep_scanner = dependency('wayland-scanner',
    version: get_option('tests') ? '>=1.23.0' : '>=1.20.0',
    native: true,
    fallback: 'wayland'
)
```

`tests=true` 时要求 `wayland-scanner >= 1.23.0`。若仍用 1.22.0 源码编译，
`.pc` 里声明的版本号不达标，meson 直接报依赖版本错误。

因此 `conandata.yml` 的 `scanner_sources` 改为 wayland **1.24.0** 源码，
且 `wayland-scanner.pc` 的 `Version:` 写作 `1.24.0`（同时满足 `>=1.23.0`）。

> 这是"1.36.1 配方原样复制会踩坑"的第二处（第一处是上面这个版本门槛本身）。

## 为什么要静态 scanner（沿用 1.36.1 的既有结论）

HMDFS **禁止动态加载共享库**：`wayland` 包自带的 `wayland-scanner` 链接
`libexpat.so` / `libxml2.so`，在本平台无法执行。故从源码编译一个
`-static` 的 scanner（仅依赖 libc），并用它生成协议代码。

同理，测试可执行文件通过静态 `libwayland-protocol.a` 获得
`wl_surface_interface` 等接口**数据符号**，不链接任何共享库。

## 编译环境

- 构建系统: meson
- 上游版本: 1.47
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 类型: 纯数据包（交付 XML + .pc）

## 与 1.36.1 的差异汇总

| 项 | 1.36.1 | 1.47 |
|---|---|---|
| `scanner_sources` | wayland **1.22.0** | wayland **1.24.0**（1.47 要求 scanner ≥1.23.0）|
| `wayland` 依赖 | 1.22.0 | **1.24.0** |
| `wayland-scanner.pc` 的 Version | 1.22.0 | **1.24.0** |
| 协议 XML 扫描目录 | stable / staging / unstable | stable / staging / unstable / **experimental**（1.47 的 `protocol_files` 含 experimental）|
| 协议 XML 数量 | 44 | **57**（+13）|
| `.pc` 模板 | 相同（`pkgdatadir=${pc_sysrootdir}${datarootdir}/…`）| 相同，仍需修正 prefix |

## 沿用的 OHOS workaround

| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | meson 找不到 llvm-ar | 注入 native file 的 `ar` 路径（zix/serd 先例）|
| 2 | `dependency('wayland-scanner', native: true)` 找不到 | 在 native file 的 `[paths]` 里注入 `pkg_config_path` 指向自造 `.pc` |
| 3 | 静态 scanner 链接缺 expat | `_find_expat_static()` / `_find_expat_include()`：按序尝试 SDK 自带 `expat_2.7.3` 与依赖包内路径，找不到即 `ConanException`（**不静默降级**）|
| 4 | `.pc` 的 prefix 指向构建前缀 | `package()` 内正则改写为包真实路径，使 `pkg_get_variable(WAYLAND_PROTOCOLS_DIR)` 有效 |

## 源码修改

**无补丁**（`patches: {}`）。所有处理都在 `conanfile.py` 内。

## 上游测试（2026-09-16 实测）

`meson test` —— **179 项：179 passed / 0 failed**。

```
Ok:  179      Fail: 0
```

三类覆盖（对照 1.36.1 的 131 项，1.47 因协议数 44→57 而增至 179 项）：

| 类别 | 内容 |
|---|---|
| `scan-*` | 每个协议 XML 过一遍 scanner（用自编译的静态 wayland-scanner）|
| `test-build-pedantic-*` | 每个协议以 `-std=c99 -pedantic -Wall -Werror` 编译（仅 include 头文件 + 静态链接接口数据，不链共享库）|
| `test-build-cxx-*` | 同上，C++ 编译器（`xdg-foreign-unstable-v1` 按上游条件跳过）|

**179/179 全过**，无沙箱受限项——因为本包的测试不依赖 socket/网络，
只用静态 scanner 做文本处理与编译，故不受 `bind()` EPERM 影响
（与 wayland / libxkbcommon 的沙箱受限情形不同）。

以 try/except 包裹仅为防御性处理，**未用 skip/xfail 掩盖**（R51）。

## 交付物

- `share/wayland-protocols/{stable,staging,unstable,experimental}/*/*.xml`
- `include/wayland-protocols/`（scanner ≥1.22.90 时提供的头文件）
- `share/pkgconfig/wayland-protocols.pc`（prefix 已修正）

## 对下游的影响

本包是 `wlroots 0.20.1` 三个版本门槛之一：

| 依赖 | wlroots 要求 | 本包 | 状态 |
|---|---|---|---|
| wayland | ≥1.24.0 | 1.24.0 | ✅ 已完成（同批）|
| xkbcommon | ≥1.8.0 | 1.8.0 | ✅ 已完成（同批）|
| **wayland-protocols** | **≥1.47** | **1.47** | ✅ 本次解决 |
| libdrm | ≥2.4.129 | 2.4.133 | ✅ 已满足 |
| pixman-1 | ≥0.43.0 | 0.46.4.3 | ✅ 已满足 |

三个版本门槛全部达标后，wlroots 0.20.1 的**顶层必需依赖即全部满足**，
可进入 wlroots 本体适配（其后端可选依赖 gbm / libudev / libseat /
libinput / hwdata / libdisplay-info 均已有方案或已解决）。
