# lwmem 2.2.4 适配笔记

## 编译环境
- 构建系统: cmake（库目标位于 `lwmem/` 子目录，由 `library.cmake` 注册 `lwmem`/`lwmem_cpp` 目标）
- 编译日期: 2026-09-28
- 编译器: clang/clang++（Conan Toolchain，`ci/conan/profiles/ohos-aarch64`）
- 状态: published

## 编译步骤

1. `python3 scripts/ohc-run.py init-build lwmem 2.2.4 --url=https://github.com/MaJerle/lwmem/archive/refs/tags/v2.2.4.tar.gz` — 下载并解压官方 v2.2.4 tarball（SHA-256 `9d34c6f9...`），建立归档骨架。
2. `python3 scripts/ohc-run.py conan-init lwmem 2.2.4` — 生成配方骨架；随后按 CMake 库改写 `conanfile.py`（`CMakeToolchain` + `cmake.configure(build_script_folder="lwmem")` 构建库子目录，手动打包头文件与静态库）。
3. `python3 scripts/ohc-run.py conan-verify lwmem 2.2.4` — G0-G4 + L2/L4/L5 全过，`conan create` 干净构建通过。
4. `python3 scripts/ohc-run.py finish lwmem 2.2.4 built` — 10/10 步完成，W3 本地 CI 模拟通过（exit 0）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试套件硬编码 win32 系统端口，编译报 `fatal error: 'windows.h' file not found` | `tests/CMakeLists.txt` 硬编码 `LWMEM_SYS_PORT "win32"`，且每个测试子目录 `lwmem_opts.h` 无条件 `#include "windows.h"`、`LWMEM_CFG_OS=1`、互斥量句柄为 `HANDLE` | 仅改 7 个测试配置头（patch 0001-0007）：`LWMEM_CFG_OS` 1→0、`HANDLE`→`void*`、`windows.h`→`stddef.h`；库核心（OS=0 时互斥量宏为空实现）零改动 |
| 2 | `CMake.configure()` 报 `unexpected keyword argument 'source_folder'` | lwmem 根 CMakeLists 顶层只构建测试，库目标在 `lwmem/` 子目录；conan 2 的 CMake 辅助器不接收 `source_folder` 关键字 | 改用 `cmake.configure(build_script_folder="lwmem")` 指向库子目录 |
| 3 | 消费者测试首版为恒绿快乐路径 | `test.c` 只断言非 NULL 与内容保持，无任何可失败负向断言 | 增加 4 条真实可失败负向断言（OOM、非法 realloc_s 输入、NULL get_size、空 region 列表），并完成注入负向证明 |
| 4 | 鸿蒙特有测试使用 `#if defined(__OHOS__)` 平台条件编译 | R8 规则：新增源码与补丁不得引入平台条件编译宏 | 重写 `platform_check()`：删除死代码，改用运行时字节序探针与 `(uintptr_t)ptr % 4` 对齐断言，消除全部平台宏分支 |

## 源码修改

补丁（7 个，`patches/0001..0007-tests-test_*_lwmem_opts.h.patch`）：移除上游 win32 系统端口依赖，将测试配置改为可移植的 OS=0 配置（`#include "windows.h"` → `#include <stddef.h>`，`LWMEM_CFG_OS` 1→0，`LWMEM_CFG_OS_MUTEX_HANDLE` `HANDLE`→`void*`）。库源码零修改。

## 依赖版本

- 无外部 Conan 依赖（lwmem 为纯 C/C++ 单库）
- 工具链：clang 15.0.4 / cmake 4.1.2 / conan 2.29.1（OHOS 适配版）

## 验证结果

```bash
# 上游测试 7/7（7 个配置各 1 个 ctest 用例）
cmake -S . -B build -DTEST_CMAKE_FILE_NAME=tests/<name>/cmake.cmake && cmake --build build && ctest --output-on-failure
# 结果：7/7 100% passed

# 鸿蒙特有测试（独立入口 + test_package 目标）
# ohos_special_test.cpp 独立运行：PASS（alloc/free/realloc/alignment/endianness）
# conan create（test_package cmake.test()）：2/2 Passed（test_lwmem + test_lwmem_ohos）

# conan 验证
python3 scripts/ohc-run.py conan-verify lwmem 2.2.4   # G1-G4 + L2/L4/L5 全过，published
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | CMake 构建配方（库子目录构建 + 头文件/静态库打包） |
| `conandata.yml` | 官方 URL 首位的源码声明（含 SHA-256） |
| `test_package/` | 消费者测试 `test_lwmem`（含 4 条可失败负向断言）+ 鸿蒙特有测试 `test_lwmem_ohos` + `lwmem_opts.h` + MANIFEST.yml |
| `patches/0001-0007` | 上游测试配置头 win32 端口移除补丁 |
| `knowledge/drafts/DRAFT-lwmem-2.2.4-test-win32-sys-port.kv` 与同 stem `.md` | 路径 B 知识草稿对 |

## 注意事项

- 测试运行需从 tests 子构建目录执行 ctest（顶层 CTestTestfile 无测试注册）。
- 关闭 OS 支持后测试在单线程下运行；如需覆盖线程安全路径须另行提供 pthread 系统端口。
- PR 文件清单严格限于 `archives/l/lwmem/2.2.4/**` 与知识草稿对。
---

**编译结束**: 2026-09-28
**最终状态**: published
