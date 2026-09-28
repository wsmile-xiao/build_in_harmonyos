# jpegqs

JPEG 去伪影工具与库：依据 JPEG 量化表恢复 DCT 系数精度，输出量化表为 1 的 JPEG。
交付物为命令行程序 `jpegqs` 与静态库 `libjpegqs.a`（含公共头 `libjpegqs.h`）。

- Upstream: https://github.com/ilyakurdyukov/jpeg-quantsmooth
- Version: 1.20210408
- Current package: `archives/j/jpegqs/1.20210408`
- Supported OpenHarmony architecture: armv8
- 依赖: `libjpeg/10`（`libjpegqs.c` 直接包含 `jpeglib.h`，CLI 走 IJG transcode API）
- 构建口径: `make SIMD=none MTOPTS= JPEGLIB="-I<libjpeg>/include -L<libjpeg>/lib -ljpeg" -j1 app lib`
  （`SIMD=none` 关掉上游 `SIMD := native` 的 `-march=native`，避免把构建机 ISA 烧进产物；
  `MTOPTS=` 去掉 `-fopenmp`，`quantsmooth.h` 的 OpenMP 循环都在 `#ifdef _OPENMP` 内且有
  `omp_get_thread_num() -> 0` 退化实现，标量路径结果不变）
- 未测面: `SIMD=none` 是**取档决定**（用上游自带开关换取产物可复现），它使上游
  SSE2/AVX2/AVX512/NEON 分支——含 aarch64 向量路径（`quantsmooth.h:132-134` 在
  `__aarch64__` 下 `#define USE_NEON`、`idct.h:91` 与 `idct.h:458` 的 NEON fdct/idct 核）
  ——完全不进入本包的编译与测试面 ⇒ 本包仅交付并验证**标量路径**，
  **NEON/SIMD 面未编译、未测试**，不主张其已验证；这不是平台限制。
- 源通道: 上游官方 release tag 归档 `.../archive/refs/tags/1.20210408.tar.gz`
  （实测与 Debian 池 pristine `.orig` 逐字节相同：同一 sha256、65410 字节、`cmp` RC=0）
- 适配路径: A（命中既有 `-march=native` 机制家族，未新建知识库条目）；测试账 12/12
