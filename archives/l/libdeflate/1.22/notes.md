# libdeflate 1.22 适配笔记

> 适配日期: 2026-09-02 | 构建系统: cmake | 状态: built

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libdeflate |
| 版本 | 1.22 |
| 源码 | https://github.com/ebiggers/libdeflate/releases/download/v1.22/libdeflate-1.22.tar.gz |
| sha256 | 7834d9adbc9a809e0fb0d7b486060a9ae5f7819eb7f55bb8c22b10d7b3bed8da |
| 构建 | CMake + ohos.toolchain（自发现，glfw 式裸 cmake） |
| 产物 | libdeflate.so（SONAME libdeflate.so.0），共享库 + 关闭静态 |

## 二、适配决策
- 延续 1.25 配方骨架：`LIBDEFLATE_BUILD_SHARED_LIB=ON` / `STATIC=OFF` / `GZIP=OFF`，`CMAKE_INSTALL_LIBDIR=lib`。
- 新增 `-DLIBDEFLATE_BUILD_TESTS=ON`：上游测试程序（test_checksums 等 8 个 CTest 用例）随包编译，`ctest` 在 build() 内执行。
- CI 构建 #36527 首次失败：旧配方将 `CMAKE_AR/RANLIB` 硬编码为 SDK 工具；CI 的 `lld` 缺少 `libxml2.so.16` 运行库且 SDK 不提供独立 `llvm-ranlib`。修复为从 Conan 配置/环境解析 GNU `ar/ranlib`（无 GNU 工具时回退 LLVM），并从 clang 推导 SDK `llvm/lib` 注入 `LD_LIBRARY_PATH`，三个 CMake 步骤均显式加载 `conanbuild`。本地复验 `conan create` 完整通过。
- `test_requires zlib/1.3.1`：上游测试程序对比测试需要 ZLIB（CMake `find_package(ZLIB REQUIRED)`），仅测试期依赖，运行时不依赖；已用 `conan download zlib/1.3.1 -r=ohpcd --only-recipe` 验证已发布（R35/R36）。
- 消费者 test() 用 `self.run("ctest ...")` 显式执行，满足 L0d stub 检测（R34）。

## 三、上游测试执行情况
- 上游官方测试入口 `scripts/run_tests.sh` 共 11 个测试组（regular/O3/march_native/valgrind/ubsan/asan/cfi/install/symbol_prefix/use_shared_lib/freestanding）。
- **全量执行结果：`All tests passed!`（脚本 exit 0），11/11 组全部通过。**
- 8 个 CTest 单元用例在每组构建配置下重复执行通过；gzip/gunzip 程序测试全量通过；install/symbol_prefix/use_shared_lib/freestanding 专项检查通过。
- HMDFS 平台限制（与库行为无关，见补丁 0001 的最窄豁免，运行时显式打印说明）：
  - `mkfifo(2)` → EPERM，FIFO 断言无法执行；
  - `link(2)`（硬链接）→ EPERM，硬链接断言无法执行；
  - `chmod` 权限位不生效，Permission denied 断言无法执行。
- 补丁 0001（gzip_tests.sh）：shebang `/bin/bash`→`/usr/bin/env bash`、ELOOP 错误文案兼容（"Symbolic link loop"）、toybox stat 探测、上述三处 EPERM 最窄豁免。
- 补丁 0002（run_tests.sh）：OHOS 无 `ldd`，`is_dynamically_linked` 与 freestanding 检查增加 `readelf -d` NEEDED 回退（精确匹配 libdeflate）。
- 均不改动库源码。
- test_package/MANIFEST.yml 声明全部 11 个上游测试组及平台限制说明，未少报。

## 四、验证结论
- 上游 11 组套件全量通过（设备本地 clang + OHOS 工具链，BASH_ENV 注入 bash 内建 id/mkfifo，stat 用系统 /usr/bin/stat）。
- conan-verify：G0/G1/G2/G3 全部 PASS，L2/L4/L5 通过，可标记 published。
- W3 本地 CI：test_package test() 用 self.run("ctest ...") 显式执行（R34），JC 单软件原子提交后增量通过。
---

**编译结束**: 2026-09-02 02:28
**最终状态**: published
