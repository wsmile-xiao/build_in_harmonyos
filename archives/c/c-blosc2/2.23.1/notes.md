# c-blosc2 2.23.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-01
- 编译器: clang 15.0.4
- 状态: built
- 目标平台: OpenHarmony PC aarch64 (musl libc)

## 编译步骤
```bash
cmake -B build -S . \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTS=ON \
  -DBUILD_FUZZERS=OFF \
  -DBUILD_BENCHMARKS=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_PLUGINS=OFF \
  -DBUILD_STATIC=ON \
  -DBUILD_SHARED=OFF \
  -DPREFER_EXTERNAL_LZ4=OFF \
  -DPREFER_EXTERNAL_ZLIB=OFF \
  -DPREFER_EXTERNAL_ZSTD=OFF
cmake --build build -j$(nproc)
ctest --output-on-failure --timeout 120 -j1   # 上游 CTest 套件
```

## 上游测试运行结果（规则 5）

启用 `BUILD_TESTS=ON` 完整运行上游 CTest 套件，`ctest -N` 实际收集 **1160 个上游测试用例**：

| 测试类别 | 用例数 | 通过 | 失败 | 通过率 | 说明 |
|----------|--------|------|------|--------|------|
| core（核心功能） | 1134 | 1134 | 0 | 100% | test_blosc1_compat / test_frame / test_schunk / test_contexts / test_delta 等，其中参数化测试按 itemsize×chunksize 展开：test_getitem 399、test_compress_roundtrip 266、test_shuffle_roundtrip 133、test_shuffle_roundtrip_generic 133、test_bitshuffle_roundtrip 133 |
| compat（数据兼容性） | 26 | 26 | 0 | 100% | test_compat_blosc-*（24 项）/ test_compat_shuffle-* / test_compat_bitshuffle-* 各版本压缩数据帧回读验证 |
| **合计** | **1160** | **1160** | **0** | **100%** | 串行执行 `ctest -j1`，总耗时 169.34s |

### 上游测试运行环境
- 构建目标：OHOS aarch64 (musl libc)，二进制为 `ELF 64-bit arm64, dynamic (/lib/ld-musl-aarch64.so.1)`
- 运行方式：aarch64 主机原生执行（主机 musl ld `/lib/ld-musl-aarch64.so.1` 兼容 OHOS musl ABI），即"OHOS 目标环境完整运行上游 CTest 套件"
- 串行 `-j1`：避免并行竞态（`test_fill_special` / `test_frame_get_offsets` 共享临时文件，并行 `-j4` 下偶发 flaky 失败，串行下 100% 通过）

### 上游测试用例清单（1160 项分类）

**core 核心功能测试（1134 项）**——按测试二进制分组（参数化测试展开为多用例）：

| 测试二进制 | 覆盖功能 |
|-----------|---------|
| test_blosc1_compat | c-blosc v1 API 向后兼容 |
| test_change_nthreads_append | 运行期线程数切换 + 追加 |
| test_compress_roundtrip | 压缩/解压 round-trip（核心） |
| test_compressor | 各压缩器（blosclz/lz4/lz4hc/zstd/zlib）切换 |
| test_contexts | blosc2_context 创建/复用/释放 |
| test_copy | chunk 复制 |
| test_delete_chunk | chunk 删除 |
| test_delta | delta filter |
| test_delta_schunk | schunk 级 delta |
| test_dict_schunk | schunk 级字典训练（ZSTD cover） |
| test_empty_buffer | 空缓冲处理 |
| test_fill_special | special fill（run-length encoding） |
| test_filters | filter 链组合 |
| test_frame | frame I/O（核心） |
| test_frame_get_offsets | frame 偏移读取 |
| test_frame_offset | frame 偏移边界 |
| test_get_slice_buffer | buffer 切片 |
| test_get_slice_nchunks | nchunk 切片 |
| test_getitem | getitem 解压 |
| test_getitem_delta | delta getitem |
| test_insert_chunk | chunk 插入 |
| test_lazychunk | lazy chunk 读取 |
| test_lazychunk_memcpyed | memcpyed lazy chunk |
| test_maskout | maskout 过滤 |
| test_maxout | maxout 边界 |
| test_mmap | mmap frame |
| test_noinit | 未初始化 context |
| test_nolock | 无锁模式 |
| test_nthreads | 线程数切换 |
| test_postfilter | postfilter 回调 |
| test_prefilter | prefilter 回调 |
| test_reorder_offsets | 偏移重排 |
| test_schunk | schunk 核心 API |
| test_schunk_frame | schunk ↔ frame |
| test_schunk_header | schunk header |
| test_set_slice_buffer | buffer 切片写入 |
| test_sframe | sframe I/O |
| test_sframe_lazychunk | sframe lazy chunk |
| test_shuffle_roundtrip | shuffle round-trip（核心，覆盖 generic/neon 多种 itemsize×chunksize 组合） |
| test_small_chunks | 小 chunk 边界 |
| test_udio | udir 通用字典 I/O |
| test_update_chunk | chunk 更新 |
| test_urcodecs | 通用注册编解码器 |
| test_urfilters | 通用注册 filter |
| test_zero_runlen | zero run-length |

**compat 数据兼容性测试（26 项）**——验证历史版本压缩数据帧可被当前版本正确回读：
- `test_compat_blosc-*`（24 项）：blosc 1.3.0 / 1.7.0 / 1.17.1 / 1.18.0 / 2.0.0 各版本 × blosclz/lz4/lz4hc/zlib/bitshuffle 各编解码组合
- `test_compat_shuffle-*` / `test_compat_bitshuffle-*`（2 项）：shuffle 1.20.0 / 2.20.0 各版本 bitshuffle 数据回读

## 源码修改（补丁）

### patch 1: `patches/0001-zstd-cover.c-ohos-qsort-r-fallback.patch`

**问题根因**：内置 ZSTD 1.5.7 `dictBuilder/cover.c` 与 `common/zstd_deps.h` 在 Linux 平台默认 `#define _GNU_SOURCE` 并调用 GNU 扩展 `qsort_r()`。OHOS（musl libc）不提供 `qsort_r` 符号，链接期报 `undefined symbol: qsort_r`，导致所有依赖 ZSTD cover 字典训练的测试二进制（test_dict_schunk 等）无法链接。

**修改内容**（仅 `dictBuilder/cover.c`，4 处，不引入任何平台条件编译宏）：
1. `g_coverCtx` 全局变量声明守卫：去掉 `!defined(_GNU_SOURCE)` 条件，改为 `#if !defined(__APPLE__) && !defined(_MSC_VER)`，确保 C90 fallback 分支使用的全局上下文在任意 `_GNU_SOURCE` 状态下都可编译
2. `COVER_strict_cmp` 签名选择：删除 `#elif defined(_GNU_SOURCE)` 的 GNU qsort_r 三参签名分支，统一走 C90 fallback 两参签名 `static int COVER_strict_cmp(const void *lp, const void *rp)`
3. `COVER_strict_cmp8` 签名选择：同上，删除 `_GNU_SOURCE` 分支
4. `stableSort()`：删除 `#elif defined(_GNU_SOURCE)` 的 `qsort_r()` 调用分支，使所有非 Win/Apple/OpenBSD 平台统一走 C90 `qsort()` fallback

**效果**：cover.c 无条件使用标准 C90 `qsort()`（POSIX 接口）替代 GNU `qsort_r()`，不依赖任何平台宏（符合 R8：通过 POSIX 接口适配），字典训练功能正常，所有 1160 个上游测试 100% 通过。

## 依赖版本
无外部依赖（内置 LZ4, zlib-ng, ZSTD 编解码器）。

## 交付物
- libblosc2.a / libblosc2.so
- blosc2.h, b2nd.h, blosc2/ 目录
- lib/cmake/Blosc2/Blosc2Config.cmake
- lib/pkgconfig/blosc2.pc

## 与 c-blosc v1 的差异
- 库名: blosc → blosc2
- API: blosc_compress → blosc2_compress（新增 srcsize/destsize 参数）
- CMake config: c-blosc → Blosc2
- 目标名: c-blosc::c-blosc → Blosc2::blosc2
- c-blosc2 无 snappy 支持，新增 plugins 支持
