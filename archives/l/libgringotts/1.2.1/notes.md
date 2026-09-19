# libgringotts 1.2.1 适配笔记

## 编译环境
- 构建系统: autotools (configure + libtool + make)
- 编译日期: 2026-09-19
- 编译器: clang 15 (aarch64-linux-ohos)
- 状态: published

## 编译步骤

1. `conan create` 进入源码目录，apply 补丁（本次无源码补丁）。
2. `generate()` 阶段：`AutotoolsToolchain` 注入交叉工具链；recipe 额外注入
   `libmcrypt-config` shim（libmcrypt conan 包不携带该脚本，上游 configure
   通过 `libmcrypt-config --libs/--cflags` 探测 libmcrypt）。
3. `build()`：打 OHOS autotools 补丁（config.guess/sub 的 OHOS hook、umask
   077→022、install-sh/missing/mkinstalldirs 的 shebang 修正），`chmod +x configure`，
   经 CONFIG_SHELL 调用 `configure --prefix=/ --disable-shared --enable-static`，
   `make -j1`，`make install DESTDIR=<package_folder>`。
4. 所有构建命令的输出重定向到日志文件，规避 OHOS worker 下编译器输出被静默
   吞掉导致的"假成功"。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `MCrypt library not found` | libmcrypt conan 包不提供 `libmcrypt-config` 脚本，上游 configure 依赖它 | recipe `generate()` 写入 `libmcrypt-config` shim 并加入 PATH，按依赖 cpp_info 回显 -I/-L/-l |
| 2 | 旧 autotools (2003) 在 OHOS 上 host 探测/链接异常 | config.guess/sub 不识别 `aarch64-linux-ohos`；libtool 调系统 ar/ranlib | 复用 libmcrypt/mhash 的 OHOS 修复：config.guess/sub hook + AR/RANLIB/NM/LD/STRIP→llvm 工具 |
| 3 | 交叉编译时编译器报错被静默吞掉 | OHOS worker 下 `self.run` 默认继承 stdout 会被丢弃 | build() 用 `self.run("cmd > log 2>&1")` 并把退出码写入 .rc 文件用于判错 |

## 源码修改

无。上游 1.2.1 源码（SourceForge 官方 tarball，md5 b2b1bad56ef33153f251ccd9500860be）
在 aarch64-linux-ohos + clang 15 下无需补丁即可编译通过。

## 依赖版本

- libmcrypt/2.5.8
- mhash/0.9.9.9
- zlib/1.3.1
- bzip2/1.0.8

## 验证结果

```bash
# test_package 消费者测试（真实调用 API 做加解密往返）
grg_test.dat 生成 + grg_decrypt_file 还原 -> memcmp 一致
OK: libgringotts encrypt/decrypt roundtrip verified
```

## 注意事项

- libgringotts 为**库**（非命令行工具），无需 `commands.json`（CLI 包才需要）。
- 上游 `make check` 的 `check-local` 硬编码 `gcc test.c` 且需本机执行，交叉编译下
  不在 recipe 内运行；等价验证由 test_package 的 API 往返测试承担。
- 运行时使用 `/tmp` 的临时文件接口（`grg_tmpfile_*`），OHOS 下需 `/tmp` 可写，
  但核心文件加解密 API 不依赖 `/tmp`，test_package 已覆盖。
- 上游 `AC_CHECK_FILES(/dev/random)` 在构建机探测到 /dev/random 即定义
  `HAVE__DEV_RANDOM`，OHOS 运行时存在 `/dev/random`，行为正常。
---

**编译结束**: 2026-09-19 11:35
**最终状态**: built
