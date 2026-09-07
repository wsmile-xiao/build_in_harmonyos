# cern-ndiff 5.09.03 适配笔记

## 编译环境

- 构建系统: cmake（上游 `tools/numdiff/CMakeLists.txt`）
- 编译日期: 2026-09-06
- 编译器: clang/clang++
- 状态: built（待真机预检回填实测证据）

## 软件信息

- **cern-ndiff 5.09.03** — CERN 数值 diff 工具，用于比较含浮点数的无格式文本文件，
  支持绝对/相对容差模板，面向回归测试与数据校验。
- 上游形态：MAD-X 的子项目 `tools/numdiff`，无独立发布包；
  版本号跟随 MAD-X tag（`5.09.03`）。
- 源码：MAD-X 官方 GitHub release tag 包
  `https://github.com/MethodicalAcceleratorDesign/MAD-X/archive/refs/tags/5.09.03.tar.gz`
  SHA-256 `cd57f9451e3541a820814ad9ef72b6e01d09c6f3be56802fa2e95b1742db7797`
  （与 Homebrew cern-ndiff 5.09.03 formula 公布值一致）。
- 产物：单个可执行文件 `bin/ndiff`（`package_type = "application"`，
  无库文件、无头文件）。
- 依赖：无（纯 C99 + UNIX 下上游自链接的 libm）。
- 补丁：一枚 test-only 补丁 `patches/0001-fix-test-register-oracle.patch`（仅修正 CTest 判定条件，二进制与测试数据零改动，见下表第 3 项）。

## 编译步骤

配方复刻 Homebrew cern-ndiff formula 的构建方式：

```bash
cmake -S tools/numdiff -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build
ctest --output-on-failure      # 上游 3 个 CTest 用例（build() 内 cmake.test()）
cmake --install build
```

Conan 侧以 `build_script_folder=<source>/tools/numdiff` 实现 `-S` 指向子目录；
`CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容上古 `cmake_minimum_required(VERSION 2.4)`。

## 上游测试清点（适配前）

来源：`tools/numdiff/CMakeLists.txt` 的 `enable_testing()` 注册项（`ctest -N` 口径）：

| # | 用例名 | 命令 | 通过条件 |
|---|--------|------|----------|
| 1 | test-register | `ndiff tests/test-register/test-register.nd.{lhs,rhs,cfg}` | 输出匹配 `diffs detected over` |
| 2 | test-register-2 | `ndiff tests/test-register-2/test-register-2.nd.{lhs,rhs,cfg}` | 输出匹配 `diffs detected over` |
| 3 | test-register-3 | `ndiff tests/test-register-3/test-register-3.nd.{lhs,rhs,cfg}` | 输出匹配 `diffs detected over` |

合计 3 个 CTest 用例。另有 `Makefile_test` 定义的 `test-constraint` 等 make 侧用例，
CMake 路径不覆盖，以 CTest 的 3 项为统计口径（见 `test_package/MANIFEST.yml`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无独立 ndiff 源码包 | ndiff 只是 MAD-X 的 `tools/numdiff` 子目录 | 下载 MAD-X 整包，`build_script_folder` 只构建子目录 |
| 2 | `cmake_minimum_required(VERSION 2.4)` 在新 CMake 下配置失败 | 上游声明的上古最低版本不被 CMake 4 接受 | `CMAKE_POLICY_VERSION_MINIMUM=3.5`（与 Homebrew 同款） |
| 3 | 上游 CTest 用例 test-register 在真机恒失败（`Required regular expression not found. Regex=[diffs detected over]`），test-register-2/3 通过 | 上游断言过期而非平台问题：`tools/numdiff/CMakeLists.txt` 的一刀切 `PASS_REGULAR_EXPRESSION "diffs detected over"` 来自 2012 年，而 test-register 数据是 2013 年加入的寄存器延迟演示——lhs(n)=2n、rhs(n)=2n-22，延迟 11 行后精确对齐，正确结果恒为 0 diffs。上游自带的 `tests/test-register/test-register.ref`（582 行）尾部即 `81 lines have been diffed` 且全文无 `diffs detected`，与 x86_64 gcc 本地复现、HarmonyOS aarch64 真机日志三方一致 | test-only 补丁仅给 test-register 追加 `PASS_REGULAR_EXPRESSION "do not differ"`（与 .ref 一致），ctest 仍运行真实 ndiff 二进制与真实上游数据；2/3 用例不断言改动 |

## 依赖版本

无编译依赖。

## 验证结果

待真机预检回填：`conan create`（含上游 `ctest` 3 项 + test_package 3 项检查）
的实测输出以 HMBS 真机日志为准，本轮不预填数字。

test_package 设计（`test_package/test_ndiff.sh`，仿 Homebrew formula 的 test 块）：

1. 检查 `bin/ndiff` 存在且可执行；
2. 容差内文件对（`0.0 2e-3 0.003` vs `1e-7 0.002 0.003`，`abs=1e-6`）退出码为 0；
3. 超容差文件对（`1.0` vs `2.0`）输出含上游报告串 `diffs detected`。

任一失败即非零退出。脚本遵循 `colordiff` 先例：`set -u` + FAIL 累加，
不在 HMDFS 上使用 `mktemp`/`trap`，测试文件直接写在 conan test 工作目录。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/ndiff` | 数值 diff 可执行文件 |
| `licenses/LICENSE` | 上游 `tools/numdiff/LICENSE`（GPL-3.0-only） |

## 注意事项

- 本包安装的 `ndiff` 二进制与 nmap 系的 `ndiff` 同名（Homebrew 亦以
  `conflicts_with "ndiff", "nmap"` 标注），属上游命名现状，不改名。
- R40 不适用：纯文本数值比较工具，无图形/多媒体/外设/系统底层相关代码。
