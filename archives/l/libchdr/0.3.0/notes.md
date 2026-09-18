# libchdr 0.3.0 适配笔记

> 适配日期: 2026-09-17 | 构建系统: cmake | 状态: built（工作树未提交，待真机预检）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libchdr |
| 版本 | 0.3.0（上游首个正式 tag，`project(chdr VERSION 0.3.0)`，SOVERSION=0） |
| 源码 | https://github.com/rtissera/libchdr/archive/refs/tags/v0.3.0.tar.gz |
| sha256 | 313f6bf5537e2494daa3daa8a931a2536fc4f2b8312c07e3c3d5324d2052fa20 |
| 构建 | CMake + CMakeToolchain/CMakeDeps（cmake_layout），原生 OHOS/aarch64 构建 |
| 产物 | 共享默认 libchdr.so（SONAME libchdr.so.0）；静态需 INSTALL_STATIC_LIBS=ON，得 libchdr-static.a |
| 头文件 | include/libchdr/（bitstream.h、cdrom.h、chd.h、chdconfig.h、coretypes.h、flac.h、huffman.h、macros.h） |

## 二、适配决策
- 零外部依赖：编解码器全部由上游 vendor（deps/lzma-25.01、deps/miniz-3.1.1、deps/zstd-1.5.7，默认 WITH_SYSTEM_*=OFF），`requirements()` 为空，无需 W0 依赖发布等待。
- `shared=True`（默认）映射 `BUILD_SHARED_LIBS=ON`；`shared=False` 映射 `BUILD_SHARED_LIBS=OFF` + `INSTALL_STATIC_LIBS=ON`（静态 target 默认不安装）。
- `BUILD_FUZZER=OFF` 显式关闭（fuzzer 需要 clang + libfuzzer，不属于交付产物）。
- 不调用 `cmake.test()`：v0.3.0 tag 无 ctest 注册，调了反而失败；build() 仍编译默认 target（含 tests/chdr-benchmark），上游证据改由 test_package 真实执行。
- 补丁 0001-open-ownership：回传上游 master 的 open-ownership 归属修复。v0.3.0 的 `chd_open_core_file_callbacks()` 在 parent 非法（cookie 非法）时直接返回而不关闭已传入的 file，`chd_open()` 因此泄漏 FILE（真机 `its descriptor was released` 失败）；memfile 回调路径同样少一次 fclose（真机共 2 处失败）。补丁在 newchd 分配前即按 master 语义关闭 file（OOM 时连带关闭 parent），与 `chd_close()` 的失败即关闭一致；`chd_open()` 经委托自动复用，无需另改。
- 非系统同名库（/lib 下无 libchdr），保留动态库默认，不做 R26 静态强制。
- 纯库，无可执行产物，不需要 commands.json（R38）。

## 三、上游测试执行情况（v0.3.0 tag 无注册，master 有 5 个 ctest）
- 审计对象：v0.3.0 源码包（520105 字节，sha256 见上表）+ master tests/CMakeLists.txt。
- v0.3.0 tag：tests/CMakeLists.txt 仅 `add_executable(chdr-benchmark benchmark.c)` 与可选 fuzz；无 `add_test()`、`enable_testing()`；顶层无 `include(CTest)`。
- master：5 个 `add_test()` — known-answer（kat.c）、legacy-decode（+corpus/legacy）、sparse-map（+corpus/seeds）、open-ownership（open_ownership.c，纯内存）、parent-decode（+corpus/parent）。
- 真机门禁拒绝 no_tests/0（清单命中上游测试），故按 dascrubber/unshield 范式 vendor 可执行的 genuine 用例：
  - `test_package/upstream_open_ownership.c` 为 master `tests/open_ownership.c` 逐字拷贝（BSD-3-Clause），仅用公开 API，与 v0.3.0 头兼容；内存构造 CHDv5 镜像，无 corpus/网络依赖。
  - 未 vendor：known-answer 需 `chd_crc16`（v0.3.0 为 `crc16`，符号已改名）且 KAT 常量与版本强绑定；其余 3 个需 generated 二进制 corpus（v0.3.0 包内无）。
- test_package 直连编译（不走 CMake 工程，避开 Toolchain 路径坑），test() 真实运行 `upstream_open_ownership`，以 `rc==0 + "all checks passed"` 为通过条件，输出 `HMBS_UPSTREAM_TEST_RESULT status:passed framework:ctest discovered:1 executed:1`；失败即抛异常中断构建，无静默跳过。
- 消费者测试（test_package/test_chdr.c）：6 项真实断言——
  1. `chd_error_string(CHDERR_NONE)` 返回非空字符串；
  2. `CHD_V5_HEADER_SIZE == 124` 头常量校验；
  3. `chd_open()` 对不存在文件优雅失败（返回非 NONE 错误，不崩溃）；
  4. `chd_read_header()` 对不存在文件优雅失败；
  5. 错误字符串对多类错误码均非空（INVALID_FILE/INVALID_PARAMETER/FILE_NOT_FOUND）；
  6. fault-injection 场景（`--missing-path`）复验缺失路径被拒绝。
- 防假绿：消费者双场景不同 sentinel + 返回码双条件；上游用例校验 `all checks passed` 且非 0 退出即失败；fixture 为固定缺失文件名，不存在空文件比空文件问题。

## 四、验证结论
- 本轮仅完成未提交工作树；待 HMBS 真机预检（conan create 全链路：构建 + benchmark 编译 + test_package 双场景 + 上游 open-ownership + 双 JSON 标记）。
- 预检通过前不 commit、不 push、不创建 PR。
