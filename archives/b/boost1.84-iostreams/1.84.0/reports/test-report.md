# boost1.84-iostreams 1.84.0 测试报告（W3 本地 CI）

日期：2026-09-05（2026-09-06 rule4 口径复核重跑仍 48/48 全绿，见 conan-create.log）
环境：OpenHarmony aarch64 本机（clang 15.0.4，aarch64-unknown-linux-ohos）
Profile：ci/conan/profiles/ohos-aarch64（os=OHOS, arch=armv8, libc++, cppstd=17, Release）

## conan create 结果

```
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
...
boost1.84-iostreams/1.84.0: [upstream-tests] TOTAL 48: 48 passed / 0 failed
boost1.84-iostreams/1.84.0: Package 'd9c564613a34ee2ecfd3d0a52a623a2c6f26eb4d' built
...
gzip round-trip OK (40 bytes compressed)
zlib round-trip OK (28 bytes compressed)
bzip2 round-trip OK (45 bytes compressed)
file_descriptor + gzip pipeline OK
mapped_file source OK
boost1.84-iostreams 1.84.0: gzip/zlib/bzip2 + file_descriptor + mapped_file OK
```

**退出码 0**，完整日志见 conan-create.log。

## 产物

- lib/libboost_iostreams.a（223,786 字节；含 zlib/gzip/bzip2 三压缩后端
  的 5 TU：file_descriptor/mapped_file/zlib/gzip/bzip2，带上游 Jamfile
  要求的 BOOST_IOSTREAMS_USE_DEPRECATED）
- include/boost/ 完整头文件树（组件包自包含）

## 上游测试（libs/iostreams/test/Jamfile.v2 test-suite iostreams 等价执行）

上游 Jamfile 测试注册条目 56（`grep -cE "test-iostreams|compile-fail-
iostreams|test-suite"` 口径，含 2 个 rule 定义行 + 1 个 test-suite 汇总
行），**真实测试目标 53 个**（无条件 45 = 44 run + 1 compile-fail；
条件 8 = bzip2_test、zlib 块 write_failure/gzip/zlib_test、lzma_test、
zstd_test、large_file_test×2）。本配置（非 Windows + zlib/bzip2 后端
启用 + lzma/zstd 未引入 + LARGE_FILE_* 未设）生效 48 项。

b2 在 OHOS 不兼容（E068），本配方在 build() 中用 clang++ 手动编译上游
测试源文件并真实运行（链接 libboost_iostreams.a + 测试期辅助库
unit_test_framework 19TU/filesystem 9TU/regex 5TU + zlib/bzip2）。

**48/48 通过**（47 run 型编译运行全过 + 1 compile-fail 型按预期编译失败）：

- run 型 47 项：array/auto_close/buffer_size/close/code_converter(+utf8
  codecvt 源)/combine/compose/component_access/copy/counter/
  deprecated_file_descriptor(带 USE_DEPRECATED 宏)/direct_adapter/
  dual_seekable/example/execute/file/file_descriptor/filtering_stream/
  finite_state_filter/flush/grep(+regex)/invert/line_filter/mapped_file/
  newline/operation_sequence/path/pipeline/read_nonblocking/regex_filter
  (+regex)/restrict/seekable_file/seekable_filter/sequence/slice/
  stdio_filter/stream_offset_32bit/stream_offset_64bit/stream_state/
  symmetric_filter/tee/wide_stream/write_failure/bzip2/gzip/zlib
- compile-fail 型 1 项：deprecated_file_descriptor 不带宏编译应失败
  （rc=1 按预期）

完整逐项结果见 upstream-tests-report.txt。

### 与上游清单的差异说明（上游真实测试目标 53 项 → 本配置生效 48 项；Jamfile 条目口径 56 项）

| 上游测试 | 排除原因 |
|---|---|
| windows_pipe_test | `<build>no <target-os>windows:<build>yes`（Windows-only，非 Windows 上游自身不构建） |
| lzma_test / zstd_test | 需系统 liblzma/libzstd（NO_LZMA/NO_ZSTD 变量语义，本包后端裁剪未引入） |
| large_file_test ×2 | 需 LARGE_FILE_TEMP/KEEP 环境变量（上游条件测试，未设即不注册执行） |

已启用后端（zlib+bzip2）对应的 4 个条件测试 bzip2_test/gzip_test/
zlib_test/write_failure_test **不在排除之列**——它们已包含在上表 48 项
中真跑通过。

## test_package（L1 下游消费冒烟）

CMake 消费者 `find_package(boost1.84-iostreams REQUIRED CONFIG COMPONENTS
iostreams)` → `boost1.84-iostreams::iostreams`，覆盖：

1. gzip 压缩 round-trip（zlib 后端经 gzip filter）
2. zlib 裸压缩 round-trip
3. bzip2 压缩 round-trip（本包 bzip2.cpp 后端）
4. file_descriptor 设备 + gzip 管道写读真实文件
5. mapped_file 内存映射源设备

全部断言通过（OHOS 侧经 llvm-objcopy + binary-sign-tool 自签名后运行，
LD_LIBRARY_PATH 指向编译器自省的 SDK libc++ 目录）。

## 依赖（W0 检查，conan download 实证）

- zlib/1.3.1 ✅（制品仓 6b129b06... 包在库）
- bzip2/1.0.8 ✅（制品仓 4b977264... 包在库）
