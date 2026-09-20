# Basis Universal v2_1_0r 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub 下载 basis_universal v2_1_0r 源码
2. 使用 CMake 构建：
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release \
         -DBASISU_EXAMPLES=OFF \
         -DBASISU_OPENCL=OFF
   make -j2
   ```
3. 产物：
   - `bin/basisu` — CLI 工具（编码器/转码器）
   - `libbasisu_encoder.a` — 静态库（包含 encoder + transcoder 实现）

## 遇到的问题与解决方案

### qsort_r 兼容性问题

**问题**: OHOS 使用 musl libc，不提供 GNU 签名的 `qsort_r()`。上游 zstd 的 `stableSort()` 函数在 Linux 上默认定义 `_GNU_SOURCE` 并调用 `qsort_r()`，导致链接时 `undefined symbol: qsort_r`。

**解决方案**: 应用 `patches/0001-zstd-zstd.c.patch`，在 zstd.c 两处 `_GNU_SOURCE` 守卫中增加 `&& defined(HAS_QSORT_R)` 条件。conanfile.py 的 `generate()` 方法仅在非 OHOS 平台设置 `-DHAS_QSORT_R`，OHOS 上不定义此宏，代码走 C90 fallback 路径（使用 `g_coverCtx` 全局变量 + `qsort()`）。

**影响范围**: 仅影响 `zstd/zstd.c` 中两处宏定义，无运行时行为改变。

## 上游测试

basisu v2_1_0r 上游存在完整的自动化测试套件 `basisu -test` (== `-test_ldr`)，定义在：
- `basisu_tool.cpp:test_mode_ldr()` — 测试主循环
- `g_etc1s_uastc_4x4_ldr_test_files[]` — 28 个测试输入声明

测试流程：对 `test_files/` 下 28 个 PNG 各执行 ETC1S level 1 / ETC1S level 128 / UASTC LDR 4x4 编码，校验压缩文件大小（±4.5%）与 PSNR（±0.3）。退出码 0 = 通过。

test_package 通过调用已安装的 basisu 二进制 + 随包发布的 28 个 PNG fixtures 来完整执行该上游测试套件。

注：本地 HMDFS 环境无法直接执行 ELF 二进制（SELinux 限制），测试在 CI 环境中执行。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/basisu | CLI 工具（编码器/转码器） |
| lib/libbasisu_encoder.a | 静态库（encoder + transcoder） |
| include/basis_universal/*.h | 公共头文件 |
| res/test_files/*.png | 28 个 LDR 测试输入 |


- 同软件其他版本: basis_universal/2.1.0 (v2_1_0 tag)
- 上游仓库: https://github.com/BinomialLLC/basis_universal
- 许可证: Apache-2.0
## 参考
- 上游仓库: https://github.com/BinomialLLC/basis_universal
---

**编译结束**: 2026-09-17 13:29
**最终状态**: built
