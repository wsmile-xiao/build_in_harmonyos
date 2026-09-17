# libfduserdata 0.1.2 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang/clang++
- 状态: built（待真机预检回填最终证据）

## Source

上游仓库：https://github.com/rd235/libfduserdata（VirtualSquare 团队，LGPL-2.1-or-later）。

版本说明：任务版本 0.1.2 对应上游官方 tag `0.1.2`（commit 719fc58），源码包为官方
`https://github.com/rd235/libfduserdata/archive/refs/tags/0.1.2.tar.gz`（R39 官方源），SHA256 如下：

```
a81c262fbdb3c9ccdc7f1bef637a344febc0c719b132d6537cd8c88ce4b8f583
```

该哈希与 Debian `libfduserdata_0.1.2.orig.tar.gz` 公布值一致，交叉印证为同一上游归档。

源码包内容：`fduserdata.c`、`fduserdata.h`（库本体，仅依赖 C 标准库 + pthread）、
`CMakeLists.txt`、`fduserdata.pc.in`、`Uninstall.cmake`、`man/`（pandoc 文档页）、
`README.md`、`COPYING`。无 `tests/` 目录。

## 上游测试审计（no_tests 依据）

逐项审计上游 0.1.2 发布包与构建文件，确认确实无任何测试：

1. 顶层 `CMakeLists.txt` 全文无 `enable_testing`、`add_test`、`add_subdirectory(tests)`；
   仅定义 `fduserdata` 库目标、`fduserdata.pc`、`man/` 子目录与 `uninstall` 目标。
2. `man/CMakeLists.txt` 仅用 pandoc 生成安装 man 页，无测试目标。
3. 发布包与 GitHub 树均无 `tests/`、`test/`、`unittests/` 目录，无 `*test*.c/cpp/py/sh` 测试源。
4. `README.md` 的编译说明仅为 `mkdir build && cd build && cmake .. && make && sudo make install`，
   未提及任何测试命令；`fduserdata.c` 尾部 `#if 0` 内有一段手工演示 main，但默认不编译、
   未注册为测试。
5. 因此 `build()` 不调用上游测试，直接输出 `status:"no_tests"` 标记；
   `test_package/MANIFEST.yml` 同步声明 `upstream_tests_exist: false` 与本审计摘要。

## Build

配方使用 `CMakeToolchain`，`BUILD_SHARED_LIBS` 跟随 `shared` 选项（默认静态）。
平台校验仅接受 `Linux`/`OHOS`（R32 口径）。

OHOS 适配点（`patches/0001-ohos-portability.patch`，POSIX 兼容方式，未引入任何平台宏，PF5 合规）：

1. 上游 `add_library(fduserdata SHARED ...)` 硬编码共享库；补丁去掉 `SHARED` 关键字，
   使其跟随 `BUILD_SHARED_LIBS`。
2. 上游 `target_link_libraries(fduserdata pthread)`；HarmonyOS libc 内含 pthread API，
   无独立 libpthread，补丁在 `CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"` 时跳过该链接
   （Linux 保持不变；同已合入 libcanard 3.3.0 模式）。
3. 上游 `install(TARGETS fduserdata LIBRARY ...)` 只安装动态产物，静态构建将安装空包；
   补丁补齐 `ARCHIVE`/`RUNTIME` 目标，保持 `LIBRARY` 不变。
4. 上游无条件 `add_subdirectory(man)`；`man/` 需要 pandoc + make，真机无此工具，
   补丁在 HarmonyOS 上跳过该子目录，其他平台保持不变。

`build()` 中真实执行 `cmake.configure()` + `cmake.build()` 后，输出
`HMBS_UPSTREAM_TEST_RESULT`（`status:"no_tests"`、`discovered:0`、`executed:0` 及具体 reason），
并落盘 `res/upstream_test_result.json` 供 test_package 重发（防缓存命中丢失证据）。

## Tests

test_package 消费者测试（`test.c`，TAP 14 检查，全部实质调用库 API）：

- 表创建/销毁：`fduserdata_create(0)` 默认哈希表、`fduserdata_destroy` 空表销毁。
- 新增/查询/归还：`fduserdata_new` 建 `struct mydata` 并 `fduserdata_put` 关闭临界区；
  `fduserdata_get` 读回并校验字段后 `fduserdata_put`。
- 哈希碰撞：fd 10 与 fd 74（`& 63` 同槽）顺序 get/check/put 验证共存且互不覆盖
  （禁止同时持有两个 get 锁：表内为单非递归互斥锁，连续 get 不 put 会死锁被看门狗 SIGKILL）。
- 删除：`fduserdata_get` 后 `fduserdata_del`，再查返回 NULL。
- 回调销毁：`fduserdata_destroy_cb` 遍历回调计数后释放整表。
- 异常路径：`fduserdata_get` 未登记 fd 返回 NULL。

`test()` 中 `self.run` 真实执行二进制，再以 subprocess 解析 `ok` 行计数，
输出 `HMBS_TEST_PACKAGE_RESULT` 标记；用例失败时二进制非零退出且 `ok` 行缺失，
门禁可捕获（非静默通过）。同时重发包内 `res/upstream_test_result.json`，
并校验其为合法 `no_tests` 证据（`discovered==0` 且 `executed==0` 且 reason 非空）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | man/ 在真机可能缺 pandoc | 上游无条件构建文档页 | 补丁在 HarmonyOS 上跳过 man/ 子目录 |
| 2 | HarmonyOS 链接 -lpthread 失败风险 | libc 已含 pthread，无独立 libpthread | 补丁按 CMAKE_SYSTEM_NAME 跳过 pthread 链接 |
| 3 | 默认静态构建安装空包 | 上游只安装 LIBRARY 产物 | 补丁补齐 ARCHIVE/RUNTIME 安装目标 |
| 5 | 策略周期 2：前三轮（TMPDIR 透传、COMPILER_WORKS 跳过、CLI/缓存钉死编译器）连续同错复现，RUN 行已显示 harmonybrew 钉死两次但报错仍指向 /data/service/hnp/bin/clang，证实 conan_toolchain.cmake 文件内容优先于 CLI/缓存顺序（先生效者胜）且旧 CMakeCache 残留旧路径 | CLI/cache 覆盖机制在该工具链下无效；根因转为“文件内容权威”，须改文件本身而非传参 | generate()/build()（含 test_package）不再依赖 CLI -D，改为生成后直接改写所有 `conan_toolchain.cmake`（C++ 先换、再换 C，追加 FORCE 版编译器与 WORKS/ABI 跳过），并删除残留旧编译器路径的 `CMakeCache.txt`；C++ 取 clang 同级 clang++ 或独立探测；TMPDIR 透传保留（环境仍只读），测试口径不变 |
| 4 | 真机 cmake C 编译器自检失败（`CMAKE_C_COMPILER: /data/service/hnp/bin/clang is not able to compile a simple test program`），伴随 `can't create temporary file /tmp/....tmp: Read-only file system` + HMBS `[readonly_tmp]` | 初判为 TMPDIR 未透传到 `conanbuild.sh`（首轮修复）；复检同错仍现（报错行号 106→144 证明首轮代码已同步），证实 try_compile 探针在 OHOS 沙箱内根本跑不起来（次轮追加 `COMPILER_WORKS/ABI_COMPILED` 跳过，行号 144→151 后同错第三次复现，证明跳过亦未生效或失败点另有所指，但摘要截断看不到真实错误） | 首轮：`_writable_tmpdir()` + `generate()` 经 `buildenv_info` + `VirtualBuildEnv` 下发 TMPDIR；次轮：`COMPILER_WORKS=1` + `ABI_COMPILED=1`；本轮（第三种策略）：不再假设 profile 编译器路径可用——`_discover_c_compiler()` 按 profile-conf→env→PATH→SDK 顺序收集候选并以真实 `clang --version` 子进程探测（不用 `os.access(X_OK)`，HMDFS 下误报，见 R49），`build()` 以 CLI `-DCMAKE_C_COMPILER` 钉死探测到的二进制（CLI -D 优先于工具链 CACHE，顺序确定），失败时 `_dump_configure_diagnostics()` 把工具链编译器行与 `CMakeError.log` 尾部打进日志以暴露被截断的真实错误；仅钉编译器/补证据，不跳过测试 |

## 依赖版本

本次编译无外部依赖（仅系统 libc）。

## 验证结果

待真机预检回填：`conan create` 需真实运行库构建 + test_package 14 检查，
并输出 `HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT(no_tests)` 两行合法 JSON 标记。

## OHOS notes

- 非系统同名库（OHOS `/lib` 无 libfduserdata），保留动态库构建能力（默认静态），R26 不适用。
- 纯库项目，无可执行产物，不创建 `commands.json`（R38）。
- 未引入 `#ifdef __OHOS__` 平台宏；全部适配在 CMake 层按系统名条件完成。
