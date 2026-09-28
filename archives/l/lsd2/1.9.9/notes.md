# lsd2 1.9.9 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt；另有 src/makefile 等价构建）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，profile: ci/conan/profiles/ohos-aarch64）
- 状态: published

## 编译步骤

1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
   - 配方: archives/l/lsd2/1.9.9/conanfile.py（CMake，USE_LSD2=OFF → 独立可执行 lsd2）
   - 源码: 官方 tag v1.9.9 tarball，sha256=decda612ad7f26c67d50f3dc46fb14bfc2ac90776e460b14c548fd6f9d281454
   - 上游 CMakeLists.txt 无 install() 规则，package() 直接拷贝 build 产物 lsd2 → package/bin
   - `CMAKE_BUILD_PARALLEL_LEVEL=1`（R9：单线程，本机 FS 拒绝 make jobserver mkfifo）
2. 原生复验（探索阶段）: cmake .. && make -j1 → 生成 lsd2 可执行文件，2 个无害
   `-Wtautological-constant-out-of-range-compare` 警告（上游源码固有，`c!=-1` 对 char 恒真）
3. conan-verify 全门禁通过: G1/G2/G3/G4 + L2/L4/L5

## 上游测试枚举台账（双口径，task 要求）

上游 **无独立测试套件**：无 tests/ 目录、无 make check / ctest 注册、无 GTest/Catch2/Boost.Test
宏或注册项（grep 全源码确认）。官方交付物 = CLI 程序 + examples/ 示例数据集。

### 源码声明口径（source_declared_total）

| 类别 | 条目 | 独立上游用例? | 说明 |
|------|------|--------------|------|
| 用户测试源 | 无 | — | 上游无任何独立测试源文件 |
| 框架头/源码 | 无 | — | 未捆绑任何测试框架 |
| 测试脚本 | 无 | — | 无 run_tests/test.sh 等 |
| 基准/夹具 | 无 | — | 无 benchmark/fixture 目录 |
| 构建目标 | lsd2（add_executable，USE_LSD2 默认 OFF） | 否 | 单一 CLI 目标；USE_LSD2=ON 时为库目标，均非测试 |
| 上游示例数据 | rooted_tree/h1n1_phyml.tree + h1n1.date | 否（示例非测试） | 真实数据集，作消费者验证输入 |
| 上游示例数据 | rooted_tree/h1n1_flexible.date | 否 | 灵活日期约束变体 |
| 上游示例数据 | unrooted_tree_with_outgroups/h1n1_* | 否 | 含 outgroup 的无根树示例 |
| 上游示例数据 | unrooted_tree_without_outgroups/Dengue.* | 否 | Dengue 无根树示例 |

**source_declared_total = 0**（无独立上游用例；示例数据集 4 组按要求列入台账但不计入用例数）。

### 当前配置可执行口径（configured_executable_total / executed_passed_total）

**configured_executable_total = 0**（上游无测试注册，OHOS 配置无任何可实例化的独立测试用例）。

### 示例数据集实际运行（验证 CLI 功能，不计入通过率分母）

| 数据集 | 命令（cwd=/storage/Users/currentUser/tmp/lsd2-smoke/...） | 退出码 | 结果 |
|--------|----------------------------------------------------------|--------|------|
| rooted h1n1 | `lsd2 -i tree.txt -d dates.txt -o out.txt -s 1700` | 0 | rate 0.00268625, tMRCA 2008.98 |
| rooted h1n1 flexible | `lsd2 -i tree.txt -d flex.date -o flex.out -s 1700` | 0 | rate 0.00267451, tMRCA 2008.98 |
| unrooted h1n1 + outgroup | `lsd2 -i og.tree -d og.date -o og2.out -s 1700 -g og.txt -G` | 0 | rate 0.00268625, tMRCA 2008.98 |
| unrooted Dengue | `lsd2 -i t.txt -d d.txt -o out3.txt -s 11000 -r a` | 0 | rate 0.000870144, tMRCA 1922.38 |

> 首次尝试 `-r`（无操作数）与无 `-G` 的 outgroup 运行按上游用法报错并退出码 1，
> 按 README/options.cpp 确认正确用法（-r l|a|as|k；-G 移除 outgroup）后复跑全部成功。

**全量通过率 = 0/0（无上游用例）；示例数据集运行 4/4。**

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 把 GitHub 仓库 URL 当页面抓取返回 HTML | URL 未指向 tarball | 用官方 tarball URL `https://github.com/tothuhien/lsd2/archive/refs/tags/v1.9.9.tar.gz` |
| 2 | conan-init 按 autotools 模板生成配方 | init 阶段从 URL 猜测构建系统 | 重写 conanfile.py 为 CMake 模板（上游实为 CMakeLists.txt） |
| 3 | `cmake.build(jobs=1)` TypeError | Conan 2.29 CMake.build() 不支持 jobs 关键字 | 移除 jobs=1，改用 `CMAKE_BUILD_PARALLEL_LEVEL=1`（R9 单线程语义） |
| 4 | make jobserver mkfifo: Operation not permitted | 本机 FS 限制 | 单线程构建（-j1 / PARALLEL_LEVEL=1） |
| 5 | 示例 `-r` 报 "requires an operand"、outgroup 报 "provide dates or -G" | 上游用法要求 | 按 options.cpp 用法复跑成功（见台账） |

## 源码修改

无补丁（patches/ 为空）。上游源码未改动；仅配方层适配（conanfile.py/CMake 变量）。

## 依赖版本

无第三方依赖（纯 C++11 标准库实现，无 requires）。

## 验证结果

- conan create / conan-verify: G1/G2/G3/G4 + L2/L4/L5 全部 PASS
- test_package 消费者测试: `lsd2 -h` 版本横幅 + h1n1 示例 dating 运行（rate/tMRCA）PASS
- 产物: package/bin/lsd2（aarch64 ELF，--version/-h 可用）

## 交付物

| 文件 | 说明 |
|------|------|
| archives/l/lsd2/1.9.9/conanfile.py | CMake 配方（application） |
| archives/l/lsd2/1.9.9/conandata.yml | 官方源 + sha256 |
| archives/l/lsd2/1.9.9/test_package/ | 消费者测试（test.sh + h1n1 数据） |
| archives/l/lsd2/commands.json | CLI 声明（R38，tool，binary=true） |

## 注意事项

- lsd2 是 CLI 工具（非库），package_type=application，无需 cpp_info.libs。
- 上游无测试套件属真实情况（已 grep 全源码确认无测试框架注册），台账如实记录 0/0。
---

**编译结束**: 2026-09-27 22:30
**最终状态**: published
