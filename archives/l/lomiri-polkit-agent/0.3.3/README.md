# lomiri-polkit-agent 0.3.3 — HarmonyOS PC 适配说明

## 1. 软件简介

[lomiri-polkit-agent](https://gitlab.com/ubports/development/core/lomiri-polkit-agent) 是
Lomiri（Ubuntu Touch 桌面）的 **PolicyKit 会话认证代理**：向 polkit 注册
`org.freedesktop.PolicyKit1.AuthenticationAgent` 实现，在用户会话内弹出认证对话框；
由 D-Bus 会话总线按 systemd user unit 激活，属会话服务而非命令行工具。

- 上游版本：**0.3.3**（GitLab 标签为 `0.3.3`，**无 `v` 前缀**；`/-/archive/v0.3.3/...` 会 404）
- 上游源码：`https://gitlab.com/ubports/development/core/lomiri-polkit-agent/-/archive/0.3.3/lomiri-polkit-agent-0.3.3.tar.gz`
- 源码 sha256：`96167c491cbb17d800e7037c0b038931104423e5d916069f34661231ccdba028`
- 开源许可：**GPL-3.0**（上游 `COPYING`，随包分发；无 fork、无镜像改写，取官方归档）
- 构建系统：**CMake**（C++17）

## 2. 适配范围（打包口径）

- 取**官方源码包**构建，未改写上游源码语义（2 个补丁均为可移植性改动，见 §3）。
- 产物：`bin/lomiri-polkit-agent/policykit-agent`（服务二进制）+ `lib/systemd/user/lomiri-polkit-agent.service`。
- **不导出**头文件/库/可执行目录（`cpp_info` 全空）：该二进制由 D-Bus 激活，
  不是用户直接调用的 CLI，故不导出 `bindirs`。
- 软件级保留 `commands.json`（`package_type = application` 的声明口径，`type=tool`）。
- 依赖：`polkit/124.1`（提供 `polkit-agent-1`）、`glib/2.84.0.1`（`gio-2.0`）、
  `libnotify/0.8.3`、`properties-cpp/0.0.4`。

## 3. 构建要点

```bash
conan create archives/l/lomiri-polkit-agent/0.3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方内三处关键处理（全部注入**本构建**路径，不碰共享系统前缀，R49）：

| 处理 | 原因 |
|---|---|
| 各依赖包 `libdir` 以 `-L` 注入 `CMAKE_(EXE\|SHARED)_LINKER_FLAGS`（glib 目录排首位） | 上游只用 `pkg_check_modules(...)_LIBRARIES`（纯 `-l` 名字、不含 `-L`），依赖 Ubuntu 系统库目录 |
| 生成版 `glib-2.0.pc` 的 `Libs:` 行补回 `-lintl` | glib 的 OHOS 包把 gettext 放在自带 `lib/libintl.so`；`PkgConfigDeps` 按 `cpp_info` 重建 `.pc` 时丢了 `-lintl` → `undefined symbol: g_libintl_gettext` |
| `BUILD_TESTING=OFF` | 上游 `tests/` 依赖 Ubuntu 专有 GMock（硬编码 `/usr/src/gtest`）与 `dbustest-1`（见 §4 申报） |

| 补丁 | 作用 |
|---|---|
| `patches/0001-CMakeLists.txt.patch` | `add_formatcode_target()` / `ENABLE_COVERAGE_REPORT()`（Ubuntu `cmake-extras` 提供）包进 `if(COMMAND ...)`，使非 Ubuntu 主机可 configure |
| `patches/0002-service-main.cpp.patch` | `service/main.cpp` 增加 `--version` / `--help` 分支，使 D-Bus 激活型服务二进制可在无 session bus/polkitd 的环境被冒烟测试 |

**运行期依赖签名（E489）**：OHOS 动态链接器拒绝加载 `.codesign` 失效/缺失的 ELF 共享库。
制品仓 `libnotify/0.8.3`（recipe rev `3d16c3c8`）的 `libnotify.so.4.0.0` 即属此列
（`dlopen` 报 `Permission denied`，运行期表现为 `Error loading shared library libnotify.so.4`
+ `notify_* symbol not found`）。`test_package/generate()` 在测试前把依赖图共享库复制到
测试私有目录并统一重签名（`llvm-objcopy --remove-section .codesign` → `binary-sign-tool
-signAlg SHA256withECDSA`），签名目录置于 `LD_LIBRARY_PATH` 首位；**只写私有副本，
不改动 conan 缓存**。三态对照证据见 `notes.md`。

## 4. 验证结果

| 项 | 结果 |
|---|---|
| 编译（`aarch64-linux-ohos` clang 15.0.4，OHOS SDK 26.0.0.18，CI 同款 profile） | **通过**（`conan create` EXIT=0） |
| 门禁 G0/G1/G2/G3 | **全部 ✅ PASS** |
| 门禁 G4 / L2 / L4 / L5 | G4 ⚠️ 无法取 package id；L2/L4/L5 ⏭️ 跳过（均因无 cache 路径，见 `reports/conan-verify-report.md`） |
| 产物：`bin/lomiri-polkit-agent/policykit-agent` | 存在，4,356,672 B（aarch64 ELF，`e_machine=0xb7`） |
| 产物：`lib/systemd/user/lomiri-polkit-agent.service` | 存在，379 B，非空 |
| 上游测试（`tests/` 注册 **3 项** ctest：`agent-test`/`auth-manager-test`/`authentication-test`） | **0/3 可运行**（GMock 硬编码 `/usr/src/gtest` + pkg-config 模块 `dbustest-1` 缺失，OHOS 与制品仓均无）；以 `-DBUILD_TESTING=OFF` 关闭，源码**未裁剪**，逐项原因见 `notes.md` 申报表（R51） |
| **鸿蒙消费者测试**（`test_package/`，R34 实质消费者用例） | **通过**：结构层（aarch64 ELF 校验 + unit 非空）+ 运行层（`--version` 输出 `lomiri-polkit-agent 0.3.3`、`--help` 含 `Usage:`）共 6 项断言全绿 |
| 依赖闭包运行期加载（E489 重签后） | **通过**：闭包共享库重签名后 smoke test 由失败转为全绿 |
| W4 Pre-PR 审计 | 见 `reports/`（PR 阶段执行，P0/P1 清零） |

## 5. 已知限制

1. **上游 unit 的 `ExecStart` 写死构建期绝对路径**：上游 `CMakeLists.txt` 用
   `configure_file` 展开 `CMAKE_INSTALL_FULL_PKGLIBEXECDIR`，因此制品内的
   `lomiri-polkit-agent.service` 会带上 conan 缓存路径；部署到目标机时需由系统集成方
   重写该行（属上游行为，本适配未打补丁改动）。
2. **端到端认证链路需目标环境具备系统组件**：agent 由会话总线激活，运行需要
   session bus + polkitd + 认证对话框后端；本仓库 `dbus` 包只含客户端库
   `libdbus-1`（无 `dbus-daemon`），polkitd 亦未适配——本包交付的是可安装的服务
   二进制与 unit。
3. **`libnotify/0.8.3` 制品签名缺陷**：本包测试通过私有副本重签名绕过；该依赖包应在
   制品仓侧修复后重发（证据见 `notes.md` 问题 5 与三态对照表）。
4. **上游 `tests/` 不可运行**：3 项 ctest 均依赖 Ubuntu 专有组件（GMock 硬编码路径、
   `dbustest-1`），OHOS 侧无替代；未被本适配裁剪或跳过其源码。
5. 产物未 strip，调试字符串内含构建目录绝对路径。

## 6. 目录说明

```
0.3.3/
├── conanfile.py                # Conan 配方（CI 输入）
├── conandata.yml               # 源码地址 + sha256 + 补丁声明（CI 输入）
├── patches/                    # 2 个补丁（CI 输入）
│   ├── 0001-CMakeLists.txt.patch
│   └── 0002-service-main.cpp.patch
├── test_package/               # Conan L1 消费者测试（CI 输入）
│   ├── conanfile.py                # 结构层 + 运行层验证 + E489 闭包重签名
│   ├── test.sh                     # 实跑 --version / --help 的冒烟脚本
│   └── MANIFEST.yml                # 上游测试清点 + 测试台账（R51）
├── manifest.yaml               # 编译元数据
├── notes.md                    # 适配笔记（问题/证据/上游测试申报表）
└── reports/                    # W3 日志、conan-verify 报告、W4 审计结果
```
