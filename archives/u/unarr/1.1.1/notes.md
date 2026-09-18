# unarr 1.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang（OHOS SDK 26.0.0.18，`--target=aarch64-linux-ohos`）
- 目标平台: OHOS / armv8（Conan profile `ohos-aarch64`）
- 状态: built

## 编译步骤

1. 源码：`https://github.com/selmf/unarr/archive/refs/tags/v1.1.1.tar.gz`（sha256 见 conandata.yml）。
   设备直连 github.com 不通，按经验把官方 tarball 按 sha256 预置到共享 conan 下载缓存
   （`~/tmp/ch/dlcache/s/<sha256>` + sidecar 双 URL），conandata.yml 只写官方 URL。
2. W0：`conan download zlib/1.3.1 bzip2/1.0.8 liblzma/5.8.1 cmocka/2.0.2 -r=ohpcd` 确认依赖配方可解析，
   并在 `conan install --build=never` 下实测二进制可用（R35：不用 `conan list` 判断 binary）。
3. 配方：CMakeDeps + CMakeToolchain；`BUILD_INTEGRATION_TESTS=ON`、`BUILD_UNIT_TESTS=ON`（cmocka 由
   `test_requires` 提供），`cmake.configure()/build()/test()`。
4. 门禁：`ohc-run.py conan-verify unarr 1.1.1` → G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `CMake Error: Compatibility with CMake < 3.5 has been removed` | 平台 CMake 为 4.1.2，上游 `cmake_minimum_required(VERSION 3.3)` 已不被接受 | 配方 `cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`（语料 825 例同法） |
| 2 | 测试程序链接失败：`undefined symbol: inflateInit2_/inflate/inflateEnd` | 上游用 `find_package(ZLIB/BZip2/LibLZMA)` 找 `ZLIB::ZLIB` 等规范目标名，而 Conan CMakeDeps 生成的是 `zlib::zlib`/`bzip2::bzip2`/`liblzma::liblzma`，`if(TARGET ...)` 判空走入空分支 → 未链接任何压缩库 | 在 `generate()` 用 `deps.set_property(<pkg>, "cmake_target_name", "ZLIB::ZLIB"/"BZip2::BZip2"/"LibLZMA::LibLZMA")` 对齐目标名 |
| 3 | 静态库消费方仍缺符号 | 上游对三个压缩库使用 `PRIVATE` 链接（对默认共享构建正确），静态 `libunarr.a` 不传播依赖 | 补丁：三处 `PRIVATE` → `PUBLIC`（静态构建的链接接口必须传播依赖） |
| 5 | 上游两条 bzip2/xz 集成用例被静默跳过（ctest 只有 19 条） | CMake 以 CONFIG 模式找到 Conan 的 `bzip2-config.cmake`/`liblzma-config.cmake` 时设置的是 **混合大小写**变量 `BZip2_FOUND`/`LibLZMA_FOUND`，而上游 `CMakeLists.txt` 与 `test/CMakeLists.txt` 检查的是**全大写** `BZIP2_FOUND`/`LIBLZMA_FOUND` → 判空走入错误分支，bzip2 后端未启用、`lipsum_zip_bzip2.zip`/`lipsum_zip_xz.zip` 两条用例未注册（zlib 恰好大小写一致，所以只有 bzip2/lzma 受影响） | 补丁在 `find_package` 之后把混合大小写结果归一化为上游使用的大写变量（顶层设置，`test/` 子目录继承）；修后 ctest 从 19 条升为 **21 条**并全部通过 |
| 4 | `Problem parsing /proc/meminfo` | CMake 在 OHOS 上解析 /proc/meminfo 失败 | 非阻塞警告，不影响配置与构建 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch` 含两组修改：
  1. `target_link_libraries(unarr PRIVATE <dep>)` → `PUBLIC`（`BZip2::BZip2`、`LibLZMA::LibLZMA`、`ZLIB::ZLIB` 三处）：本配方默认构建静态库（`shared=False`），静态库的依赖必须进入链接接口，否则消费方（含上游 `unarr-test`）无法解析 zlib/bzip2/lzma 符号。
  2. `find_package()` 之后把 CONFIG 模式设置的混合大小写 `BZip2_FOUND`/`LibLZMA_FOUND` 归一化为上游检查的 `BZIP2_FOUND`/`LIBLZMA_FOUND`：否则 bzip2/xz 两个后端被静默跳过，对应两条集成用例不注册（详见问题 5）。

## 依赖版本

- zlib/1.3.1、bzip2/1.0.8、liblzma/5.8.1（均为平台已发布的预编译包；unarr 的 `USE_SYSTEM_*` 默认 ON，命中后链接系统库）
- cmocka/2.0.2（测试期依赖，`test_requires`，用于 crc32 单元测试）

## 上游测试

上游提供真实自动化测试，且由本配方在 `build()` 中通过 `cmake.test()` 执行：

- 集成测试：`test/CMakeLists.txt` 的 `run_test(...)` 注册项，逐个读取 `test/corpus/integration/` 下的
  rar4/tar/zip(store/deflate64/lzma/ppmd)/7z(store/default/max/lzma/ppmd) 样本并校验解压结果。
- 单元测试：`test/crc32-test.c`（cmocka）。
- 注册条目：`test/CMakeLists.txt` 共 **20 条** `run_test` 集成用例（其中 `lipsum_zip_bzip2.zip` 受 `if(BZIP2_FOUND)`、`lipsum_zip_xz.zip` 受 `if(LIBLZMA_FOUND)` 条件保护，7z 五条受 `ENABLE_7Z` 保护）+ 1 条 crc32 单元用例 = 21 条。
- 实测结果：**21/21 通过（100%），0 失败**（ctest 输出 `100% tests passed, 0 tests failed out of 21`）。本配方启用全部后端（zlib/bzip2/liblzma/7z），故 21 条全部注册并执行。

## 验证结果

```bash
# 设备（CONAN_HOME=~/tmp/ch/home-glm41-unarr）
python3 scripts/ohc-run.py conan-verify unarr 1.1.1
# → G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 L4 L5 PASS

# 上游测试（conan create 内 ctest）
100% tests passed, 0 tests failed out of 21

# 消费者测试（test_package/test.c）
ok  : test fixture built
ok  : ar_open_memory() returns a stream
ok  : ar_open_tar_archive() accepts the fixture
ok  : ar_parse_entry() finds the entry
ok  : entry name is hello.txt
ok  : entry size is 12 bytes
ok  : ar_entry_uncompress() succeeds
ok  : decompressed payload matches the input
ok  : archive has no second entry
ok  : ar_open_memory() accepts arbitrary data
ok  : garbage is rejected by ar_open_tar_archive()
unarr consumer test: all checks passed
```

消费者测试：1 个消费者程序（`test_package/test.c`），11 项断言全部通过，覆盖
`ar_open_memory` → `ar_open_tar_archive` → `ar_parse_entry` → `ar_entry_get_name/size` →
`ar_entry_uncompress` 主路径与"非归档数据被拒绝"的负路径。

## 注意事项

- 交付 `libunarr.a` + `include/unarr.h`（纯库，无命令行工具，故无 `commands.json`）。
- 上游 `test/corpus/` 样本随源码 tarball 提供，测试不依赖外部工具或网络。
- 上游 `cmake_minimum_required(VERSION 3.3)`，平台 CMake 4.x 需要 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容。

---

**编译结束**: 2026-09-16
**最终状态**: built
