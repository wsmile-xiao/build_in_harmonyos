# utmps 0.1.3.4 适配笔记

## 编译环境

- 设备：HarmonyOS PC（aarch64，OHOS），主检出 `~/build_in_harmonyos`，任务 worktree `~/qzy/hw-6-utmps-0.1.3.4`，分支 `feat/utmps-0.1.3.4`。
- 工具链：`/data/service/hnp/bin/clang`（profile `ci/conan/profiles/ohos-aarch64`，`tools.build:jobs=2`，实际构建按 skarnet 要求降到 `-j1`）。
- Conan 2.29.1，独立 `CONAN_HOME=~/tmp/ch/home-hw-6-utmps`（`remotes.json` 从已验证 home 复制，含 `ohpcd` 远端）。
- 参考先例：同族 `archives/e/execline/2.9.9.2`、`archives/s/skalibs/2.15.1.0`、`archives/s/s6-dns/2.4.1.0`。

## 软件概述

skarnet 的 utmps：对 utmp/wtmp 的重写，提供 `libutmps` 客户端库与三个程序（`utmps-utmpd`、`utmps-wtmpd`、`utmps-write`），由 daemon 独占 utmp/wtmp 文件、客户端经 socket 存取。

## 编译步骤

1. `source()`：`get(self, **conan_data["sources"], strip_root=True)`。
2. `build()`：`./configure --prefix=<package_folder> --disable-shared --with-sysdeps=<skalibs>/lib/skalibs/sysdeps --with-include=<skalibs>/include --with-lib=<skalibs>/lib` → `make -j1` → **`make -j1 check`**（真实执行上游测试入口，实测零用例） → `make -j1 install`（安装直接落在 package_folder，故 `package()` 只补许可证）。
3. `package_info()`：`libs=["utmps"]`、`includedirs=["include"]`、`bindirs=["bin"]`（本包全部程序装入 `bindir`，包树内无 `sbin/`），并对 skalibs 声明 `transitive_headers/transitive_libs`。

## configure 参数说明

- skarnet 自研 configure **不是 autotools**：不认 `--host/--build`，也不用 `AutotoolsToolchain`；编译器由 conan 的 `conanbuild` 环境提供。
- `--with-sysdeps` 必须指向 skalibs 包内的 `lib/skalibs/sysdeps`（平台探测结果目录）；`--with-lib` 指向含 `libskarnet.a` 的 `lib/`。
- `--enable-shared` 默认关闭 ⇒ 配方的 `shared` 选项映射到 `--enable-shared/--disable-shared`。
- `--enable-nsss` 不启用（否则多一条 `nsss` 硬依赖）；`--enable-utmp`、`--enable-libc-includes` 不启用 ⇒ 只装 `utmps/utmpx.h`，不覆盖 sysroot 里的 musl `utmpx.h`。

## 遇到的问题与解决方案

| 现象 | 根因 | 处置 |
|---|---|---|
| `Package type is 'library', but no 'shared' option declared`（依赖图阶段） | conan 2 对 library 型强制要求 `shared` 选项 | 声明 `options={"shared":[True,False]}`、`default_options` False，并真正映射到 `--disable-shared`（不让选项成装饰） |
| `fatal error: 'skalibs/tai.h' file not found`（test_package 编译期） | `utmps/utmps.h` 自身包含 skalibs 头，属公共接口，但默认不传播 | `requires("skalibs/2.15.1.0", transitive_headers=True, transitive_libs=True)`（先误用 `cpp_info.requires=["skalibs::skalibs"]`，那是同包组件机制，已纠正） |
| `undefined symbol: TAIN_now`（消费者链接期） | skalibs 的 `tain_now` 是函数指针变量、惯用 `_g` 宏走 `STAMP`，`TAIN_now` 不存在 | 测试改用 `tain_addsec_g` / `utmps_start_g` |
| `make: jobserver mkfifo: ...: Operation not permitted` | HMDFS 不支持 mkfifo | 与同族一致：`make -j1`，不靠 `-j` 并发 |
| 取包 TLS 不可达 | 设备出口到 `www.skarnet.org` 报 `SSLEOFError`、`curl http=000` | 取 skarnet 自家 GitHub 镜像 tag 归档；两容器**逐文件 sha256 比对**为 94 个共有文件全等（GitHub 仅多 `.gitignore`），故 `url`+`sha256` 同取自该件，官方 release 件哈希在 manifest 的 `alternate_official` 备档 |

## 运行面限制（决定测试形态，非缺陷隐瞒）

四臂探针实测：AF_UNIX **路径** socket 的 `bind` 在 `$HOME`、`$HOME` 子目录、cwd 全部 `errno=1 Operation not permitted`，`/dev/shm` 为 `errno=13`，抽象命名空间与 TCP loopback 可用；`/run`、`/var` 不存在且 `mkdir /run` 被拒 ⇒ **daemon 无法在本机监听**，端到端 round-trip 不可测。但 socket 路径本身可运行期改向（`utmps_start()` 第二参、`utmps-write -U/-W`），只有 `UTMPX_FILE=/run/utmps/utmp` 是编译期常量，`utmpxname()` 实测返回 -1。

## 源码修改

无补丁：`patches_applied: []`（配方仍按门禁显式调用 `apply_conandata_patches`/`export_conandata_patches`）。

## 依赖版本

- `skalibs/2.15.1.0`（唯一硬依赖；其 `lib/skalibs/sysdeps` 与 `libskarnet.a` 均取自已发布二进制 `4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`）。
- `nsss/0.2.1.3` 不启用（`--enable-nsss` 默认关）。

## 验证结果

- 上游静态测试数 **0**（已按四种上游形态自数）：顶层 `Makefile:130` 是 `tests: $(TEST_BINS)`、`Makefile:138` 是 `check: tests` + `for i in $(TEST_BINS) ; do ./tools/run-test.sh $$i || exit 1 ; done`；而本包的 `package/targets.mak` 只定义 `BIN_TARGETS`（3 个程序）/`LIBEXEC_TARGETS`（空）/`LIB_DEFS`，**根本不定义 `TEST_BINS`** ⇒ 变量为空、`check` 的循环零次迭代；`src/tests/` 目录在发布件里不存在（`tools/run-test.sh` 需要 `src/tests/<prog>.expected` 或 `.baseline`，缺即 `fatal: missing baseline` + `exit 100`）；`test*`/`*test*` 源文件仅 `tools/run-test.sh` 一个驱动脚本本身；无 `res/` 语料目录、无 `*RUNTEST*`；`examples/` 是 openrc/s6/s6-rc 的服务监管配置样例（18 个文件、0 个 `.c`），不是测试代码。⇒ `N_static=0` 是真实零。配方 `build()` 中仍**真实执行** `make -j1 check`（不跳过上游入口），其输出即该结论的凭据；不拿自写消费者用例冒充上游全量。
  - `build()` 中真实执行上游入口的凭据（`reports/conan-create.log`）：`utmps/0.1.3.4@ohpcd/stable: RUN: make -j1 check` 之后**无任何用例输出**、紧接 `RUN: make -j1 install` ⇒ `check` 以 0 个用例成功返回（`$(TEST_BINS)` 未定义），非跳过。
- W3 真机 `conan create` 通过：`utmps/0.1.3.4@ohpcd/stable` 包 `528aee6c4a4effc58a7d58a9b14645ded6276e30`（rrev `5badd7ec4d47312276a6759759a65892`），打包 3 个程序 + `libutmps.a` + 4 个头。
- 消费者测试（test_package，另列）：**5 条断言全部通过**——`UTMPS_UT_LINESIZE=32`、`UTMPS_UT_HOSTSIZE=256`、`struct utmpx` 字段往返、`utmps_start` 无 daemon 时干净失败（实测 `rc=0 errno=2`）、`utmps-write -h` 用法含 `-U utmpd-socket` 与 `-W wtmpd-socket`（实测 `rc=100`，文本命中）；`utmpxname()` 实测 `rc=-1` 仅记录不断言。
- 凭据：`~/tmp/uc2/hw-6/utmps-create-1.log`（全绿）、探针 `~/tmp/uc2/hw-6/utmps-probe2.sh`。
---

**编译结束**: 2026-09-28 01:01
**最终状态**: built
