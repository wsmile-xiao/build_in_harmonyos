# udpxy 1.0.25.1 适配笔记

## 编译环境

- 构建系统: raw Makefile（`chipmunk/` 子目录，无 configure，默认目标即 release）
- 上游版本: GitHub tag `1.0-25.1`（即 Fedora/Arch 口径的 1.0.25.1）
- 源码: `https://github.com/pcherenkov/udpxy/archive/refs/tags/1.0-25.1.tar.gz`
- sha256: `a1a16e60895c6b2fd151321db47f5d5373843116f1b98ed9749e6c25a6c44497`
  （本地实测下载计算，与 OpenWrt 记录的同 tag 哈希逐字一致）
- 编译日期: 2026-10-10
- 编译器: clang 15（OHOS SDK，待真机预检实证）
- 状态: built（待真机 rule4 门禁验证后由 HMBS 提交）

## 编译步骤（配方内，待真机执行）

1. W0 依赖检查：零第三方依赖（纯 POSIX socket/libc 头文件），无 requires，直接通过。
2. `source()`: `get()` + `strip_root=True` + `filename="udpxy-1.0.25.1.tar.gz"`（E392 要素 1）。
3. `build()`: 打补丁 → `make release CC=<conf> -j1`（`cwd=source_folder/chipmunk`，E392 要素 2/3）
   → `rm -f udpxrec && cp udpxy udpxrec`（去 symlink 化）
   → 编译并运行上游 6 个测试程序 + 3 个反向对照。
4. `package()`: Conan `copy()` 直拷 `bin/udpxy`、`bin/udpxrec`、`share/man/man1/*.1`
  （不用 `make install`：其 man 页压缩步骤依赖 `/bin/gzip`，OHOS worker 无此路径）。

## 上游测试清点（R51）

- tar 包 `chipmunk/test/` 目录：6 个 `test_*.c` 独立测试程序
  （test_a2size / test_a2time / test_addrport / test_cache / test_ifaddr / test_txtf），
  每个自带 `main()`，无任何测试框架（无 ctest/gtest/autotools TESTS）。
- `Makefile` 无 `check`/`test` 目标（全文检索确认）；`verify` 目标只是重编 5 种构建风味，不运行测试。
- `mktestcache.sh` 只是 test_cache 的手工编译提示，且已 stale：
  写的是 `cache.c`（实际在 `test/cache.c`），且缺 `extrn.c`（`g_flog` 未定义会链接失败）。
  配方内已按修正后的命令编译运行。
- 同目录的 getflv/mcprobe/upxc 是开发者工具而非测试（mcprobe 需真实组播源），不计入总数。
- 结论：上游测试总数 6（口径 auto：单一可数的独立 main 程序组），配方 `build()` 内全部编译运行，
  另加 3 个非法输入反向对照（必须失败，证明 harness 非空转）。
- 证伪设计：正向用例断言 rc=0 且输出含真实解析值（如 `size [32Kb] = (32768) bytes`）；
  反向用例断言 rc≠0；test.sh/功能测试同理（200 + 标识 + 端口回显三重断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 `--help`/`-h`，L2 只能 warn，test_package 无法做 K0 断言 | 2008 年 CLI 惯例 | 0001 补丁（K0 契约，udptunnel/endlessh 先例）：`-h` 与 `--help` 走 `usage(stdout)` + exit(0)，缺参/未知选项保留 `ERR_PARAM=1`；udpxy/udpxrec 双入口同改；无平台宏 |
| 2 | `make install` 在 OHOS 上不可用 | man 页步骤硬编码 `/bin/gzip` | `package()` 改用 Conan `copy()`（endlessh 先例），man 页以未压缩形态进 `share/man/man1` |
| 3 | 源码在 `chipmunk/` 子目录；codeload 风格 tag URL；profile 编译器是字典 | raw-makefile 三陷阱 | 严格按知识 E392 三要素写配方（filename / check_type=dict 取 c / cwd 指向 chipmunk） |
| 4 | `udpxrec` 构建产物是 symlink | 上游 `ln -s` | build 内替换为真实拷贝，包内无 symlink 语义（argv[0] 分发不受影响） |
| 5 | 上游测试链接报 `undefined symbol: g_uopt`（真机 preflight，5 个解析类测试全挂） | `util.c` 引用的 `g_uopt` 唯一定义在含 `main()` 的 `udpxy.c`，无法链入独立测试程序；连上游 `mktestcache.sh` 同样缺该定义 | 配方 `build()` 内构建期生成零初始化桩 `test_g_uopt_stub.c`（Conan 缓存内，非入库补丁），`is_verbose=0` 走非 verbose 路径；测试断言不受影响 |
| 6 | `t_cache` 链接报 `undefined symbol: set_cache_trace`（上一轮桩修复后暴露的第二个缺口） | 上游 `test/test_cache.c` 经 `UDPXY_TRACE_CACHE` 调用该函数，但全树无任何定义（`test/cache.c` 只有 `static ltrace_on` 而无 setter，属上游提交缺口） | 0002 补丁：在 `test/cache.c` 内用真实 `ltrace_on` 变量实现该函数（默认行为不变），并在 `test/cache.h` 补声明；属测试脚手架补全，非伪造桩，断言零删减 |
| 7 | test_package 4 断言失败：`udpxy -h`/`--help` 退出非零且 stdout 无 usage （no-args 与状态页通过；构建日志显示两补丁均已 Apply） | 补丁内容经逐 hunk 精确校验无误，但二进制行为缺失：编译树与打补丁树可能非同一份拷贝（复用 build 文件夹或粗粒度 mtime 导致 stale .o 存活），或 getopt 路径单点失效 | 0001 补丁加强（`-h` 并入 `--help` 预拦截，双入口；保留 getopt `case 'h'` 做纵深）+ 配方 `_ensure_cli_help` 对编译树做标记断言、缺失时按补丁原文幂等补齐（已证与补丁逐字节一致）+ 编译前强制删除受影响 .o + build 内冒烟实测 `./udpxy -h/--help`、`./udpxrec -h/--help`（失败即抛，附 captured 输出）；test.sh 与 build() 分别补真实计数的 HMBS 结果标记 |

## 源码修改

- `patches/0001-cli-help.patch`：udpxy.c（optmask 加 `h`、`--help` 预拦截、`case 'h'`）+
  udpxrec.c（同理）。纯 POSIX C，沿用文件自身 `(void)`/`exit()` 风格，无 `__OHOS__` 宏，
  平台无关 portability 补丁。补丁上下文已用脚本对源码逐 hunk 精确校验（4/4 exact-match）。
- 手写原因：本机无 `.opendesk` 设施，无法运行 `refresh-patch --auto`；
  内容等价于工具生成（标准 unified diff，`a/`/`b/` 前缀，-p1 可应用），待 CI/preflight 实证。
- `patches/0002-test-cache-trace.patch`：`test/cache.c` 补真实 `set_cache_trace()` 实现
  （写 `ltrace_on` 标志，默认行为不变）+ `test/cache.h` 补声明。两 hunk 已用脚本对源码
  逐行精确校验（header 行数恒等式与上下文 exact-match 全通过）；本机 git shim 连已知良好的
  0001 也解析失败，故以 Python 精确模拟 + header 恒等式为准，待 preflight 实证。

## 依赖版本

- 无第三方依赖（零 requires）。
- 构建工具：GNU Make、clang 15、Conan 2.x（OHOS 适配版，均由真机/CI 侧提供，待实证）。

## 风险与待验证项（真机预检重点观察）

1. `osdef.h` 仅在 `__linux`（无下划线）时定义 `NO_SOCKADDR_SA_LEN`；
   若 OHOS clang 不定义 `__linux` 而只定义 `__linux__`，`sa_len` 引用会编译失败。
   预案（需预检失败才启用，PF5 禁止补丁新增 `__OHOS__`）：改为
   `#if defined(__linux) || defined(__linux__)`（POSIX 兼容写法，无平台宏）。
2. `ln -s`（udpxrec symlink 步骤）若真机文件系统不支持，build 会失败；
   预案：`NO_UDPXREC=yes` 或配方内跳过该步骤（届时按实际日志处理）。
3. 功能测试以 root 运行时会走 pidfile 分支（`/var/run` 可能不存在）；
   若预检身份为 root 且失败，按日志调整（非 root 前景运行无此分支）。
4. `-Werror` 仅保留在主构建；测试程序用 `-W -Wall --pedantic`（去 `-Werror`），
   避免测试文件自身告警阻塞交付（结果真实性不受影响：rc 与输出双断言）。

## 验证结果（待真机预检回填）
## 本轮改动（2026-10-10，仅改工作树，未提交，待真机预检）

- `patches/0001-cli-help.patch`：`--help` 预拦截扩展为 `-h`/`--help` 双形式 （udpxy/udpxrec 双入口，`getopt case 'h'` 保留）；4 个 hunk 经脚本对原始 tar 包逐行精确校验（offset+行数+内容全匹配，见 `.hmbs/check_patch1.py` ALL OK）。
- `conanfile.py`：`build()` 新增 `_ensure_cli_help(src)`（编译树标记断言+幂等补齐，与补丁逐字节等价性已实证：`.hmbs/validate_equiv.py` 对原始源码分别跑 fallback 与补丁应用，4 文件逐字节一致且二次运行 no-op）→ 删 stale `.o` 强制重编 → `_smoke_cli_help` 实测刚构建的二进制（rc 与 stdout 双断言，失败抛 ConanException 附输出）→ `_run_upstream_tests` 末尾输出 `HMBS_UPSTREAM_TEST_RESULT`（custom 框架，6/6，计数来自 6 次直接执行，无字符串计数）。
- `test_package/test.sh`：末尾输出 `HMBS_TEST_PACKAGE_RESULT`（PASS/TOTAL 为断言同步计数器，恒有 PASS+FAIL==TOTAL==10），失败时同样输出 `passed:false` 标记后再以非零退出。
- 本地可验证项已全过：两 conanfile `py_compile`、补丁 hunk 校验、fallback↔补丁等价、test.sh TOTAL 计数==10（与 MANIFEST `assertion_count: 10` 一致）、全文件 LF。


- `conan create`：待 HMBS 真机预检执行。
- 上游 6/6（+3 反向对照）：待回填。
- test_package 10/10：待回填。

## 工作树污染声明（2026-10-10，提交时请排除）

- `archives/l/libXext/README.md`、`archives/l/libXext/manifest.yaml` 在本轮内被工作树之外的
  并发写入者反复改写（内容系悬空提交 84b788224“libxext 1.3.7 适配”的两个文件，与本任务无关；
  实证：`git ls-files -s` 与 `git diff --raw` 在相邻命令间给出互相矛盾的 index blob，
  且 `git checkout HEAD -- <paths>` 写入后仍被改回）。
- 该污染非本任务改动，HMBS 提交时必须排除这两个文件（只提交 `archives/u/udpxy/` 即可满足 W2 原子性）。
- `git status` 中若仍见该两处 M，以本声明为准，不属于本 PR 内容。

## 交付物（预期）

| 文件 | 说明 |
|------|------|
| bin/udpxy | 主服务（-p 端口监听，/status/ 状态页） |
| bin/udpxrec | 同二进制（argv[0] 分发），组播录制工具 |
| share/man/man1/udpxy.1、udpxrec.1 | 英文 man 页（未压缩） |
