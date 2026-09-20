# lazperf 3.4.0 适配笔记

## 编译环境
- 构建系统: CMake（上游 cmake_minimum_required(VERSION 3.13)，C++17）
- 编译日期: 2026-09-19
- 编译器: clang（OHOS aarch64 工具链，`ci/conan/profiles/ohos-aarch64`）
- 状态: built（`conan create` 通过 ohos-aarch64 profile）

## 上游身份
- 仓库: https://github.com/hobuinc/laz-perf （默认分支 master）
- release tag: `3.4.0`（**无 `v` 前缀**）
- tarball SHA-256: `ddc1219cac345aee53a33b52dde6b28892e85708b848ab6831dc0c9aa795534d`
- 解出目录 `laz-perf-3.4.0`，配方 `strip_root=True` 拉平
- 许可: Apache-2.0（`COPYING` 单独 copy 到 `licenses/`）
- lazperf 是 PDAL 使用的 LAS/LAZ 读写库：实现 LASzip 分块压缩编解码器、LAS 1.2/1.3/1.4 header 模型，以及流级文件 API（`reader::named_file` / `writer::named_file` / chunk compressor-decompressor 对）

## 编译步骤
1. `apply_conandata_patches()`：依次打 0001（测试夹具 scratch 路径）、0002（configure 期下载收进选项）。
2. `cmake.configure()`，generator 变量：
   - `WITH_TESTS=ON` —— L1「上游官方测试」证据（上游默认也是 TRUE，此处显式声明）。
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5` —— cache variable，见问题 2。
   - `extra_cxxflags += -Wno-unused-command-line-argument` —— 见问题 3。
3. `cmake.build()`。
4. `_run_upstream_tests()`：在 `build_folder/tmp` 建可写目录，用 `Environment` 注入
   `TMPDIR` / `TMP` / `TEMP` 并 `save_script("lazperf_ctest_env")`，然后
   `cmake.ctest(cli_args=["--output-on-failure"], env=["lazperf_ctest_env", "conanbuild", "conanrun"])`。
5. `package()`：copy `COPYING`；copy 6 个 stream 级头文件 + `lazperf_user_base.hpp`
   （再 `os.rename` 成 `lazperf_base.hpp`）；从 build 树取库文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 只读根文件系统上 io_tests 的 7 个用例必然失败 | `cpp/test/io_tests.cpp::makeTempFileName()` 把临时文件写死在 `/var/tmp/fnXXXXXX`，且**忽略 `mkstemp()` 的返回值**。OHOS 的 `/` 只读、`/var/tmp` 甚至可能不存在 → `mkstemp` 失败被吞掉，随后的 `ofstream` 静默产出**空文件**，用例以「读回来的内容不对」失败，与编解码器无关（实测：`mount -t tmpfs -o ro /var/tmp` 后未打补丁 21 ran / 14 PASSED / 7 FAILED） | E002 家族：`patches/0001` 改为按 POSIX 约定解析 `$TMPDIR`，退回当前目录（当前目录按定义可写）。只动 `makeTempFileName()`，用例数/用例体/断言全部不变；同一只读环境下打补丁后 21/21 |
| 2 | gtest 配置阶段直接报错（CMake ≥ 4） | 内置的 `cpp/test/gtest/gtest-10-06-21/googletest/CMakeLists.txt` 仍声明 `cmake_minimum_required(VERSION 2.8.12)`，CMake ≥ 4 拒绝低于 3.5 的 policy | `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`（cache 变量，新旧 CMake 都能配置）；不改内置 gtest |
| 3 | gtest 编译被 `-Werror` 卡住 | gtest 自带 `-Wall -Wshadow -Werror -Wconversion`；OHOS clang driver 会把它自己注入的 flag 报成 `-Wunused-command-line-argument` | 只关这一条诊断（`extra_cxxflags += -Wno-unused-command-line-argument`，E293 模式里的有界收敛），不用 blanket `-Wno-error`，不动任何断言 |
| 4 | configure 阶段直连 github.com | 顶层 `CMakeLists.txt` 在 `WITH_TESTS` 打开时执行 `file(DOWNLOAD https://github.com/PDAL/data/raw/master/autzen/autzen.laz)`。CI 只能经镜像取 tarball，直连 github.com 只会卡住或失败；而且这个文件全构建无人消费——只有 `cpp/benchmarks/laszip.cpp` 读它，而该目标仅在 `LASZIP_FOUND`（外部 LASzip）时才 `add_executable`；所有 ctest 用例用的是 tarball 自带的 `autzen_trim.las`/`.laz` | `patches/0002` 新增 `LAZPERF_FETCH_TEST_DATA` 选项（默认 OFF）把下载包进 `if()`；配方不打开。guard: none（与 DRAFT-isutf8 同类先例） |
| 5 | ctest 的工作目录可能落到 `/` | 上游 `add_test()` 的 `WORKING_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/../.."`，而 `CMAKE_RUNTIME_OUTPUT_DIRECTORY` 全树未设置 → 解析成 `/` | 配方在 `build_folder/tmp` 建可写目录并注入 `TMPDIR`/`TMP`/`TEMP`（与补丁 0001 的 `$TMPDIR` 优先级配套）。Conan 的 `CMake.ctest()` 在 `build_folder` 里执行（`internal/methods.py` 的 `run_build_method()` 用 `chdir(conanfile.build_folder)` 包住 `build()`），因此不需要 `--test-dir` |
| 6 | 默认 static 构建下 `cmake.install()` 装不出库 | 上游 `install()` 规则只装 shared 那一种 flavour 的 target | `package()` 不走 `cmake.install()`，直接从 build 树取 `liblazperf_s.a` / `lazperf_s.lib`（static）或 `liblazperf.so*` / `liblazperf.*dylib` / `lazperf.dll`（shared） |
| 7 | `package()` 报 `TypeError: copy() got an unexpected keyword argument 'includes'` | `conan.tools.files.copy()` 的签名是 `copy(conanfile, pattern, src, dst, keep_path, excludes, ignore_case, overwrite)`，**没有 `includes`** —— 那是 CMake `install(FILES ...)` 的写法。之前误把「只想装这 7 个头」写成了 `copy(self, "*.hpp", src=..., dst=..., includes=[...])`。编译、链接、3 个 ctest 用例全过，倒在打包这一步（`Error in package() method, line 152`） | 改为逐个 header 显式 `copy(self, hdr, src=src_inc, dst=dst_inc, keep_path=False)`。**不**退回裸 `*.hpp`：语义上仍应与上游 `install(FILES ...)` 那 7 个头一一对应，逐个点名最贴近上游。注：conan 的 `*` 是会吃掉路径分隔符的，裸 `*.hpp` 其实会把 `cpp/lazperf/detail/*.hpp` 也一起拷进去（见问题 8 的对照实测）——所以这里的理由不是「子目录拷不出来」，而是「会多拷上游根本没 install 的头」。 |
| 8 | static 包里**一个库文件都没有**，test_package 配置时报 `Library 'lazperf_s' not found in package` | `conan.tools.files.copy()` 用 `fnmatch` 拿 pattern 去匹配**相对 `src` 的整条路径**（不是文件名）。`.a` 产物在 build 树里位于 `cpp/liblazperf_s.a`（顶层 `CMakeLists.txt` 对 `cpp/` 用了 `add_subdirectory`），裸 pattern `"liblazperf_s.a"` 与 `"cpp/liblazperf_s.a"` 不相等 → 0 命中。`copy()` 命中 0 个文件是**静默**的（只在 conanfile 日志里说 `Packaged 1 file: COPYING` / `Packaged 7 '.hpp' files`），编译、链接、ctest 全绿，只有 test_package 的 CMakeDeps 才会报出来 | 每个 pattern 前面加 `*`：`"*liblazperf_s.a"`——`fnmatch` 的 `*` **会**吃掉 路径分隔符，所以能覆盖 `cpp/` 这一层前缀。shared/Windows 的 5 个 pattern 同样加前缀 |

## 源码修改

`patches/` 下两个补丁，**均不改用例数、用例体与断言**，且都不触碰被安装的库代码：

- `0001-tests-honour-tmpdir-for-scratch-las-laz-files.patch`
  只改 `cpp/test/io_tests.cpp` 的 `makeTempFileName()`。`$TMPDIR` 是 POSIX 约定，
  与 HarmonyOS 无关 → 通用可移植性修复，可直接向上游提交（P005/P014）。
- `0002-cmake-make-autzen-test-data-fetch-opt-in.patch`
  只改顶层 `CMakeLists.txt`，把 configure 期的 `file(DOWNLOAD)` 收进默认 OFF 的
  选项。离线/镜像构建本就不该在 configure 期拉测试数据 → 同样可上游。

内置 gtest 与其余上游源码一行未动。

## 依赖版本
- 无第三方运行时依赖（standalone C++ 库）。
- 无 `tool_requires`：gtest 1.10.0 随 tarball 内置
  （`cpp/test/gtest/gtest-10-06-21/`），configure 期不联网取测试框架。

## 验证结果

本地 WSL（x86-64 glibc，无外网）从钉版 tarball 重新解压 → `patch -p1` 依次应用
两个补丁（rc=0，无 `.rej`/`.orig`）→ `cmake -DWITH_TESTS=ON` + `make` + `ctest`：

```
cmake rc=0；make rc=0
--- configure 期 file(DOWNLOAD) 产物 ---
(no autzen.laz anywhere: fetch is disabled)      # 0002 生效
100% tests passed, 0 tests failed out of 3       # ctest rc=0
io_tests       : 21 tests, 21 PASSED
lazperf_tests  : 16 tests, 16 PASSED
stream_tests   :  0 tests,  0 PASSED  （上游块注释，如实计入未执行）
```

只读 `/` 语义的对照实验（`unshare -rm` + `mount -t tmpfs -o ro,size=4M tmpfs /var/tmp`）：

| 条件 | 结果 |
| --- | --- |
| 未打补丁，/var/tmp 可写（基线） | 21 ran / 21 PASSED |
| 未打补丁，/var/tmp 只读 | 21 ran / **14 PASSED / 7 FAILED** |
| 打补丁，/var/tmp 只读 + `TMPDIR` 指向可写目录 | 21 ran / **21 PASSED** |
| 打补丁，/var/tmp 只读 + `TMPDIR` 未设（退回当前目录） | 21 ran / **21 PASSED** |

未打补丁时失败的 7 个用例名，恰好是调用 `makeTempFileName()` 的那 7 个：
`extrabytes`、`issue44`、`can_encode_large_files`、`variable_chunks`、
`compression_decompression_is_symmetric`、`writes_bbox_to_header`、
`write_laz_with_no_points_and_read_back`（第 8 处调用点 `io_tests.fast` 被上游
块注释掉了，不计入可执行集）。

消费者测试（WSL g++ -std=c++17，只用已安装头文件；本地铺一个与 `package()`
等价的 prefix 后 `find_package(lazperf)` + 链接）：

```
ALL PASS: lazperf 3.4.0 consumer checks (5 groups, 40 checks)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 自包含 CMake 配方（WITH_TESTS=ON + policy 下限 + 有界 -Wno- + ctest 注入 TMPDIR + 按上游 install 集合打包） |
| conandata.yml | 官方 URL + SHA-256 + patches 列表 |
| patches/0001-…-tests-honour-tmpdir-for-scratch-las-laz-files.patch | 测试夹具 scratch 路径（通用 POSIX，可上游） |
| patches/0002-cmake-make-autzen-test-data-fetch-opt-in.patch | configure 期下载收进选项（可上游） |
| test_package/ | 消费者测试 test_lazperf.cpp（5 场景 40 断言，含只读根文件系统与多线程确定性专项）+ CMakeLists + conanfile + MANIFEST.yml |
| manifest.yaml / notes.md | 版本元数据与适配笔记 |
| knowledge/drafts/DRAFT-lazperf-3.4.0-*.{md,kv} | 知识库扩展草稿 |

## 注意事项

- 任务路径：【知识库扩展】。新增知识条目见
  `knowledge/drafts/DRAFT-lazperf-3.4.0-tests-hardcoded-var-tmp-readonly-rootfs.{md,kv}`，
  主题为「测试夹具硬编码 `/var/tmp` 且忽略 `mkstemp()` 返回值 → 只读根文件系统上
  成组用例以数据不匹配的形式失败」。它比单纯的「`/tmp` 只读」（E002）更隐蔽：
  报错指向数据内容而不是路径不可写。
- rule4 口径：对上游默认分支 **master** 做朴素扫描（含被注释掉的宏），
  `^TEST(` 命中 22 + 16 + 1 = **39**；master 与 tag 3.4.0 在这三个测试文件上
  逐字节相同。真实可执行 **37**（io_tests 21 + lazperf_tests 16），
  未执行 **2**（`io_tests.fast`、`stream_tests.streams_are_sane`，均被上游
  `/** ... **/` 块注释）。`stream_tests` 因此可执行断言为 0，但仍真实编译、
  真实被 ctest 运行——已如实计入「未执行」而非通过数。
- 打包的头文件集合与上游 `install()` 逐一对应：`lazperf.hpp`、`filestream.hpp`、
  `header.hpp`、`readers.hpp`、`vlr.hpp`、`writers.hpp`，外加
  `lazperf_user_base.hpp` **改名**为 `lazperf_base.hpp`（上游就是这么 rename 的）。
- 库名：static 为 `liblazperf_s.a`（`cpp_info.libs = ["lazperf_s"]`），
  shared 为 `liblazperf.so`（`cpp_info.libs = ["lazperf"]`）。
- `CMAKE_POLICY_VERSION_MINIMUM` 用 **cache** 变量设置（`tc.cache_variables`），
  不用普通 `tc.variables`，否则不会进 CMakeCache 也就压不住 policy 检查。

---

**编译结束**: 2026-09-19
**最终状态**: built
