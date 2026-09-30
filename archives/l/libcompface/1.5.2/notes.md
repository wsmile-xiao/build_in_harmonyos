# libcompface 1.5.2 适配笔记

## 编译环境
- 构建系统: autotools（configure + Makefile.in）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4 / llvm-ar / llvm-ranlib
- 目标平台: HarmonyOS PC arm64（OHOS/armv8）
- 状态: built（待 Conan/W3/PR 流程完成）

## 源码与依赖
- 权威源码镜像: https://github.com/SvitloLinux-pkgs/compface/tree/1.5.2（vanilla source mirror，源码文件与上游归档一致）
- 下载 URL: https://github.com/SvitloLinux-pkgs/compface/archive/1.5.2.tar.gz
- SHA256: 36c142990e423cc275147745b60b6174e501c967783d3059185a1d234fc42d32
- 编译依赖: 无
- 上游源码以多根目录归档解压；Conan `source()` 使用 `strip_root=True`。

## 编译步骤
```bash
CC=clang AR=llvm-ar RANLIB=llvm-ranlib CFLAGS='-O2 -fPIC -fcommon' \
  ./configure --prefix="$DEFAULT_PREFIX"
make -j1
```

上游 Makefile 提供静态 `libcompface.a` 和 `compface`/`uncompface` 工具，不提供 shared-library 构建路径。上游 `OBJECTS` 漏列 `compface.o`，且压缩/解压对象各自定义了同名旧式全局状态；适配补丁将 `compface.o` 加入库对象列表、令 `uncompface.o` 使用共享状态的外部声明，并以 `-fcommon` 保持旧式 tentative globals 的链接兼容。上游 install 目标还会对 HarmonyOS 签名 ELF 执行 `strip`，适配补丁将其改为可覆盖的 `STRIP` 变量，OHOS Conan 配方传入 `STRIP=:` 保留签名段（Linux 保持上游默认）；补丁也补齐标准 `DESTDIR` 安装语义。Autoconf 临时目录使用的 `umask 077` 也改为 HMDFS 可写的 `umask 022`。Conan 配方固定 `--enable-static --disable-shared`。

## 发现与知识
- ✅ GitHub mirror provenance, SHA-256 pinning, and the absence of an upstream test suite are recorded above.
- ✅ HMDFS requires `umask 022` for generated Autoconf temporary directories and shell-invoked `install-sh`.
- ✅ The static package must preserve HarmonyOS `.codesign` sections by disabling install-time stripping.
- ✅ The Conan consumer covers both API and CLI round-trips because the upstream archive has no formal tests.

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status` 无法创建 `confstatXXXXXX/subs.sed` | HMDFS 对 configure 内部 `umask 077` 创建的临时目录权限处理异常 | `0003-configure.patch` 将 configure 两条临时目录路径的 `umask 077` 改为 `umask 022` |
| 2 | `make install` 报 `./install-sh: Permission denied` | HMDFS 保留归档中的 `install-sh` 非可执行模式 | Conan `package()` 通过 `/bin/sh install-sh` 覆盖 `INSTALL`、`INSTALL_PROGRAM` 和 `INSTALL_DATA` |
| 3 | 上游没有 `make check` 目标 | 1.5.2 源码没有测试目录、CTest/pytest 注册或正式测试程序 | 不伪造上游测试；MANIFEST 明确 `upstream_tests: []`，由 Conan consumer test 覆盖库 API 与 CLI |
| 4 | 上游安装会 strip HarmonyOS 签名 ELF、未实现 DESTDIR，Autoconf 临时目录在 HMDFS 不可写，且静态库漏列 `compface.o`/重复定义全局状态 | install 目标直接执行 `strip`；目的变量不带 DESTDIR；configure 使用 `umask 077`；Makefile.in 只包含 `uncompface.o`；两个实现都以 `MAIN` 定义 legacy state | `0001`–`0004` 增加 DESTDIR、可覆盖 `STRIP`、改用 `umask 022`，并将两 API 与共享状态组合进一个库；配方传 `STRIP=:`/`-fcommon`，consumer test 同时调用两个 API |

## 上游测试清点（R51）
- `tests/`/`test/` 目录: 0
- 测试文件/测试程序: 0
- CTest/pytest/Autotools `TESTS` 注册: 0
- `make -j1 check`: `No rule to make target 'check'.`（exit 2，表示无目标而非测试失败）

## Conan consumer 测试
`test_package/test.c` 生成确定性的 48×48 checkerboard，执行并验证：
- `compface()` 与 `uncompface()` 库 API 往返；
- `compface`/`uncompface` CLI 往返；
- `uncompface -X` 的 48×48 XBM 输出与 288 个像素字节。
共 13 项 CHECK 断言。

## 交付物
- `lib/libcompface.a`
- `include/compface.h`
- `bin/compface`
- `bin/uncompface`
- `man/man1` 与 `man/man3` 手册页

## 注意事项
- 该包同时包含库和 CLI，软件级 `commands.json` 已声明 `compface`/`uncompface` 所属 Conan 版本。
- 预认领临时树中的 Debian orig 源仅用于勘验；交付配方改用 HTTPS 的 GitHub vanilla source mirror，不使用 Debian 重打包 URL。

### 对话 #1 — 2026-09-17
- 完成 W0/W1、源码校验、Autotools 构建、Conan 配方、consumer test、W3 本地 CI 和 clean-verify。
- `conan-verify`、`clean-verify` 与 W3 均通过；状态为 `built`，待提交流程完成。

**编译结束**: 2026-09-17 15:38
**最终状态**: built
