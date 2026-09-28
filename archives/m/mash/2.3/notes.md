# Mash 2.3 · HarmonyOS PC 适配笔记

任务 #8702，目标 aarch64 OHOS。上游 v2.3 tag 的 tarball SHA-256 为
`f96cf7305e010012c3debed966ac83ceecac0351dbbfeaa6cd7ad7f068d87fe1`。
上游提供 `configure.ac`、`Makefile.in` 和自包含的 `test/` FASTA/FASTQ 数据，
但不提供预生成的 `configure`。

## 构建与依赖

- `autoconf` 生成 configure；向 configure 传 Conan 的 `capnproto/1.3.0`、
  `gsl/2.8` 包前缀，zlib 头来自 `zlib/1.3.2`。
- OHOS SDK 的 CC/CXX 从 Conan profile `tools.build:compiler_executables` 取得。
  上游 Makefile 使用 glibc 的 `-lstdc++` 和系统 `-lz/-lpthread`；构建时改用
  clang++ 自带 libc++、Conan zlib 静态归档以及 OHOS libc。
- 制品仓 GSL 2.8 只有 `.so`，不能启用上游的 `--enable-static-gsl`（该开关
  硬找 `libgsl.a/libgslcblas.a`）。保持动态 GSL，在运行上游测试时显式
  提供 GSL 包目录的 `LD_LIBRARY_PATH`。
- OHOS 的 HMDFS 不能创建 Autoconf `umask 077` 所需的模式 0700 临时目录；
  按已有 E011/E114 去掉生成版 configure 中的 `umask 077 &&`。

## B 类新机制：glibc 版本化 memcpy 包装

上游在非 Darwin 构建中强制 include `memcpyLink.h`，其中有
`.symver memcpy,memcpy@GLIBC_2.2.5`，并以 `-Wl,--wrap=memcpy` 链接
`memcpyWrap.o`。OHOS libc 没有 `memcpy@GLIBC_2.2.5`，首轮完整链接失败：

```
ld.lld: error: undefined symbol: memcpy@GLIBC_2.2.5
```

原始对象 `llvm-nm -u` 显示 `U memcpy@GLIBC_2.2.5`；补丁把
`.symver` 强制 include、`--wrap=memcpy` 和包装对象**一起**从构建图移除，
补丁后只有普通 `U memcpy`，且包装对象不再构建。单独移除 `.symver`
会让 `__wrap_memcpy()` 内部调用再次被 `--wrap` 重写成自身；独立最小
探针以 4 次递归为上限，实测退出码 42。修复后真实 Mash 上游测试全过。
通用边界和反例见配套 `knowledge/drafts/` 草稿。

## 测试结果

`conan create` 在真机完成构建，`make test` 实际执行并比对四个参考输出：
`genomes.json`、`reads.json`、`genomes.dist`、`screen`，**4/4 PASS**。
`test_package/test_mash.sh` 对安装后的二进制做版本、草图生成、包内容查询、
自身距离零值等 **5/5** 组消费者检查，输出
`MASH_CONSUMER_SUMMARY checks=5 fails=0`。

上游 `Makefile.in` 的测试目标、四个 `diff` 命令和随包样本可在 v2.3
源码中逐项核对。构建过程只使用官方来源和已发布的 Conan 依赖。
