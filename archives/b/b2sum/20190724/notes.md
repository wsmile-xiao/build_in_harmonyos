# b2sum 20190724 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，非 autotools)
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (clang 15.0.4)
- 链接器: GNU ld (/data/service/hnp/bin/ld.bfd)
- 状态: published
- 源码嵌套: BLAKE2 仓库内 b2sum/ 子目录（build_subdir=b2sum）

## 编译步骤

1. `init-build b2sum 20190724 --url=https://github.com/BLAKE2/BLAKE2/archive/refs/tags/20190724.tar.gz`
2. 嵌套源码被自动提升（b2sum/ 子目录 → 顶层），但丢失了 ../sse/ 和 ../ref/ 等兄弟目录
3. 将 ref/ 目录从完整 tarball 复制到 work 目录的父级（`/storage/Users/currentUser/tmp/builds/ref/`），以保持 `../ref/` 相对路径兼容原始嵌套结构
4. 修改 Makefile（4处修改）：
   - `CFLAGS?=-O3 -march=native` → `CFLAGS?=-fPIC -O2`（-march=native 在 aarch64 不可用）
   - `CFLAGS+=-I../sse` → `CFLAGS+=-I../ref`（使用 ref 纯 C 实现替代 SSE）
   - `FILES=b2sum.c ../sse/blake2b.c ../sse/blake2s.c ../sse/blake2bp.c ../sse/blake2sp.c` → `FILES=b2sum.c ../ref/blake2b-ref.c ../ref/blake2s-ref.c ../ref/blake2bp-ref.c ../ref/blake2sp-ref.c`
   - 链接行添加 `$(LDFLAGS)` 以支持 `-fuse-ld=`
5. `make CC=clang LDFLAGS='-fuse-ld=/data/service/hnp/bin/ld.bfd' PREFIX=$DEFAULT_PREFIX MANDIR=$DEFAULT_PREFIX/share/man NO_OPENMP=1 -j1`
6. `make install DESTDIR=$TEST_PREFIX` (staging)
7. ELF 签名 + staging 验证 + 质量门禁 G1-G4 PASS
8. `ohc-run.py package b2sum 20190724`（预编译包制作 85KB）
9. `make install`（不带 DESTDIR，安装到 $DEFAULT_PREFIX）
10. 用户验证: 全4种算法、文件哈希、BSD风格输出、官方参考向量对比均 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 嵌套源码提升丢失兄弟目录 | init-build 将 BLAKE2/b2sum/ 提升为顶层，../sse/ ../ref/ 丢失 | 将 ref/ 目录放置在 work 目录的父级，保持 ../ref/ 路径兼容 |
| 2 | SSE 实现不兼容 aarch64 | sse/blake2-config.h 要求 __SSE2__，aarch64 不支持 | 切换为 ../ref/ 纯 C 实现（FILES 和 -I 路径均改为 ../ref） |
| 3 | -march=native 不可用 | aarch64 musl 环境下 clang 不支持 -march=native | 改 CFLAGS 默认值 (?=) 为 -fPIC -O2 |
| 4 | Makefile 缺 LDFLAGS | 原始链接行只有 $(CC) $(FILES) $(CFLAGS) $(LIBS) | 添加 $(LDFLAGS) 到链接行 |
| 5 | OpenMP 不支持 | musl 环境缺少 OpenMP 运行时 | NO_OPENMP=1 禁用 |
| 6 | CFLAGS 命令行覆盖 += 不生效 | GNU Make 命令行覆盖 CFLAGS 时 += 追加不生效 | 改 Makefile 默认值 (?=)，不命令行覆盖 CFLAGS |
| 7 | G0 补丁路径不匹配嵌套结构 | promoted 结构生成 a/makefile 补丁，但原始 tarball 是 b2sum/makefile | 在 manifest.yaml 中添加 build_subdir: b2sum |

## 源码修改

- makefile: 4 处修改（CFLAGS 默认值、include 路径 ../sse→../ref、FILES 源文件、链接行加 LDFLAGS）

## 依赖版本

- 无额外依赖（纯 C 实现，仅依赖 libc）
- musl 动态链接 (/lib/ld-musl-aarch64.so.1)

## 实际执行的验证命令

```bash
$ /storage/Users/currentUser/usr/local/bin/b2sum --help
Usage: b2sum [OPTION]... [FILE]...
  -a <algo>    [blake2b|blake2s|blake2bp|blake2sp]
  -l <length>  digest length in bits
  --tag        create a BSD-style checksum
  --help       display this help and exit

$ echo "hello world" | b2sum -
fec91c70284c72d0d4e3684788a90de9338a5b2f47f01fedbe203cafd68708718ae5672d10eca804a8121904047d40d1d6cf11e7a76419357a9469af41f22d01  -

$ echo -n "" | b2sum -
786a02f742015903c6c6fd852552d272912f4740e15847618a86e217f71f5419d25e1031afee585313896444934eb04b903a685b1448b755d56f701afe9be2ce  -
（与官方 BLAKE2b 空输入参考值完全匹配）

$ echo -n "abc" | b2sum -
ba80a53f981c4d0d6a2797b69f12f6e94c212f14685ac4b74b12bb6fdbffa2d17d87c5392aab792dc252d5de4533cc9518d38aa8dbf1925ab92386edd4009923  -
（与官方 BLAKE2b "abc" 参考值完全匹配）

$ echo "hello world" | b2sum -a blake2s -
9e63cf8c57ba5a7c3019c344ae7192d12f683fb0b5fc03b21bc6d1a377977257  -

$ echo "hello world" | b2sum -a blake2bp -
dc377be11f4fc9ab6ce6a2e3e17ee012850ce815cdef6bd04d66d0ed18e910e52b74566ced847ee4d75269b6c3f54f36049ebb79cb517b0e7565c8009e08852f  -

$ echo "hello world" | b2sum -a blake2sp -
43958a843c00345bae4492cc04ecd1e47453469afeae277e067cad66244625eb  -

$ echo "hello world" | b2sum --tag -
BLAKE2b (-) = fec91c70284c72d0d4e3684788a90de9338a5b2f47f01fedbe203cafd68708718ae5672d10eca804a8121904047d40d1d6cf11e7a76419357a9469af41f22d01

$ echo "hello world" | b2sum -l 256 -
c71b05fd1d1c7bf7e928ff18e58db5193e9316416cc26ba9cc9094da80d7011e  -

$ seq 1 1000 | b2sum -
55c4cb370b45d7faf646d17ffee79a1809f5cf09205f0716b033fb47e9b99cea16b6553dfcfa81bf2673d63629d90fed9469052450a7c823a5ab4fffb944850c  -
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| b2sum-20190724-ohos-aarch64.tar.gz | 85KB (87585字节) | 预编译包（含 ELF 签名） |
| b2sum-20190724-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 质量门禁结果

| 门禁 | 结果 | 备注 |
|------|------|------|
| G0 干净构建验证 | PASS | build_subdir=b2sum, 补丁自包含 |
| G1 二进制完整性 | PASS | ELF 64-bit LSB arm64 |
| G2 功能可用性 | PASS (⚠1) | b2sum 不支持 --version（上游设计） |
| G3 可移植性 | PASS (⚠2) | 无 RPATH、ELF 签名通过 |
| G4 档案完整性 | PASS | manifest, notes, patches 完整 |

## 注意事项

- b2sum 不支持 --version 参数，仅有 --help（上游设计，非编译缺陷）
- 必须使用 GNU ld (/data/service/hnp/bin/ld.bfd) 替代 lld
- aarch64 平台必须使用 ../ref/ 纯 C 实现，不可使用 ../sse/ SSE 优化实现
- manifest.yaml 中 build_subdir: b2sum 是必需的，确保 G0 clean-verify 正确应用补丁
- Makefile 修改后使用 ../ref/ 路径（而非 ./ref），兼容原始嵌套目录结构

---
**编译结束**: 2026-06-09
**最终状态**: published