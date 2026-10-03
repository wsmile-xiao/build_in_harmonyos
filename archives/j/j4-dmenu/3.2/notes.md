# j4-dmenu 3.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，目标 `aarch64-unknown-linux-ohos`）
- 标准库: libc++
- 状态: built

## 编译步骤

上游用 CMake，默认通过 FetchContent 从 GitHub 拉取 spdlog / fmt / Catch2。
适配后改为使用制品仓中已发布的包：

```bash
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
                -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 -b missing
```

配方在 `generate()` 中设置的关键变量：

- `NO_DOWNLOAD=ON`（必填）：让上游 `CMakeLists.txt` 对所有 `WITH_GIT_*` 开关执行覆盖，
  并将依赖解析退化为 `find_package()`，从而接上 conan 提供的 spdlog / fmt / Catch2。
- `WITH_TESTS=ON`：编译上游 Catch2 单元测试目标 `j4-dmenu-tests`。
- `OVERRIDE_VERSION=3.2`：避免 tarball 场景下 `git describe` 回退导致版本号异常。
- `CMAKE_MODULE_PATH=<catch2包目录>/lib/cmake/Catch2`：让上游 `include(Catch)` 能找到 `Catch.cmake`。

构建产物是可执行程序 `j4-dmenu-desktop`（`package_type = application`），
另有测试二进制 `j4-dmenu-tests`（不安装）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake configure` 报 `include could not find requested file: Catch`，随后 `catch_discover_tests` 报 `Unknown CMake command` | CMakeDeps 生成的 `Catch2-Target-release.cmake` 用（对库为空的）`catch2_BUILD_DIRS_RELEASE` 覆盖 `CMAKE_MODULE_PATH`，抹掉了 conan 预置路径；Catch2 的 `Catch.cmake` 位于包内 `lib/cmake/Catch2/`，未在模块搜索路径中 | `generate()` 中把 `<catch2包目录>/lib/cmake/Catch2` 显式写入 `CMAKE_MODULE_PATH` |
| 2 | 编译报 `fmt::join` 未声明（`src/main.cc`） | spdlog 制品的 `cpp_info.includedirs` 含 `include/spdlog`，使 `#include <fmt/ranges.h>` 解析到 spdlog 自带的 shim `spdlog/fmt/ranges.h`；该 shim 有 `#pragma once`，反过来把真正的 fmt 头挡掉，真正的 `fmt/ranges.h` 从未被解析 | `generate()` 中把 spdlog 的 `includedirs` 覆盖为仅 `<包目录>/include` |
| 3 | 链接/测试期 `undefined symbol`（spdlog、fmt 相关） | 制品仓默认 `shared=True`；而 `catch_discover_tests` 在**构建期**直接执行测试二进制，此时 conanrun 运行环境尚未生效 | `default_options` 中设 `spdlog/*:shared=False`、`fmt/*:shared=False` |
| 4 | `cmake.test(cli_args=[...])` 报 `Unknown argument --output-on-failure` | `CMake.test()` 的 `cli_args` 是传给**构建工具**的，不是传给 ctest 的 | 改为直接 `self.run('ctest --test-dir ... --output-on-failure -E pytest')` |
| 5 | 上游 pytest 系统测试无法运行 | `tests/system_tests/system_test.py` 需要真实 dmenu/X 会话 | ctest 加 `-E pytest` 排除，仅跑 Catch2 单元测试 |

## 依赖版本

上游在 `CMakeLists.txt` 中钉的是 spdlog 1.14.1 / fmt 10.2.0 / catch2 3.6.0，
制品仓中均未发布，故改用制品仓**已发布**的等价版本：

| 依赖 | 上游钉定 | 本配方实际使用 |
|------|----------|----------------|
| spdlog | 1.14.1 | 1.17.0 |
| fmt | 10.2.0 | 12.2.0 |
| catch2 | 3.6.0 | 3.16.0 |

版本跨度最大的是 fmt（10 → 12），问题 2 即由该版本的 include 路径相互作用暴露，
已通过覆盖 `includedirs` 解决，源码无需改动。

## 源码修改

**无源码补丁（零补丁适配）**。全部适配通过 `conanfile.py` 的 `generate()`
工具链变量 + 依赖 `cpp_info` 覆盖完成，未改动上游任何文件。

## 验证结果

```bash
$ conan create . -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64 -b missing
...
100% tests passed, 0 tests failed out of 79
Total Test time (real) =   1.00 sec

[test] j4-dmenu-desktop --version
3.2
✅ --version reports 3.2
[test] j4-dmenu-desktop --help
✅ --help exit 0
✅ --help documents --dmenu
✅ test_package j4-dmenu/3.2 passed
```

- 上游 CTest：注册 79 个用例，实际执行并通过 **73** 个、0 失败，另有 **6** 个被上游
  `SKIP()` 守卫跳过（#11/#24/#42/#48/#55/#58）。跳过原因是上游把临时目录硬编码为 `/tmp`
  （`tests/FSUtils.cc:157`、`tests/TestI3Exec.cc:106`），本机 `/tmp` 为只读 `erofs` 挂载，
  `mkdtemp` 必然失败——环境限制，非上游缺陷。上游测试源静态计数另有 258 处断言宏。
  故不采用"79/79 全通过"的表述；逐条跳过原因见 `reports/test-report.md`。
- test_package：可执行程序冒烟测试通过（`--version` 报 3.2、`--help` 退出 0 且列出 `--dmenu`）
- 宿主为 HarmonyOS aarch64，OHOS 产物可在本机直接执行，故测试为真实运行结果

## 注意事项

- `NO_DOWNLOAD=ON` 是本适配的前提；若开启下载，构建会从 GitHub 拉取依赖而非使用制品仓版本。
- spdlog 的 `includedirs` 覆盖是必需的，否则 fmt 头会被 spdlog 的 shim 遮蔽（问题 2）。
  该覆盖同时兼顾 spdlog 自身头文件（仍在 `include/` 下）与外部 fmt 的解析。
- Catch2 为 `with_tests` 选项下的测试期依赖，不会链接进发布的 `j4-dmenu-desktop`。
- 发布的可执行程序静态链接 spdlog/fmt，避免运行期动态库依赖。

## 收尾核验（`ohc-run.py finish j4-dmenu 3.2 built`）

交付物就绪检查 **全部通过**：

| 检查项 | 结果 |
|---|---|
| `reports/test-report.md` | ✅ |
| `packaging/*.tar.gz`（release 914 KB + debug 302 KB） | ✅ |
| `.staging-verified`（实测 `--version` rc=0，verified=1 failed=0） | ✅ |
| `.build-closed` / notes「编译结束」 | ✅ |
| 质量验证 G1 / G0 / G2（R29 conan 通道） | ✅ |
| W2 PR 原子性（15 个变更文件，无框架文件） | ✅ |
| manifest `knowledge_ref` 引用（`unreferenced=0`） | ✅ |

状态取 **`built`** 而非 `published`：按 `knowledge/ARCHIVE-SPEC.md:255`，
`published` 要求 `conan verify` 通过**且 conan upload 发布成功**；本配方未执行
`conan upload`，故按规范取 `built`（与 coeurl 0.3.2 等既有 conan 配方一致）。
`finish` 的 argparse 默认值为 `published`，此处显式传参覆盖。

`finish` 退出码为 1，但两处失败均**不属本 PR 范围**，且改动前即存在：

1. **G0 干净构建验证 `configure` exit 127** —— `g0-configure.log` 记录
   `./configure: No such file or directory`。上游是 CMake + Meson 项目
   （仅有 `CMakeLists.txt`/`meson.build`，无 `configure`），
   G0 走的是 autotools 专用流程，对 CMake/conan 配方恒失败；
   真正的构建由 R29 的 conan 通道（G1/G0/G2）验证并通过。
   证据：改动前的 `finish` 运行同样报 `exit 127`。
2. **step5b 知识图谱完整性（字段缺失）** —— 报告 `E219.kv`、`E253.kv`、`E305.kv`
   的 `root_cause`/`rec_approach` 为空。三者分属 yanjiaxin / goblinrs / junshi_liu，
   与本次适配无关，且修复它们会破坏 W2「一个 PR 只允许一个软件」，
   故不在本 PR 处理。本 PR 新增的 `E620`/`E639` 草稿字段齐全。

顺带记录三处工具缺陷（均为基础设施只读文件，未在本 PR 修改）：

- `scripts/ohc/verify_build.py`：`_run()` 已固定 `timeout=15`，第 129 行又传
  `timeout=5` → `subprocess.run` 抛 `TypeError` 被 `except Exception` 吞掉，
  导致 **G2 功能门禁恒判失败**（`--version` 实为成功）。详见
  `reports/quality-report.md` 的"人工复核"节。
- `scripts/ohc/package_builder.py`：`step9_tarball` 以 `cwd=pkgdir` 执行
  `tar -czf <相对路径>`，仅当 `--project-dir` 为绝对路径时可用；
  传相对路径会因目标目录不存在而"打包失败"。
- `scripts/ohc/finish.py`：`gen_summary` 抛 `'str' object has no attribute 'append'`。

---

**编译结束**: 2026-09-25 20:43
**最终状态**: built
