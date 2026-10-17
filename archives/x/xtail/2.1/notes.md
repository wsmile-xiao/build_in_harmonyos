# xtail 2.1 — OpenHarmony PC aarch64 适配笔记

## 源码与 W0
- 源仓库：`https://salsa.debian.org/debian/xtail.git`；使用其 `upstream/2.1` 官方标签归档（不是 Debian 重打包）。已下载两次，SHA256 一致：`f43fc0a730e86cb123e2dd2982e6174fea0e64df3652c4a35286cb9d93557adf`。
- 依赖：仅目标系统 libc；无外部 Conan requires，W0 不需查询额外包；仓库无本包历史归档。
- 构建系统：预生成 GNU Autoconf configure + Makefile.in；本机 Conan 2.29.1、OHOS NDK clang，目标 aarch64-linux-ohos，宿主 x86_64。
- 许可证：Salsa Debian 官方 `debian/copyright` 标注上游 Unlicense（`debian/*` 独立 BSD-3-Clause）。

## R51 上游测试清点
- 解包后的 `tests/`/`test/` 目录 0 个；上游源码自带 C 源 3 个，没有测试源、没有 CTest/pytest 注册（各 0）。
- 实际执行 `make check`：`make: *** No rule to make target 'check'. Stop.`；故上游测试 N=0、实际 N′=0，**不宣称 0/0 通过率**。
- 补齐 `test_package/test.c`：aarch64 原生 runner 执行包内 `bin/xtail`，监视文件写入并断言新增内容。x86 runner 验证包内 AArch64 ELF 存在与目标架构，但跳过动态交付二进制的**功能运行**；不能将跳过计为功能通过。W3 的 L1e 破坏性反向验证若删去 `bin/`，`test()` 会失败，证明测试与交付包实质绑定。

## 编译、问题和修复
1. `CC=<NDK>/aarch64-unknown-linux-ohos-clang CFLAGS=-O2 ./configure --host=aarch64-linux-ohos --prefix=/usr` 成功。
2. 第一次 `make -j2`：`/bin/sh: 1: autoconf: not found`；老版本预生成的 `configure.in` 比归档的 `configure` 新，Makefile 自动重生成脚本。配方在构建前仅 `os.utime` 更新发布版 `configure` 和 `config.h.in` 的时间戳，不安装 autoconf、不变更上游文件内容。知识引擎 E232 是**原生 OHOS shell 无法启动 configure**，与本次缺 autoconf 不同，不照搬其解法。
3. 再次 `make`：`miscfuncs.c:68:26: error: use of undeclared identifier 'MAXNAMLEN'`。源文件错误地用 BSD 文件名最大长度当作完整路径数组长度。`0001-miscfuncs.c.patch` 加 `<limits.h>`、`PATH_MAX` 和目录/文件名长度边界检查，目标和其它 POSIX 平台都适用。知识引擎 E032 针对 dirent 特性宏，未覆盖 `MAXNAMLEN`；新增 `knowledge/drafts/E550-draft-D79C.{kv,md}` 草稿。
4. 首次 `conan-verify` 的 G2：`xtail.c:3:10: fatal error: 'config.h' file not found`。Conan out-of-source 将 `config.h` 放在构建子目录，老 Makefile 仅 `-I$(srcdir)`；在 `AutotoolsToolchain.extra_cflags` 添加本次私有 `self.build_folder` 的 `-I`，未使用共享前缀。知识图谱 E540（runner PATH 缺工具）为误命中，不按建议改 PATH。
5. 首次 `finish` W3 L1e：`negative test: test does not depend on package`。原始 `test()` 在 x86 完全跳过，没有访问被测包，破坏性反向验证也通过；现先校验真实交付 `bin/xtail` 的 ELF/aarch64 头，缺包时必失败，只有原生目标运行 `test.c` 功能测试。静态副本 QEMU 的 2/2 功能测试与交付产物的 ELF 校验是不同证据，不互换。
6. `make -j2` 后得到 aarch64-linux-ohos 动态可执行文件；用同一批 `.o` `clang -static` 重链本机 QEMU 验证副本。交付物仍为配方编译生成的动态 `bin/xtail`，**未声称其在 x86 runner 实跑**。

## 测试证据
- `qemu-aarch64 /root/tmp/xtail-ohos-static <test-file>`：文件追加监视 1/1 通过（`XT-append-file` 出现在输出）。
- `qemu-aarch64 /root/tmp/xtail-ohos-static <long-dir>`：总路径超过 255 字节时目录中新文件发现与内容输出 1/1 通过（`XT-long-directory-scan` 出现在输出）；共 2/2 静态重链功能检查通过。
- `test_package/test.c` 原生目标功能测试仍待 CI 运行；本地 x86 功能 0/1、跳过 1，不把跳过算通过。W3 L0、L1、L5 和 L1e 破坏性反向验证均通过：实际卸去包内 `bin/` 后 `test()` 失败。
- `finish` 的可选 G0 旧脚本报 `configure: warning: []: invalid host type` 和 `C compiler cannot create executables`（未注入本次 Conan 交叉编译工具链），不代表 G2/W3 失败；`packaging/` 与 `*.tar.gz` 属废弃交付形式；全仓 SUMMARY 生成时报 `'str' object has no attribute 'append'`，均未变更框架文件。
- 编译器提示 `strcmp` 隐式声明及旧式 `sleep` 原型、`size_t` 打印格式警告；无 `-Werror`、本次不对无关代码作额外清理。

## 交付
`conanfile.py`、`conandata.yml`（版本键 SHA256）、`patches/0001-miscfuncs.c.patch`、`test_package/`、软件级 `commands.json`；本地构建缓存、QEMU 重链副本不随 PR 提交。
---

**编译结束**: 2026-09-24 22:22
**最终状态**: built
