# minibwa

lh3 的轻量级 BWA 短序列比对工具。

## 简介

minibwa 是一个面向短读段比对的轻量级 BWA 重实现（v0.7, r421），保留
BWA-MEM 风块的映射算法核心，代码量远小于完整 BWA。主要命令：
- `index`：构建参考索引（默认 libsais + QSufSort/bwtgen 组件）
- `map`：短读段比对（支持 paired-end、甲基化 `--meth` 模式）
- `fa2bit`/`genraw`/`genbwt`：索引内部构建流程的子命令

同时提供静态库 `libminibwa.a` 与公共头 `minibwa.h`，C API 与上游
api-test 示例（`mb_idx_load`/`mb_map`/`mb_opt_init`）配合使用。

## 技术信息

- **许可证**：MIT（含可选 GPL 组件 QSufSort/bwtgen，默认启用，`gpl=0` 可关）
- **编程语言**：C99
- **构建系统**：Makefile（纯 Makefile，无 configure）
- **依赖**：zlib/1.3.1.1（gzip 输入）、pthread、m
- **SIMD 支持**：aarch64 由 ksw2 内置 s2n-lite.h NEON 翻译层原生支持

## 构建配置

在 aarch64/OHOS 平台上应使用以下参数构建：
```
make -j1 ARCH=aarch64 CC=clang AR=llvm-ar \
     INCLUDES="-I<zlib>/include" LDFLAGS="-L<zlib>/lib" \
     gpl=1 mimalloc=0
```

要点：
- `ARCH=aarch64` 显式传递（Makefile 默认取 `uname -m`，交叉场景不可靠）
- `mimalloc=0` 必须使用：mimalloc 的 malloc override 在 OHOS emulated
  TLS bootstrap 阶段于 `__emutls_get_address` 递归栈溢出（知识 E210）；
  `mimalloc=0` 是上游官方开关，回退 kalloc 分配器
- 串行 make：HMDFS 工作区无法承载 GNU make jobserver FIFO（知识 E074）
