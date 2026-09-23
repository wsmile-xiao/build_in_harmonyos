# crunch-dxtc 0.56.2 适配笔记

## 编译环境
- 构建系统: cmake（上游自带 CMakeLists.txt + test/test.py 测试 harness）
- 编译日期: 2026-09-10
- 编译器: clang/clang++ 15（HarmonyOS PC aarch64 真机）
- 状态: built（待真机预检回填证据后由 HMBS 提交）

## 上游确认
- 上游仓库：https://github.com/DaemonEngine/crunch（Dæmon 团队维护的 CRN 分支，含 Unity 改进与 CMake 构建）
- 版本标签：`unvanquished/0.56.2`；Debian/Ubuntu `crunch-dxtc 0.56.2-1` 源码包即跟踪该分支的 `unvanquished/*` 标签
- 源码包：`https://github.com/DaemonEngine/crunch/archive/refs/tags/unvanquished/0.56.2.tar.gz`
- sha256：`1863f38c82c172ed2902e6b8201d7df86b298bcc9c415589bbf9b1e306b4851c`（实测下载计算）
- 许可证：Zlib（license.txt）
- 零外部依赖：stb_image/miniz/lzma 均已 vendor，无需先发布依赖（R36 通过）

## 上游测试清点（适配前）
- 测试 harness：`test/test.py`（约 18KB），被上游 Azure CI 全平台调用（Linux amd64/i686/arm64/armhf、Windows MinGW、macOS）
- 用例构成：约 91 次进程调用（`crunch --help` + 7 组全格式互转 png/tga/bmp/crn/dds/ktx/jpg-to-all 共 49 次 + tga/png/bmp/jpg 转 png/crn 共 32 次 + bmp/jpg 转 crn 共 3 次 + example1/2/3 共 6 次）
- 校验构成：`test/checksums.tsv` 89 条 blake2b 记录（files 校验）+ 重复转换一致性比对（clones 校验，约 45 条）
-  verdict 行总数约 134 行；配方解析 `Yes/No` verdict 行生成 `HMBS_UPSTREAM_TEST_RESULT`
- 构建命令（与上游 CI 对齐）：`cmake -S. -Bbuild -DBUILD_CRUNCH=ON -DBUILD_EXAMPLES=ON -DBUILD_SHARED_LIBS=OFF -DUSE_FAST_MATH=OFF`，测试命令：`CRUNCH_BUILD_DIR=<build> python3 test/test.py`

## 编译步骤（配方逻辑）
1. `get()` 解包上游 tarball（strip_root）
2. `CMakeToolchain` 注入：`BUILD_SHARED_LIBS=OFF`（默认静态）、`BUILD_CRUNCH=ON`、`BUILD_EXAMPLES=ON`（供测试 harness 用，不 install）、`USE_FAST_MATH=OFF`（可复现）、`BUILD_STATIC_LIBCRN=ON` + `INSTALL_STATIC_LIBCRN=ON`（否则静态库不 install）
3. `cmake.configure()` + `cmake.build()`
4. `_run_upstream_tests()`：`CRUNCH_BUILD_DIR=<build_folder> python3 test/test.py`（cwd=源码目录），subprocess 捕获输出，解析 verdict 行并做证伪检查（产物目录非空、退出码为 0），输出 `HMBS_UPSTREAM_TEST_RESULT` 标记；失败即抛异常中断构建
5. `package()`：`cmake.install()`（lib + crunch + man 页）+ 手动 copy `inc/crnlib.h、crn_decomp.h、crn_defs.h、dds_defs.h` 到 include/ + license.txt 到 licenses/
6. `package_info()`：`libs=["crn"]`、`bindirs=["bin"]`，Linux/OHOS 加 `system_libs=["pthread"]`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游版本号 0.56.2 无 GitHub release，只有 git tag | Debian 打包跟踪分支 tag 而非 release | conandata.yml 直接引用 `archive/refs/tags/unvanquished/0.56.2.tar.gz`（官方源，R39 合规），sha256 实测 |
| 2 | 上游 `cmake --install` 不装头文件 | 上游 CMakeLists 无 headers install 规则 | 配方 `package()` 手动 copy 4 个公开头文件 |
| 3 | 静态库默认不 install | 上游 install 规则只覆盖 shared 或显式 STATIC_LIBCRN | 非 shared 时注入 `BUILD_STATIC_LIBCRN=ON` + `INSTALL_STATIC_LIBCRN=ON` |
| 5 | 真机 cmake.configure 报 CXX compiler identification unknown（/data/service/hnp/bin/clang++），先后叠加 TMPDIR 重定向、CMAKE_SYSTEM_NAME=Linux、LD_LIBRARY_PATH 探针三轮仍同错 | Conan CMakeToolchain 把 os=OHOS 映射为 vanilla cmake 不认的 HarmonyOS（ML-0035），强改 Linux 又与 OHOS SDK clang 目标错配；LD 探针复用同一缺失路径故 ENOENT | 本轮换路线：删 CMakeToolchain/Linux 覆盖/探针，改自发现 ohos.toolchain.cmake + 裸 cmake，构建前签名 crunch/example 二进制，CRUNCH_BUILD_DIR 指向 build-ohos 真实二进制目录 |
| 4 | 测试断言数字不能猜 | 真机未跑前无实测数 | 配方动态解析 verdict 行计数；PR 正文数字留待真机 evidence 轮回填 |

## test_package 设计（R34）
- `test_crn.cpp`：8 项真实 libcrn API 检查（无条件跳过，任一失败即非零退出）+ 生成 `test_input.tga`
- `conanfile.py test()`：运行 `./test_crn`（8）→ `crunch --help`（9）→ `crunch -file test_input.tga -out test_output.crn` 真实转换并断言产物非空（10），输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=10）
- 编译器取自 `tools.build:compiler_executables`（R33），链接包内 `libcrn` 并校验 includedirs/libdirs 真实存在（防 L1e 反向验证误判）

## 验证结果
- 本轮：工作树已完成，未提交；待 HMBS 真机预检（conan create 全量：构建 + 上游 test.py + test_package）
- 上游测试用例通过率：待真机 evidence 轮回填
- 新增测试用例通过率：待真机 evidence 轮回填

## 交付物（预期）
| 文件 | 说明 |
|------|------|
| libcrn.a | 静态库（默认）；shared=True 时为 libcrn.so |
| crunch | DXTc 纹理压缩/转码命令行工具 |
| crnlib.h / crn_decomp.h / crn_defs.h / dds_defs.h | 公开头文件 |
| crunch.1 | man 页 |

## 注意事项
- `crnlib.h` 要求 `-fno-strict-aliasing`（上游 CMake 已默认注入，勿删）
- 如真机出现校验和 mismatch（平台浮点差异），优先检查是否误开了 fast-math，而非放宽校验
- 本包同时是库和工具：软件级 `commands.json`（type tool）已配套

## 2026-09-10 preflight exit6 follow-up
- ohos.toolchain.cmake hard-require fails when SDK file absent in preflight sandbox; switch to hybrid: SDK present -> bare cmake, absent -> conan_toolchain Linux fallback with existence-checked compiler.

## 2026-09-10 upstream_test follow-up（真机 png-to-all/unvanquished_64.crn 失败）
- 现象：`python3 test/test.py` 在第 4 个转换（png->crn，`crunch -helperThreads 3 -file test/unvanquished_64.png -out .../png-to-all/unvanquished_64.crn`）崩溃；日志刷屏 `crn_mem.cpp(130): Assertion failed: "crnlib_free: bad ptr"` + `crnlib_realloc: bad ptr`，终结于 `crn_vector.cpp(42): Failure: "buf"`，harness 报 `Command failed`，`HMBS_UPSTREAM_TEST_RESULT` 为 failed（executed=0）。
- 根因：`inc/crnlib.h` 定义 `CRNLIB_MIN_ALLOC_ALIGNMENT = sizeof(size_t)*2`（64 位上 16），`crnlib_free/realloc/msize` 在运行时硬校验该对齐（`crnlib_mem_error` 常开，Release 也不关闭）；而 `crnlib_default_realloc` 的 malloc/realloc 路径直接调 `::malloc/::realloc`，其仅保证 `alignof(max_align_t)`（部分 musl/OHOS 目标上为 8）。Release 下 `CRNLIB_ASSERT` 被 NDEBUG 静默，malloc 侧 8 字节对齐无声通过，free/realloc 侧 `bad ptr` 集中爆发并导致 vector 扩容返回 NULL（"buf"），属分配器可移植性缺陷而非测试可跳过项。FreeBSD 已有同类修复先例（DaemonEngine/crunch PR #36，`aligned_alloc`）。
- 修复：新增 `patches/0001-crn_mem-aligned-alloc.patch`（conandata.yml 已登记，`apply_conandata_patches` 在 build() 自动应用）：malloc 路径按对齐向上取整后 `posix_memalign(16)`（失败回退 `malloc`）；realloc 路径改为对齐 malloc + `memcpy(min(old_usable, size))` + `free`，保持 16 字节不变量；FreeBSD 原 `aligned_alloc(size)` 同步修正取整。不删断言、不跳过测试、不改测试口径。
- 待验证：HMBS 下一轮真机预检（conan create 全量）确认 `test/test.py` verdict 行与 checksums.tsv 校验是否通过；数字以预检日志实测为准回填 PR 正文。

## 2026-09-11 test_package follow-up（真机 crnlib.h NULL/size_t 未声明）
- 现象：库本体构建通过，test_package 编译 `test_crn.cpp` 失败：`inc/crnlib.h:212/231/232/535/540 use of undeclared identifier 'NULL'` + `:510/511 unknown type name 'size_t'`（clang++ -std=c++11，10 errors）。
- 根因：上游 `inc/crnlib.h` 全文件零 `#include`，直接使用 `NULL`/`size_t`；旧 libstdc++ 靠传递包含偶然可用，严格 clang/libc++ 独立 `#include <crnlib.h>` 即失败。库内 .cpp 因先含其他头才偶然编过，消费者必现。
- 修复：新增 `patches/0002-crnlib-h-missing-includes.patch`（conandata.yml 已登记，build() 经 `apply_conandata_patches` 应用后随 `package()` copy 进 include/）：在 `#define CRNLIB_H` 后加 `#include <stddef.h>`，不改任何 API；test_crn.cpp 保持 `#include <crnlib.h>` 首位不变以验证头文件自包含。
- 待验证：HMBS 下一轮真机预检确认 test_package 编译链接通过。
