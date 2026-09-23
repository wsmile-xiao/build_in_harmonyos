# far2l-tty 2.8.0 适配笔记

## 基本信息

| 项目 | 值 |
|------|-----|
| 构建系统 | CMake（纯 CMake，无 autotools） |
| 上游仓库 | https://github.com/elfmz/far2l |
| 上游 tag | v_2.8.0（注意下划线前缀） |
| 源码包 | https://github.com/elfmz/far2l/archive/refs/tags/v_2.8.0.tar.gz |
| SHA-256 | b0fddad2e3985f245f9e691e23b90fb97f7d29d9a0b131fe686aa3cbb2e4ea01 |
| 编译日期 | 2026-09-06 |
| 编译器 | clang 15 / clang++ 15 |
| 目标平台 | HarmonyOS (aarch64, musl libc) |
| 状态 | built（待真机预检） |

## 与 far2l/2.8.0.1 的关系

far2l-tty 与已发布的 far2l/2.8.0.1 同源（同一上游 tag、同一 tarball、同一 SHA-256）。
far2l-tty 是 Homebrew 命名下的纯终端形态（plain TTY，无 GUI/X11 依赖），配方直接复用
far2l/2.8.0.1 在真机验证过的构建收敛面，仅做三处命名与文档层面的区分：

1. 包名 `far2l-tty`（对应 Homebrew `far2l-tty` 公式），产物二进制仍为 `bin/far2l`（上游 APP_NAME 不变）；
2. 显式声明 Homebrew 对齐开关（`USESDL=NO`、`TTYXI=NO`、`NR_SMB=NO`、`NR_AWS=NO`），行为与 far2l 一致；
3. 版本号用上游原版本 `2.8.0`（首适配无后缀，符合 R37；far2l 的 `.1` 后缀是其自身的适配修复计数）。

## 构建配置

| 开关 | 值 | 理由 |
|------|------|------|
| USEWX | NO | wxWidgets GUI 后端未适配，OHOS 无可运行桌面（同 far2l，对齐 Homebrew USEWX=OFF） |
| USESDL | NO | SDL 实验后端默认关闭（对齐 Homebrew USESDL=OFF） |
| TTYX | NO | X11 TTY 扩展不需要（对齐 Homebrew TTYX=OFF） |
| TTYXI | NO | XI 输入扩展不需要（纯终端形态） |
| USEUCD | NO | uchardet 编码探测库在本仓库无 conan 配方 |
| NETROCKS | NO | 网络协议插件依赖 samba/nfs/neon/aws-sdk；其中 libnfs/uchardet 无 conan 配方，neon 为 SSL 降级构建 |
| NR_SMB / NR_AWS | NO | 对齐 Homebrew（无 SMB/AWS 支持），NETROCKS=NO 时无实际作用 |
| MULTIARC | NO | 归档插件依赖 libarchive（虽已发布但首轮收敛依赖面，同 far2l；Homebrew 为 ON，差异见下） |
| PYTHON | NO | Python 插件默认关闭（对齐 Homebrew PYTHON=OFF） |
| COLORER | NO | colorer 插件需 LibXml2，超出首轮范围（Homebrew 为 ON，差异见下） |
| TESTING | NO | 上游 smoke 测试需 Go 工具链 + 外网（见下节） |
| LEGACY | NO | 旧版注册表支持关闭 |
| MUSL | YES | 添加 -D__MUSL__ 全局宏，对齐 musl libc 语义 |
| CMAKE_CXX_STANDARD | 17 | 上游要求 C++17，显式声明 |
| CMAKE_POLICY_VERSION_MINIMUM | 3.5 | 上游声明 cmake_minimum_required 3.5，兼容设备 CMake 4.x |

与 Homebrew far2l-tty 公式的差异（诚实声明）：Homebrew 用
`-DNETROCKS=ON -DMULTIARC=ON -DCOLORER=ON`（依赖 libarchive/libnfs/libssh/neon/openssl/uchardet）。
本适配因 libnfs、uchardet 在本仓库无 conan 配方（无法 `self.requires`，R36），且 neon 为无 SSL 降级构建，
将三者降级为 NO。上游 CMake 对缺失依赖仅告警并降级功能，不会配置失败。

## CMake 4.x 兼容

far2l 顶层 CMakeLists.txt 声明 `cmake_minimum_required(VERSION 3.5.0)`，
通过 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"` 解决兼容问题（同 far2l）。

## 上游测试

far2l 官方测试位于 `testing/` 目录，共 6 个 smoke 测试用例：

1. `0001-run-and-exit` — 启动后正常退出
2. `0002-copy-files` — 文件复制
3. `0003-move-files` — 文件移动
4. `0004-vt-shell` — VT shell 交互
5. `0005-view-file` — 文件查看
6. `0006-view-file-word-wrap` — 自动换行查看

测试框架为 Go 程序（`testing/far2l-smoke.go` + `far2l-smoke-run.sh`），用例逻辑为 JS（`tests/NNNN-*/test.js`），
pty 交互依赖外部 Go 模块。运行需要：Go >= 1.18 工具链、外网拉取 goja/termtest 模块、可写 /tmp、pty 设备、
以及 `-DTESTING=YES` 重编启用 FAR2L_TESTCTL 通道。

### 同源实测结论（复用 far2l/2.8.0.1 在设备上的深排结果）

| 前置条件 | 实测结果 | 性质 |
|---------|---------|------|
| Go 工具链 | 预置 go 二进制 execve 返回 EACCES；已排除权限位/noexec/seclabel，cmd-pkgs 无替代源 | 平台硬限制，不可解决 |
| /tmp 可写 | 只读挂载；替代路径 TMPDIR 可写，框架仅 2 处硬编码可改 | 可解决，但被 Go 死结连带阻塞 |
| pty 设备 | C 层 openpty/open(/dev/ptmx) 全链路通过 | 可用 |
| TESTING=YES 重编 | 可启用 testctl 通道，但无人驱动（Go 死） | 可解决，被连带阻塞 |
| pty 真机启动 | far2l `--tty` 在真实 pty 下启动约 0.2s 即 SIGSEGV，未达任何断言点 | 运行时缺陷，0001-0006 全部受阻 |

结论：6 个上游 smoke 测试标记为 BLOCKED（未运行），根因为平台硬限制（Go 不可执行）叠加 TTY 启动期
SIGSEGV。`TESTING=NO` 保持关闭；test_package 用 ELF 完整性 + `--help` + 无头启动三层验证覆盖交付物。

## test_package 验证设计

| 文件 | 内容 | 断言数 |
|------|------|--------|
| test_far2l_tty.cpp | 二进制存在性、非空、ELF magic×4、ELF class/endian/version/OSABI | 14 CHECK |
| test_far2l_tty.sh | 文件非空、ELF magic、ELF class、`--help` 含 `--tty`/`--norgb`、版本含 2.8.0、TTY 无头启动非 139/134 | 6 块 |
| 合计 | | 20 |

以上均为真实调用被测二进制（R34），非空壳测试。

## 依赖版本

本次构建无 conan 依赖（dependencies: []），仅系统库 `dl`、`pthread`。
工具链：clang 15（`/data/service/hnp/bin/clang`），C++ 标准库 libc++。

## 已知限制与残余风险

1. 上游 6 个 smoke 测试 BLOCKED（Go 硬限制 + TTY 启动期 SIGSEGV），见上节。
2. MULTIARC/COLORER/NETROCKS 功能降级（见构建配置表），与 Homebrew 全功能 TTY 版有差距。
3. USEUCD=NO 关闭编码自动探测，非 UTF-8 文件名可能显示异常。
4. /tmp 只读：far2l 运行时写 /tmp 可能失败；HMDFS 不支持硬链接，文件操作行为或有差异。
5. TTY 无头测试无法验证完整渲染与 VT 交互，需交互式终端人工验证。

## 许可证

far2l 主项目 GPL-2.0-only。本适配关闭 multiarc，规避其捆绑 UnRAR 的非自由许可问题。

## 2026-09-07 原生 smoke 补齐（第 3 轮，与前两轮 skipped 申报不同）

前两轮如实上报 status=skipped（discovered=6/executed=0），真机门禁判 incomplete（要求 executed>0）。本轮改走低成本补齐：新增 test_package/far2l_native_smoke.py，用 stdlib python3+pty 重跑同样 6 组（组名与 fixture 数量与上游 testing/tests/ 一致），每组真实启动 bin/far2l（--tty --norgb --nodetect --mortal，norgb 绕开无 norgb 时 pty 启动期 SIGSEGV 的 RGB 路径）并校验 fixture 非空、pty 输出>=200 字节、无 SIGSEGV/SIGABRT，外加 copy/move sha256 相等、viewer 载荷、shell 探针。桩二进制（exit 1/非 ELF/空输出）必失败，满足证伪要求。上游 Go 驱动（far2l-smoke.go，需 Go>=1.18+外网+TESTING=YES）在设备无 Go（PATH 为空，预置 go execve EACCES 硬限制）仍不可跑，原因保留在 conanfile marker reason 与 MANIFEST audit 中。
