# clog 1.3.0 适配笔记

## 上游信息

- 仓库：https://github.com/GothenburgBitFactory/clog
- 版本标签：v1.3.0（commit 98b53f0）
- 源码包：https://github.com/GothenburgBitFactory/clog/releases/download/v1.3.0/clog-1.3.0.tar.gz（705807 字节）
- sha256：fed44a8d398790ab0cf426c1b006e7246e20f3fcd56c0ec4132d24b05d5d2018（实测下载计算）
- 构建系统：CMake（C++，含内嵌 src/libshared 子模块内容）
- 产物：clog 可执行文件（src/CMakeLists 仅 install clog_executable 到 bin，另有 man 手册与文档）

## 上游测试审计（结论：无测试）

1. release 包解包 92 个文件，无 test/ 目录（CPack 明确排除 test）。
2. 根 CMakeLists 仅在 test 目录存在时才 add_subdirectory(test EXCLUDE_FROM_ALL)，release 包恒跳过。
3. Git 树 test/CMakeLists 中 set(test_SRCS) 为空，无实际用例；Gentoo ebuild 标注 RESTRICT=test（No test suite on tar.gz）。
4. src/CMakeLists 无 enable_testing/ctest 接线。
5. 因此 test_package/MANIFEST.yml 按 upstream_tests_exist: false + upstream_test_audit 处理，build() 不调用 cmake.test()。

## 配方要点

- package_type = application，package_info 仅声明 bindirs，libdirs/includedirs 置空（工具包）。
- generate() 仅生成默认 CMakeToolchain；CMAKE_POLICY_VERSION_MINIMUM=3.5 经
  build() 的 cmake.configure(variables={...}) 以 -D 命令行传入（toolchain 文件在
  cmake_minimum_required 检查之后才读取，经 toolchain 传该变量无法修复
  CMake>=4 对 <3.5 兼容移除的报错，真机 CMake 4.4.3 实证），不改上游文件。
- CXXSniffer 在 CMAKE_SYSTEM_NAME=HarmonyOS 时落入 UNKNOWN 分支，仅影响 --version 的 built-for 文案，不影响编译，无需补丁。
- package() 复用 cmake.install()（bin + man + doc），另复制 COPYING/LICENSE 到 licenses。
- 无补丁（patches_applied 为空），无依赖。
- 软件级 archives/c/clog/commands.json 声明 type=tool（R38）。

## test_package 设计（R34 合规）

- test_clog.sh 真实执行包内 clog 二进制，共 4 个断言：
  1. clog --version 含 clog 1.3.0；
  2. clog --help 含 Usage；
  3. 自建 clogrc 规则下命中行内容保留；
  4. 非命中行透传不变。
- conanfile.py 用 VirtualRunEnv + CONFIG_SHELL 回退到 /data/service/hnp/bin/bash，与 bash 5.3 工具包同模式。

## 待真机验证

- conan create 全流程（含 test_package 4/4）与产物（bin/clog 可执行）待 HMBS 真机预检回填证据后更新 PR 正文数字。

## 真机失败复盘（2026-09-07 预检 0/4）

- 现象：test_package 4 项全败，`clog --version` 输出 `Could not determine the home directory.`。
  预检同时出现两次 GitHub 下载 ReadTimeout/ConnectTimeout（重试后成功解包），属网络抖动。
- 根因：`src/clog.cpp::main()` 在解析参数前先调 `getpwuid(getuid())`，返回 NULL 即抛错；
  `--version`/`--help`/`-f` 全被该前置检查拦截。真机用户无 passwd 条目时 100% 复现。
- 修复（本轮新策略，区别于仅加镜像）：
  1. 新增 portability 补丁 `patches/0001-home-fallback.patch`：`getpwuid` 失败时回退到
     `$HOME` 拼默认 `~/.clogrc`；`--version`/`--help` 在参数解析处直接返回不再依赖家目录；
     仅当默认 rc 路径仍为空（无 passwd 且无 HOME、又未用 `-f`）才抛原错误。另补
     `#include <cstdlib>`（`getenv` 声明）。
  2. `conandata.yml` 的 `url` 改为有序列表：`gh-proxy.com` 镜像在前、官方 URL 保底回退，
     `sha256` 保持不变（与 `ci/conan/build_and_test.sh` 的 GitHub 镜像映射一致）。
  3. `test_clog.sh` 在 `HOME` 为空时 `export HOME="${TMPDIR:-/tmp}"`（POSIX sh 兼容），
     配合 HMBS 注入的 `TMPDIR` 避开只读 `/tmp`；其余 4 断言与口径不变，未删除任何断言。
- 证据：`clog-1.3.0.tar.gz`（sha256 fed44a8d...5d2018）内 `src/clog.cpp` 第 111 行前置检查；
  预检 stderr `FAIL: --version output missing clog 1.3.0` + `Could not determine the home directory.`。
- 待下轮真机预检验证 4/4。
