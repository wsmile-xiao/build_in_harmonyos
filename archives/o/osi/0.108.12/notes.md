# osi 0.108.12 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-09-11
- 编译器: clang/clang++ 15（HarmonyOS PC aarch64，原生构建）
- 状态: built（待真机预检回填实测证据后更新）
- 上游仓库: https://github.com/coin-or/Osi
- 上游版本: releases/0.108.12（2026-03-11 发布）
- 源码: https://github.com/coin-or/Osi/archive/refs/tags/releases/0.108.12.tar.gz
- sha256: 1d80d0b4275f2e1ceefc6dda66b8616e3a8c8b07a926ef4456db4a0d55249333
- 测试输入: 官方 Data-Sample 1.2.13（https://github.com/coin-or-tools/Data-Sample，sha256 cb4c3713b2a2510d0b6387c24a68c88ba5eff27e2c392429653b1bdef50f06c9）

## 编译步骤

1. 同步上游 main，创建分支 `feat/osi-0.108.12`。
2. 参考同族已验证配方 `archives/c/coin-osi/0.108.12`（同上游同版本）与 `archives/c/coinutils/2.11.13` 的 HarmonyOS 经验：in-source 构建、config.guess 识别 HarmonyOS/HongMeng 为 Linux musl、umask 002 规避 HMDFS 临时目录问题、OHOS 可执行文件需 llvm-objcopy + binary-sign-tool 自签名后运行。
3. `conanfile.py` 关键 configure 参数：
   `--without-blas --without-lapack --without-cplex --without-gurobi --without-mosek --without-xpress --without-soplex --without-glpk`，依赖 `coinutils/2.11.13`。
4. OHOS 路径：`CONFIG_SHELL=/system/bin/sh sh ./configure` 在 `build_folder/ohos-work` 内执行，`make -j1`，然后 `make -C Osi/test unitTest` 并签名，再 `make -C Osi/test test unittestflags=-mpsDir=<Data-Sample>`。
5. `package()` 用 `make install DESTDIR=<package_folder>`，清理 `*.la`、`pkgconfig`、`share`。
6. 消费者测试 `test_package/osi_smoke.cpp` 真实调用 `CoinPackedMatrix::setDimensions/getNumCols` 与 `OsiRowCut::setLb/setUb/lb/ub`，共 2 个断言检查，运行后打印 `HMBS_TEST_PACKAGE_RESULT` 标记；`conanfile.py build()` 上游测试后打印 `HMBS_UPSTREAM_TEST_RESULT` 标记。

## 上游测试清点

- 来源目录：`Osi/test/`（`unitTest.cpp` + `Makefile.am` 定义的 `test` 目标）。
- 默认可运行：1 个 `unitTest` 可执行文件，内部覆盖 OsiRowCut、OsiColCut、OsiCuts、OsiTestSolverInterface（使用 OsiTestSolver + Data-Sample MPS 输入）。
- 明确未运行：CPLEX/GLPK/Gurobi/Mosek/SoPlex/XPRESS 后端测试（`COIN_HAS_*` 守卫，本配方显式 `--without-*` 关闭，原因见 `test_package/MANIFEST.yml`）；Netlib 全量集（需 `COIN_HAS_NETLIB` + 外部 Netlib 数据包，且默认 Vol 派生测试求解器显式跳过 Netlib）。
- 证伪要求：真机预检需确认 `unitTest` 输出以 `All tests completed successfully` 结尾且参照 MPS 非空；`make test` 退出码 0 不等于已运行，需在日志中见到测试执行痕迹。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS/HongMeng | 上游 config.guess 仅匹配 Linux/GNU | 补丁 0002/0003 将 HarmonyOS/HongMeng 映射为 Linux musl，复用 coin-osi 已验证补丁 |
| 2 | 安装时调用 `pkg-config --libs osi` 在交叉/OHOS 环境失败 | `Osi/Makefile.in` 的 install-data-hook 强依赖宿主 pkg-config | 补丁 0001 注释掉该两行，复用 coin-osi 已验证补丁 |
| 3 | HMDFS 下 `umask 077 && mktemp -d` 与 `mkdir $tmp` 临时目录失败 | 鸿蒙分布式文件系统对 077 掩码/硬链接/临时文件有限制 | OHOS 构建前将两处 umask 改为 002，使用独立 ohos-work 目录，与 coin-osi 一致 |
| 4 | OHOS 可执行文件默认无签名无法运行 | OHOS 要求 codesign | 构建后用 llvm-objcopy 去除旧签名段，再用 binary-sign-tool 自签名（unitTest 与 osi_smoke 均签名） |
| 5 | 上游默认测试数据路径 `../../Data/Sample` 缺失 | 未 vendor 测试数据 | 在 `source()` 额外下载官方 Data-Sample 1.2.13 到 `_test_data/Sample`，并以 `-mpsDir` 显式传入 |
| 6 | 真机预检 `coin-utils/2.11.13` 在 conancenter/ohpcd 均无法解析 | conancenter 最高仅 2.11.12；`coin-utils`（带连字符）在 ohpcd 未发布，而同族 `coinor-osi/0.108.11`、`coinor-dylp/1.10.4`、`coin-or/0.108.12`、`clp/1.17.11` 均依赖已发布的 `coinutils/2.11.13` | 依赖改用仓库内已发布、可解析的 `coinutils/2.11.13`（`transitive_headers=True` 保留，`package_info` 改为 `coinutils::coinutils`，与 `coin-or`/`clp` 写法一致）；`.pc` 名同为 `coinutils`，configure 侧无影响 |

## 源码修改

- `patches/0001-no-pkg-config-check.patch`：禁用安装时 pkg-config 调用。
- `patches/0002-osi-config-guess.patch`：Osi/config.guess 支持 HarmonyOS/HongMeng（含 aarch64 HongMeng 识别）。
- `patches/0003-root-config-guess.patch`：根 config.guess 支持 HarmonyOS/HongMeng。
- 以上三补丁均复用 `archives/c/coin-osi/0.108.12` 已验证内容，未引入 `__OHOS__` 平台宏。

## 依赖版本

- `coinutils/2.11.13`（transitive_headers=True）
- 测试输入 `Data-Sample/1.2.13`
- 工具链：HarmonyOS PC clang 15，conan 2.x，cmake（仅 test_package 消费者构建）

## 验证结果

- 本地仅做静态检查（`python -m py_compile`、补丁文件存在性、`git diff --check`），未在本机运行 conan（按任务守则，编译验证在真机内执行）。
- 待 HMBS 真机预检回填：`conan create` 构建日志、上游 `unitTest` 输出、`osi_smoke` 输出及两行 HMBS JSON 标记。预检通过前保持未提交，不创建 PR。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/o/osi/0.108.12/conanfile.py | 主配方（autotools，OHOS 签名+上游测试+HMBS 标记） |
| archives/o/osi/0.108.12/conandata.yml | 源码 URL+sha256、Data-Sample、3 个补丁声明 |
| archives/o/osi/0.108.12/test_package/ | osi_smoke 真实 API 调用测试 + MANIFEST.yml |
| archives/o/osi/0.108.12/manifest.yaml | 版本级元数据 |
| archives/o/osi/manifest.yaml | 软件级元数据 |

## 注意事项

- 本包名为 `osi`（目录 `archives/o/osi`），同上游同版本另有历史包 `coin-osi/0.108.12`（目录 `archives/c/coin-osi`），两者源码同源、依赖闭包一致，本次为新包名首适配，conan ref 为 `osi/0.108.12`，CMake 包名为 `osi::libosi`。
- Windows 工作区存在上游 `archives/l/libXext` 与 `archives/l/libxext` 仅大小写不同的两个目录，本机始终显示脏树，与本任务无关，未修改。
- PR 正文测试数字必须以真机预检日志为准，本轮不猜测；补充说明需如实列出未运行的后端用例及原因。
