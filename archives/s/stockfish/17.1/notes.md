# stockfish 17.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-12
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. Downloaded NNUE neural network files (nn-1c0000000000.nnue, nn-37f18f62d772.nnue) from tests.stockfishchess.org
2. Built with: `make ARCH=armv8 COMP=clang RTLIB=compiler-rt -j1 stockfish`
3. Installed binary to staging: `$TEST_PREFIX/$DEFAULT_PREFIX/bin/stockfish`
4. Installed binary locally: `$DEFAULT_PREFIX/bin/stockfish`
5. Verified: `echo "quit" | $DEFAULT_PREFIX/bin/stockfish` → "Stockfish 17.1 by the Stockfish developers"
6. Packaged: `ohc-run.py package stockfish 17.1`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-latomic` linker error | OpenHarmony SDK lacks libatomic; aarch64 has built-in 64-bit atomics | Use `RTLIB=compiler-rt` to skip `-latomic` in Makefile |
| 2 | NNUE files not in source | Stockfish embeds .nnue via INCBIN at compile time | Downloaded nn-1c0000000000.nnue and nn-37f18f62d772.nnue manually from tests.stockfishchess.org |
| 3 | Empty version in build context | init-build couldn't parse version from sf_17.1 tag URL | Manually set version to 17.1 |

## 源码修改

No source modifications required. Stockfish compiles cleanly on aarch64/musl with ARCH=armv8.

## 依赖版本

- clang 15.0.4 (OpenHarmony SDK)
- GNU Make 4.4.1
- pthread (system)

## 验证结果

```bash
$ echo "quit" | $DEFAULT_PREFIX/bin/stockfish
Stockfish 17.1 by the Stockfish developers (see AUTHORS file)

$ file $DEFAULT_PREFIX/bin/stockfish
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| stockfish-17.1-ohos-aarch64.tar.gz | 77172KB | 预编译包（含 ELF 签名） |
| stockfish-17.1-ohos-aarch64-debug.tar.gz | 184KB | Debug symbols |

## 注意事项

- Stockfish Makefile uses `../scripts/net.sh` for NNUE download, which breaks after src directory promotion. Must download .nnue files manually before building.
- `RTLIB=compiler-rt` is required on OpenHarmony to avoid `-latomic` linker error (libatomic not available, but unnecessary on aarch64).
- ARCH=armv8 is the correct target for aarch64 OpenHarmony. ARCH=armv8-dotprod could also work if dotprod SIMD extension is available.
- NNUE network files are embedded into the binary via INCBIN, so the binary is self-contained (~78MB with embedded networks).
---

**编译结束**: 2026-06-15 11:52
**最终状态**: built
---

**编译结束**: 2026-06-15 15:48
**最终状态**: built
