# wayland-protocols 1.48 适配笔记

## 为什么升级到 1.48（R37）

**不是追新版，是被 kwin 6.7.2 的门槛逼上来的**：

```
kwin-6.7.2/CMakeLists.txt:  find_package(WaylandProtocols 1.48)
```

仓内原版本 1.47 不满足。本包是鸿蒙 PC KDE Plasma 合成器依赖链的第一环：

```
wayland-protocols 1.48 → plasma-wayland-protocols 1.21.0
                       → kwayland 6.7.2 → kwin 6.7.2
```

## 1.47 → 1.48 上游变更盘点

1. **4 个新协议目录**：`xdg-session-management`（staging）与 `xx-cutouts` /
   `xx-keyboard-filter` / `xx-zones`（experimental）。协议字典协议文件数
   60 → 64（stable 5 / staging 31 / unstable 22 / experimental 6，与 release
   tarball 64 个 XML 一一对应），上游测试数 179 → 191（+4 协议 × 3 类 =
   +12：scan + pedantic-c99 + cxx）。静态 scanner 的协议遍历覆盖四目录，
   新协议自动纳入 libwayland-protocol.a 与测试集。
2. **.pc 生成迁移到 pkgconfig.generate()**：上游删除
   wayland-protocols.pc.in / wayland-protocols-uninstalled.pc.in 两个模板，
   改用 meson 内置 pkgconfig.generate(dataonly)。生成的 .pc 仍写作
   `pkgdatadir=${pc_sysrootdir}${datarootdir}/wayland-protocols`，
   与 1.47 配方 package() 中"prefix 改写为包真实路径"的修正逻辑完全兼容，
   该修正继续保留。
3. **tests/meson.build 变量改名**：`wayland_protocols_srcdir` →
   `meson.project_source_root()`，纯改名，无逻辑变化。
4. **scanner 版本门槛不变**：tests=true 时仍要求
   `dependency('wayland-scanner', version: '>=1.23.0')`，故继续用
   wayland 1.24.0 源码编译静态 scanner。

## 内嵌静态 scanner 的既有结论（沿用 1.47）

1.36.1 的配方从 **wayland 1.22.0** 源码编译静态 `wayland-scanner`。
**1.47 起不能沿用 1.22.0**，因为启用测试时对 scanner 有硬性版本要求：

```meson
# wayland-protocols-1.48/meson.build:11
dep_scanner = dependency('wayland-scanner',
    version: get_option('tests') ? '>=1.23.0' : '>=1.20.0',
    native: true,
    fallback: 'wayland'
)
```

`tests=true` 时要求 `wayland-scanner >= 1.23.0`。若仍用 1.22.0 源码编译，
`.pc` 里声明的版本号不达标，meson 直接报依赖版本错误。

## 为什么要静态 scanner（沿用 1.47 的既有结论）

HMDFS **禁止动态加载共享库**：`wayland` 包自带的 `wayland-scanner` 链接
`libexpat.so` / `libxml2.so`，在本平台无法执行。故从源码编译一个
`-static` 的 scanner（仅依赖 libc），并用它生成协议代码、跑上游
meson test（scan 64 + pedantic-c99 64 + cxx 63，共 191 项）。

## 0001：HMDFS 禁 exec 脚本 → 解释器前缀（真机实测补丁）

2026-09-30 真机 conan-verify 首次 G2 失败（code=126）：

```
FAILED: [code=126] tests/test-build-pedantic-...c
/bin/sh: .../b/tests/replace.py: Permission denied
```

HMDFS 对 exec() 脚本文件一律 EACCES（chmod +x 无效，xcb-util /
automake 1.19 同坑）。上游 tests/meson.build 以
`find_program('scan.sh')` / `find_program('replace.py')` 找到脚本后
**直接 exec**（custom_target 与 meson test 均是），故在平台必挂。

0001 补丁（tests/meson.build，4 处）：

1. `sh = find_program('sh')`，scan 测试改 `test(name, sh, args: [scan.sh
   全路径, protocol_path])`（SCANNER env 不变）；
2. `py = find_program('python3')`，replace_command 改
   `[py, replace.full_path(), ...]`（pedantic-c99 / cxx 两个生成器共用）。

测试逻辑零修改：脚本内容逐字未动，扫描四模式 --strict、
pedantic C99 编译参数、C++ 编译参数全部保留；191 项测试全量执行。

> G0 的 E090 预警（meson 把 host 识别为 'harmonyos' 而非 'linux'）与本
> 包无关：wayland-protocols 1.48 的 meson.build / tests/meson.build 无任何
> `host_system == 'linux'` 门控（已 grep 证实），configure 与 510 个构建
> 目标全部正常生成。

## 上游测试计数（实测口径）

- 协议字典（meson.build 四字典直计数）：stable 5 + staging 31 +
  unstable 22 + experimental 6 = **64 协议文件**；
- tests/meson.build 对每个 protocol_file 生成 **1 scan**（scan.sh 四模式
  --strict）+ **1 pedantic-c99**（client/server 头 + private-code，
  -std=c99 -pedantic -Wall -Werror）+ **1 cxx**（client/server 头，
  -Wall -Werror；`xdg-foreign-unstable-v1` 除外）；
- 合计 **64 + 64 + 63 = 191 项**，构建期 `meson test` 直接执行（静态
  scanner + 静态 libwayland-protocol.a 使全部测试可在 OHOS 平台运行，
  1.47 配方 MANIFEST 中 "skipped, scanner 不在 OHOS" 的旧声明不实）。

## test_package：消费者 E2E（本 MR 重写）

旧 test_package 仅有 4 个纯存在性检查（.pc 存在 + stable/ 目录存在），
本 MR 重写为消费者端到端测试，消费链与真实下游一致（kwayland /
plasma-wayland-protocols 同款）：

1. test_package 取得 wayland 1.24.0 源码（与主配方同源、sha256 校验），
   编译静态 wayland-scanner；**注意 conan 2.29 对 in-place test_package
   不调用 source()（真机实测：主配方 source() 执行而 test_package 的
   跳过），下载放在 build() 开头经 get() 落盘 build_folder**；
   **CI#65173 修复**：同一 run 内 test_package 的 get() 是对
   gitlab.freedesktop.org 的第二次下载请求，被 429 限流（主配方第一次
   下载成功），conan-build-test 挂 FileNotFoundError wayland-src/config.h。
   改为优先复用主配方 source() 已下载的缓存副本——被测试包的
   package_folder（`p/<hash>/p`）与 source_folder（`p/<hash>/s`）是
   conan 缓存的兄弟目录，主配方把 scanner 源码解压在
   `s/wayland-scanner-src`，直接复制复用零二次请求；取不到才回退
   get() 下载（sha256 校验不变）；
2. 用该 scanner 对包内 **7 个代表协议** XML（stable ×2 / staging ×3
   含 1.48 唯一进入安装集的新协议 xdg-session-management / unstable ×2）
   生成 client-header + private-code，并生成闭包（wayland.xml 核心接口
   wl_surface/wl_seat/wl_output；xdg_toplevel 引用由同批 xdg-shell 提供）。
   **上游 installed_protocol_files 仅 stable/staging/unstable，
   experimental 设计不安装（真机实测包内无 experimental/ 目录）**——
   E2E 是消费者视角测试，只消费安装集；3 个 experimental 新协议
   （xx-cutouts / xx-keyboard-filter / xx-zones）由上游 191 项测试覆盖
   （scan/pedantic/cxx 对全部 64 个源 XML 执行）；
3. `consumer_e2e.c` 与生成代码一起编译链接，运行时逐例核验编译态接口
   数据与包内 XML 定义一致（接口名 / 版本号 / 请求计数 / XML 原样包含
   name 与 version 属性）：**7 用例 × 4 检查点 = 28 项**，逐例
   TEST PASS/FAIL + 末行 TEST SUMMARY，任一失败退出码 1；
4. pkgdatadir 由 test_package 消费 wayland-protocols.pc 定位（VAR=value
   解析 + `${var}` 递归展开，验证 package() 的 prefix 修正真实生效）。

本地等价环境实测（Windows MinGW + 同源静态 scanner，2026-09-30）：
- 上游 191 项：**191/191 PASS**（平台差异仅 3 处 shim：PE 无 visibility
  → -Wno-attributes / WL_EXPORT 置空；MinGW sys/types.h 缺 uid_t/gid_t
  → typedef 补充。OHOS 为 ELF + musl，均原生支持，无需任何改动）；
- 消费者 E2E：**28/28 PASS**，RC=0。
真机实测（2026-09-30，ohos-aarch64，conan 2.29.1，conan-verify 第 6 轮
最终干净构建，fork `a59d747ec8`，完整日志 conan-create.log 留存设备）：

- 上游 191 项：构建期 `meson test` 实测 **Ok: 191, Fail: 0**（scan 64 +
  pedantic-c99 64 + cxx 63，零跳过；701 个构建目标全部产出）；
- 消费者 E2E：**TEST SUMMARY: 28 passed, 0 failed**，退出码 0；
- conan-verify 全门禁 PASS（G0/G1/G2/G3/G4 + L2/L4/L5），verdict 可标记
  published。

关键摘录见 `reports/device-test-evidence.md`。
