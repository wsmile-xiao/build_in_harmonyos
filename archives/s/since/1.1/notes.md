# since 1.1 适配笔记

## 编译环境
- 构建系统: makefile（上游明确拒绝 autotools，见 Makefile 首行注释）
- 编译日期: 2026-09-21
- 编译器: aarch64-unknown-linux-ohos-clang（Conan profile `ohos-aarch64`）
- 状态: built（配方验证与 W3 本地 CI 均通过；制品上传由 CI release 流水线在合并后执行）
- 依赖: 无（仅 libc，POSIX + 可选 inotify）

## 源码来源与权威性

上游主页 `http://welz.org.za/projects/since` 只提供明文 HTTP（无 HTTPS 服务，
`curl https://welz.org.za` 连接被拒），不符合 R39/PF7 的 https 官方源要求。
因此取 Debian packaging 仓库 `salsa.debian.org/debian/since` 的 **upstream 分支**
（`upstream/1.1` tag，gbp 保存的纯上游树，不含 `debian/` 目录）。

已做两项核验：

1. **内容等价**：salsa archive 解包后与上游原始 tarball 逐文件 sha256 完全一致
   （since.c `a5ccc393dd37d51b6cf1df24450a07d9c0b027eec081afff665fa7069159e535`、
   Makefile `41c9a974…`、README `2f86a565…`、COPYING `8ceb4b9e…`、since.1 `31624c69…`），
   即非 Debian 重打包，无 `+dfsg` 改动。
2. **下载稳定**：同一 URL 连续两次下载 sha256 相同
   （`29428b198d617309f888b19247c5b192ecaebf42a76f8a1ede2650e52cb53993`）。

## 编译步骤

```bash
# 交叉编译（Conan 之外的手工打通）
make CC=$NDK/llvm/bin/aarch64-unknown-linux-ohos-clang CFLAGS="-O2 -Wall"
# → since: ELF 64-bit LSB pie executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1
```

配方中 `build()` 只做一件事：`make CC="<conf 取得的 clang>" -j1`，
CFLAGS/CPPFLAGS/LDFLAGS 由 `AutotoolsToolchain` 环境注入（R33，不依赖裸 shell 变量）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile 写死 `CC = gcc`，且 `CFLAGS =` 整行覆盖 | 1998 年的手写 Makefile，未考虑交叉编译 | 补丁改为 `CC ?=` / `CFLAGS ?=`，编译行补 `$(CPPFLAGS) $(LDFLAGS)` |
| 2 | inotify 特性由 `test -f /usr/include/sys/inotify.h` 决定 | 探测的是**构建机**头文件，交叉编译时与目标 sysroot 无关；在无 `/usr/include` 的机器上会静默丢掉 `-DUSE_INOTIFY`，产出行为不可复现 | 补丁改为用目标编译器探测：`$(CC) -E -x c -include sys/inotify.h /dev/null`（OHOS sysroot 有该头，实测启用） |
| 3 | `refresh-patch --auto` 报「无有效新补丁」，patches/ 为空 | `init-build` 用**硬链接**创建 `.work`（与 `.orig` 同 inode），原地写回的编辑器把 `.orig` 一起改了，diff 恒为空 | 还原 `.orig`（从 tarball 重解）并断开硬链接后重新生成；已沉淀为知识草稿 `E543-draft-7C1A` |
| 4 | 本机（x86_64）无法运行交叉产物做功能验证 | OHOS musl 动态加载器 `/lib/ld-musl-aarch64.so.1` 在 qemu-user 下段错误（静态链接可运行） | 功能验证用 `-static` 编译的副本在 qemu 下实跑；**发布产物仍是动态链接**，未因测试改变链接方式；已沉淀为知识草稿 `E544-draft-7C1A` |
| 5 | test_package 的 skip 判据取自被测二进制的退出码 | 「进程启动了但返回非 0」被误判成「本机无法执行」，在 aarch64 真机上会把启动即失败的产物吞成通过（W4 审计 P1） | 改为：仅当输出带明确的不可执行特征（缺 musl loader / Exec format error / qemu signal）才算不可执行；且 aarch64 宿主上探测失败一律判 fail 不允许 skip |

## 源码修改

`patches/0001-Makefile.patch`（6 增 5 删，仅 Makefile）：外部工具链变量优先 +
inotify 用目标编译器探测。补丁中**不含任何平台宏**（`__OHOS__` 等），
对 Linux/OHOS 行为一致。

## 上游测试清点（R51）

| 项 | 结果 | 证据 |
|---|---|---|
| 上游 tarball 内测试目录 | 0 个 | `since-upstream-1.1` 仅 5 个文件：COPYING / Makefile / README / since.1 / since.c |
| 上游注册的测试用例 | 0 个 | Makefile 只有 `since` / `install` / `clean` 三个 target；`make check` → `No rule to make target 'check'`；无 configure、无 ctest/pytest |
| 可运行的上游测试 | N/A | 上游确无测试，故 N = 0，无「跑与不跑」之分 |
| 打包层测试（非上游 tarball） | 6 条断言 | Debian autopkgtest `debian/tests/simple`（同一 salsa 仓库 master 分支，不在 upstream tarball 内） |

补全动作：把 Debian autopkgtest 的 6 条断言语义移植进 `test_package/test_since.py`，
外加 1 条产物校验（aarch64 ELF + 可执行位），共 7 条断言。

## 验证结果

```bash
# 1) 交叉编译产物
$ file since
since: ELF 64-bit LSB pie executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1

# 2) Debian autopkgtest simple（6 条断言）在 qemu-aarch64 下实跑（静态副本）
$ PATH=<qemu wrapper>:$PATH AUTOPKGTEST_TMP=... sh -x debian/tests/simple
TESTING: -z / default action / reset / -z multiple files / default action multiple files
→ 全部通过，脚本 set -e 跑到结尾，rc=0   # 6/6

# 3) test_package 套件（test_since.py）对静态副本实跑：8/8
$ python3 test_package/test_since.py <含静态副本的目录>
[ok] artifact: ... (aarch64 ELF, executable)
[ok] binary runs: since 1.1
[ok] -z discards existing content and records state (single file / second file)
[ok] default action prints appended line             [ok] truncation is detected and reported
[ok] -z emits discard headers for multiple files     [ok] multi-file output carries per-file headers
[ok] -f follow mode streams a line appended after start (inotify/poll path)
[summary] runtime checks: 7/7 passed     # 加 artifact 校验共 8 条断言

# 4) 门禁有效性自验（W4 审计反例）：把一个「能启动但立即返回 1」的
#    aarch64 静态二进制冒充产物，套件必须判失败而不是 skip
$ python3 test_package/test_since.py <坏二进制目录>
[summary] runtime checks: 0/7 passed   →  rc=1   # 加强 -z 断言后零输出产物一分不得
$ python3 test_package/test_since.py ""              # 包里没有 bin/since
[fail] since binary not found (bindir='')  →  rc=1   # 无 PATH 回退，测试离不开被测包

# 5) conan create 自动触发的 test_package（本机 x86_64，动态产物）
artifact 校验通过；动态产物因缺 musl loader 无法执行 → 运行时断言如实打印 skip 并附探测原文，
CI（aarch64 真机）上该分支自动转为实跑 6 条断言；若在 aarch64 上启动失败则直接判 fail。
```

qemu 限制说明：`qemu-aarch64` 可运行**静态**链接的 OHOS aarch64 程序；动态链接产物会在
OHOS musl loader 阶段 segfault（hello-world 同样复现，与 since 无关）。因此本机功能验证
用静态副本完成，发布产物保持动态链接不变。

## 注意事项

- `since` 的状态文件默认写 `$HOME/.since`，`$HOME` 不可用时回退 `/tmp/since`；
  鸿蒙 `/tmp` 只读（E002），实际使用请确保 `$HOME` 可写或用 `SINCE` 环境变量指定路径。
- 产物为命令行工具，已按 R38 在软件级目录提供 `commands.json`。
---

**编译结束**: 2026-09-21 01:56
**最终状态**: built
