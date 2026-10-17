# oggfwd 0.2-git20150412.506088e 适配笔记

## 编译环境
- 构建系统: makefile（无 configure，单文件 `oggfwd.c` + 手写 `Makefile`）
- 编译日期: 2026-09-30
- 编译器: OHOS NDK clang 15（`/data/service/hnp/bin/clang`），目标 aarch64-linux-ohos
- 状态: built（W3 `conan create` 通过；published 由发布流水线置位）
- 语言预检: 纯 C（1 个 `.c` 文件 + Makefile）→ `lang-preflight` 默认口径放行

## 源码
- 上游 oggfwd（J^ / rafael2k / Philipp Schafft，GPL-2.0），Debian orig 快照（git 506088e，2015-04-12）
- URL: `https://deb.debian.org/debian/pool/main/o/oggfwd/oggfwd_0.2+git20150412.506088e.orig.tar.xz`
- sha256: `d69f3bfa283ced9240a3cd025e776f12d46b111cf1bfcdc488ea303b0f0031bd`

## 编译步骤
1. `libshout/2.4.6` 已发布到 ohpcd（W0：`conan download libshout/2.4.6 -r=ohpcd --only-recipe` 通过），其传递依赖 libogg / libvorbis / speex / openssl 均已发布。
2. 上游 Makefile 无 configure：`CC`/`CFLAGS`/`INCLUDEFLAGS`/`LINKFLAGS` 均可由环境或命令行覆盖 → 配方零补丁。
3. `build()`：`make -C <source_folder> oggfwd CC=<conf 编译器> "INCLUDEFLAGS=<AutotoolsDeps CPPFLAGS>" "LINKFLAGS=<LDFLAGS> -Wl,--as-needed <LIBS>"`，
   头文件 / 库路径 / 链接库（`-lshout -lspeex -lvorbis -logg -lssl -lcrypto -lpthread -lm -ldl`）全部取自 Conan 依赖图，不依赖 shell 变量（R33）。
4. `package()`：手工安装 `bin/oggfwd`、`share/man/man1/oggfwd.1`、`licenses/LICENSE`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `make install` 不可用 | 使用 `install -o root -g bin`，非 root 构建与 musl（无 `bin` 组）必失败 | 不调用 `make install`，`package()` 中 `copy` 安装产物 |
| 2 | `self.conf.get("tools.build:compiler_executables:c")` 报 `does not exist in configuration list` | 该 conf 是 dict 类型，不能带 `:c` 后缀取键 | `conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")` |
| 3 | `make oggfwd` 报「没有规则可制作目标」 | `basic_layout` 下 `Makefile` 在 `source_folder`，`autotools.make` 默认在 `build_folder` 执行 | `make -C "<source_folder>"` |
| 4 | test_package 在 x86 W3 runner 上 `Exec format error` | aarch64 ELF 不能在 x86 主机执行（无 `/lib/ld-musl-aarch64.so.1`，E544） | `test()` 仅在 aarch64 主机运行消费者用例，其余主机只校验构建；本地用静态重链 + qemu 实跑 |
| 5 | 假 Icecast 服务器握手卡死 | libshout 默认 `-T auto` 先发 `OPTIONS * HTTP/1.1` + `Upgrade: TLS/1.0` 探测；且 libshout 2.4.6 先发**不带凭据**的 `SOURCE` 请求，收到 401 后才带 Basic 认证重试 | 测试中按 usage 是否含 `[-T ` 决定加 `-T disabled`；假服务器模拟 Icecast：无凭据 → 401 + `WWW-Authenticate`，带凭据 → 200 |

## 源码修改
无（`patches/` 为空，`conandata.yml` 无 patches 节）。

## 依赖版本
- libshout/2.4.6（→ libogg/1.3.6、libvorbis/1.3.7、speex/1.2.1、openssl/3.5.6.1）
- libogg / libvorbis 在制品仓中仅有共享库（`libogg.so` / `libvorbis.so`），故 `bin/oggfwd` 动态依赖它们（运行期由 Conan 运行环境 / hnp 依赖解析）；
  `-Wl,--as-needed` 去掉了未使用的 `libvorbisfile` / `libvorbisenc` NEEDED 条目。

## 上游测试清点（R51）
- 上游源码包仅 `oggfwd.c` / `Makefile` / `oggfwd.1` / `README` / `ChangeLog` / `LICENSE` / `.gitignore`：**无 `tests/` 目录、无 ctest / pytest、Makefile 无 `check`/`test` 目标** → 上游测试 N=0，N′=0。
- 由 `test_package` 补真实功能测试（见下）。

## 验证结果

- W3 `conan create`（ohos-aarch64 profile）通过，产物为 `ELF 64-bit LSB pie executable, ARM aarch64`，解释器 `/lib/ld-musl-aarch64.so.1`。
- 鸿蒙特有测试（rule12）：`test_package/test_fake_icecast.c`（CMake 构建的消费者程序）在本地起假 Icecast 服务器，
  fork/exec 被测包安装的 `bin/oggfwd`，4 个场景共 11 项断言：
  usage 与退出码 1、缺参被拒、连接建立、401 挑战后凭据重试、挂载点、HTTP Basic（`source:hackme`）、`-n` 覆盖 `-m` 元数据文件的 name、
  `-m` 文件 description 到达服务器、`-g` genre 到达服务器、空输入 `Connected to server` + `Total bytes read: 0` + 退出 0、连接被拒 `Error connecting` + 退出 1。
- 本地实跑证据（x86 runner，E544：动态产物跑不起来）：用同源 `oggfwd.c` 加静态 libshout / speex / openssl 与本地静态编译的 libogg / libvorbis
  `-static` 重链 `oggfwd-static`，消费者程序同样 `-static` 编译，`qemu-aarch64 ./test_fake_icecast_static ./oggfwd-wrap.sh`
  → `ALL PASSED (0 failure(s))`，退出码 0（11/11 PASS）。**这不等于交付产物（动态链接）已实跑**；
  交付产物的运行时用例接入 `test_package`，由 aarch64 CI 主机在 `conan create` 中执行。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/oggfwd` | Icecast 源客户端（commands.json 已声明） |
| `share/man/man1/oggfwd.1` | 手册页 |
| `licenses/LICENSE` | GPL-2.0 |

## 注意事项
- 源 URL 使用 Debian 官方 pool 的 `orig.tar.xz`（上游仅 git 快照，无正式 release 包；GitHub / GitLab 官方归档不可达）；sha256 已核对。
  本地 PF 闸 PF7（Debian 下游重打包源）命中，属官方托管例外——任务发起人已明确批准，在 PR 正文登记，建 PR 时使用 `--no-preflight`；同形态先例：`archives/a/a52dec`、`archives/a/aalib` 等。
- `oggfwd` 在读到 stdin 首块数据（或 EOF）之后才 `shout_open`；测试用 `/dev/null` 作 stdin 即 EOF，可触发握手。
- 测试写元数据文件使用 `$TMPDIR`（OHOS `/tmp` 只读，E002），未设置时退回当前目录。
---

**编译结束**: 2026-09-30 01:00
**最终状态**: built
