# chunkio 1.5.2 适配笔记

## 编译环境
- 构建系统: CMake（设备 cmake 4.1.2，上游 `cmake_minimum_required(VERSION 3.0)`）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++（`/data/service/hnp/bin/clang`，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（conan verify 通过、未 upload ⇒ 按 O5 只写 `built`）

## 编译步骤

配方在 `conan create` 内完成全链（无手工 configure 步骤）：

1. `source()`：按 conandata.yml 下载 `v1.5.2.tar.gz`（sha256 `c73e8092…987a5`，三路取证一致），
   `strip_root=True` 解压，随后 `apply_conandata_patches()` 按序应用 5 个补丁
   （`patch_ng`，`strip=0`，这是这些 diff 的书写形式）。
2. `generate()`：`CMakeToolchain` 注入
   `-DCIO_LIB_STATIC=ON -DCIO_LIB_SHARED=OFF -DCIO_BACKEND_FILESYSTEM=ON -DCIO_TESTS=ON`
   以及 CMake 4 兼容所需的
   `CMAKE_POLICY_VERSION_MINIMUM=3.5`、`CMAKE_POLICY_DEFAULT_CMP0042=NEW`、
   `CMAKE_POLICY_DEFAULT_CMP0077=NEW`；`BUILD_SHARED_LIBS` 由 conan 的
   `SharedLibBock` 按 `options.shared` 自动发布。
3. `build()`：`cmake.configure()` → `cmake.build()` → 运行上游 acutest 全套
   （`ctest --output-on-failure -V`，再直接执行上游未注册的 2 个性能程序），
   输出 `HMBS_UPSTREAM_TEST_RESULT` 标记；任何一例失败即 `ConanException`。
4. `package()`：拷贝 `LICENSE` 到 `licenses/`，`cmake.install()` 落
   `include/chunkio/*.h`（含生成的 `cio_info.h` / `cio_version.h`）、
   `include/monkey/mk_core/*.h`（`chunkio.h` 依赖的 `mk_list.h`）、
   `lib/libchunkio-static.a` 与 `lib/libcio-crc32.a`。
5. `test_package`：`find_package(chunkio)` + `chunkio::chunkio` 编译消费者程序
   并以 `self.run(..., env="conanrun")` 直跑（17 个 CHECK）。

**外部编译依赖 0 个**：`deps/crc32`（静态辅助库）与 `deps/monkey/include`
都在源码归档里自带，随本包一起构建/安装；`find_package(Sanitizers)` 只在
`CIO_SANITIZE_ADDRESS=ON` 时才会触发，本配方不启用。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游**没有任何 `install()` 规则**，`cmake.install()` 装出空包 | 上游 CMakeLists 只有 `add_library`/`add_executable`，全树 0 处 `install(` | 补丁 `0001-add-installer.patch`（与 conan-center-index 的 `1.5.2-0001-add-installer.patch` 逐字一致），并同时注释掉 `add_subdirectory(tools)` —— `cio` CLI 不再构建，产物为纯库（无 `bin/`，按 R38/L0k **不需要** `commands.json`） |
| 2 | `CMake Error: Compatibility with CMake < 3.5 has been removed` | 设备/CI 的 CMake 4.1.2 移除了 <3.5 兼容，上游钉 `cmake_minimum_required(VERSION 3.0)` | `CMAKE_POLICY_VERSION_MINIMUM=3.5`（cache 变量，同 CCI 做法），另加 CMP0042/CMP0077 保险 |
| 3 | `src/cio_utils.c:29: fatal error: 'fts.h' file not found` | musl/HarmonyOS **不提供 `<fts.h>`**（`fts(3)` 是 glibc/BSD 扩展），设备 `find / -name fts.h` 无命中 | 补丁 `0003-ohos-fts-to-nftw.patch`：`__has_include(<fts.h>)` 探测；有则走原 fts 实现，没有则用 POSIX `nftw(3)`（`FTW_DEPTH\|FTW_PHYS`，语义对齐原 `FTS_NOCHDIR\|FTS_PHYSICAL\|FTS_XDEV` 的"先子后父、不跟随符号链接"）。设备实测 `nftw` 编译+运行均可用 |
| 4 | 上游 fs/stream 测试大量失败：`cio_file_unix.c:563 Permission denied`、`cannot adjust chunk size … to 4096 bytes`，随后 SIGSEGV | **`fallocate(2)` 与 `posix_fallocate(3)` 在本平台都被以 EACCES 拒绝**（HMDFS/tmpfs 不支持文件预分配），而上游只在 `errno == EOPNOTSUPP` 时才降级，于是直接把错误当结果上报 → resize 失败 → mmap 出 0 长文件 → 崩溃。独立探针：`fallocate rc=-1 errno=13`、`posix_fallocate rc=13`、`ftruncate rc=0`。知识图谱 **E523** 已在档（同一 errno 家族：HMDFS/tmpfs 不支持 fallocate 返回 EACCES） | 补丁 `0004-ohos-fallocate-ftruncate-fallback.patch`：① `fallocate` 失败时**只要不是 `ENOSPC`** 就降级到 `posix_fallocate`；② `posix_fallocate` 返回 `EACCES/EPERM/EOPNOTSUPP/ENOSYS/EINVAL/ENOTSUP` 时再降级到 `ftruncate(2)`。真实"空间不足"仍按上游语义直接报错，不会被掩成 Bus Error |
| 5 | 上游 acutest 套件把临时目录硬编码成 `/tmp/…`，`cio_create(root_path="/tmp/")` 返回 NULL | `/tmp` 在本机是**只读 erofs**（`touch /tmp/x` → `Read-only file system`），且属主 root、0755，`access(path, W_OK)` 必失败 → `check_root_path()` 直接拒绝建上下文 | 补丁 `0005-ohos-tests-tmpdir.patch`：经 `configure_file` 把 `CIO_TESTS_TMPDIR` 注入测试头，指向**可写的构建目录** `${CMAKE_CURRENT_BINARY_DIR}/test-tmp/`；改动 `tests/{CMakeLists.txt, cio_tests_internal.h.in, context.c, fs.c, stream.c, fs_perf.c, fs_fragmentation.c}`。**属于对上游测试用例的修改**，已在 PR 正文"上游测试用例修改说明"如实勾选 |
| 6 | prescan 判 `PSCAN-MUSL-002 critical：mremap syscall 在 OHOS 上不可用` | 规则是字面 grep（`kb_ref: null`，无 E 条目背书），命中在 `src/cio_file_unix.c:131` 的构建面上 | 按 §二.23 三步裁量做了**一手编译+运行探针**：`mremap(p,4096,8192,MREMAP_MAYMOVE)` 在本设备 `mremap OK old=… new=…`，rc=0；且 fs 测试真实走到 remap 路径全部通过 ⇒ 判"该命中在此设备不成立"，**不改源码**，在此留档 |
| 7 | `ci/tools/extract_upstream_tests.sh` 无法运行 | 脚本第 33 行硬编码 `WORK_DIR="/tmp/upstream_test_analysis_$$"`，`/tmp` 只读 | 本任务在 `$TASK_DIR/tools/` 放了一份只改该行的本地副本执行（不入库），已在 `feedback/pending/` 登记 |

## 源码修改

5 个补丁，全部在 `conandata.yml` 的 `patches."1.5.2"` 中声明，应用顺序即编号顺序：

| 补丁 | 类型 | 影响文件 | 来源 |
|---|---|---|---|
| `0001-add-installer.patch` | portability | `CMakeLists.txt`、`deps/crc32/CMakeLists.txt`、`src/CMakeLists.txt` | conan-center-index `recipes/chunkio/all/patches/1.5.2-0001-add-installer.patch`（逐字一致） |
| `0002-disable-pic.patch` | portability | `CMakeLists.txt` | conan-center-index `…/1.1.6-0003-disable-pic.patch`（逐字一致；conandata 对 1.5.2 同样引用它） |
| `0003-ohos-fts-to-nftw.patch` | portability | `src/cio_utils.c` | 本任务 |
| `0004-ohos-fallocate-ftruncate-fallback.patch` | platform | `src/cio_file_unix.c` | 本任务 |
| `0005-ohos-tests-tmpdir.patch` | test | `tests/CMakeLists.txt`、`tests/cio_tests_internal.h.in`、`tests/context.c`、`tests/fs.c`、`tests/stream.c`、`tests/fs_perf.c`、`tests/fs_fragmentation.c` | 本任务 |

补丁链已离线自证：把补丁按序打到**原始 tarball 解压结果**上，与实际编译所用
源码树 `diff -r` 逐字节一致（`PATCH-CHAIN-IDENTICAL`）。

## 依赖版本

- 外部编译依赖：**0**（`requirements()` 为空，`w0-deps.txt` 内容 `none`）
- 自带子树：`deps/crc32`（编译成 `libcio-crc32.a` 并安装）、`deps/monkey/include`
  （只装头文件，供 `chunkio.h` 的 `mk_list.h` 使用）、`tests/lib/acutest`（测试框架，不安装）

## 测试与验证结果

计数口径统一为**框架注册数（acutest `TEST_LIST` 条目）**，读数全部来自真实输出：

```sh
# 上游套件清点（CIO_TESTS=On 的构建树）
$ ctest -N                     # Total Tests: 4
$ for p in cio-test-context cio-test-memfs cio-test-stream cio-test-fs \
           cio-fs_perf cio-fs_fragmentation; do ./$p --list; done
#  context 3 / memfs 1 / stream 1 / fs 11  = 16（ctest 注册）
#  fs_perf 6 / fs_fragmentation 2          = 8（上游 add_test 被注释）
#  合计 N = 24
```

| 口径 | 数值 |
|---|---|
| 上游用例数 N（acutest 注册案例，候选数法取最大） | **24** |
| 其中 ctest 注册并执行 | 16（4 个程序） |
| 其中上游注释掉 `add_test` 的性能程序，由配方直接执行 | 8（2 个程序） |
| 上游断言数（`TEST_CHECK`，单列口径） | 145（context 22 + memfs 5 + stream 2 + fs 98 + fs_perf 7 + fs_fragmentation 3） |
| `test_package` 消费者断言（鸿蒙特有测试） | 17 |

设备实测（探索轮，全部 PASS）：

```sh
$ ctest --output-on-failure
100% tests passed, 0 tests failed out of 4
$ ./tests/cio-fs_perf            # SUCCESS: All unit tests have passed.（6/6）
$ ./tests/cio-fs_fragmentation   # SUCCESS: All unit tests have passed.（2/2）
$ ./test_chunkio                 # assertions=17 failures=0（消费者程序，独立编译链接）
```

## 注意事项

- **对上游测试用例有修改**（补丁 0005，临时目录由 `/tmp/…` 改为构建目录下的
  `test-tmp/`），PR 正文按模板勾选"是"并逐条说明；未删除、未跳过任何用例。
- 包型为**纯静态库 + 头文件**：无 `bin/`，按 R38/L0k **不创建** `commands.json`
  （L0k 对"库类型不应有 commands.json"是 warn 级，本包按库类走）。
- `tests` 选项默认 ON，但上游测试程序链接的是 `chunkio-static`，所以
  `shared=True` 时配方会把 `CIO_TESTS` 置 OFF 并打印说明（不会静默失败）。
- 性能程序 `cio-fs_perf` 是全套里最慢的一支（`write_up_down_10000` 单例最重），
  设备实测 `cio-fs_perf` ≈73s、`ctest`（4 个注册程序）≈5s、
  `cio-fs_fragmentation` 亚秒级 —— 合计约 80s，不构成 CI 超时风险
  （CI 单包超时默认 3600s）。
