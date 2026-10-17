# mpsolve 3.2.3 adaptation notes (2026-09-20)

- 任务: 8982; 平台: mpsolve/3.2.3 (开源鸿蒙PC专项积分赛); 分支 feat/mpsolve-3.2.3
- 上游: https://numpi.dm.unipi.it/wp-content/uploads/2025/08/mpsolve-3.2.3.tar.bz2
  sha256=1f2e239c698c783b63a5e6903e76316c0335a01d71c466a8551e8a3f790b3971 (3.3 MB)
  **3.2.3 在 GitHub 上没有 tag**（robol/MPSolve 最新 tag 停在 3.2.1，master HEAD 自报
  AC_INIT 3.2.3），官方发布物是比萨数值分析组项目页的 make dist tarball；Debian 的
  mpsolve_3.2.3.orig.tar.bz2 即取自该 tarball。
- 定位: application（MPSolve CLI + libmps）；commands.json 包级（R38）。
- **本版最大变化：不再需要 autoreconf 引导。** make dist tarball 自带生成的
  configure / Makefile.in / aclocal.m4，于是 3.2.1 为引导付出的整套代价全部消失：
  没有 autoconf/automake/libtool 的 tool_requires、没有 ACLOCAL_PATH 注入 pkg.m4、
  更没有「OHOS 禁 shebang exec 所以要把 autotools 脚本包成 ELF 启动器」那套绕行。
  配方直接从 `sh ./configure` 起跑。
- **补丁 0001 已成死补丁，但"旧补丁失效"推不出"本版不需要补丁"。** 3.2.1 的
  `0001-mps-mpc-register-keyword.patch`（C++17 移除 register 关键字，mps/mpc.h 里
  `register signed long int`）在 3.2.3 里上游自己修掉了，照搬会 apply 失败，故不再携带；
  但 tarball 自带的 config.guess / config.sub 是 **autoconf 2.71 一代**的快照
  （config.sub `timestamp='2022-01-03'`），不认识鸿蒙三元组，仍必须补两条 platform 补丁。
- **★★ OHOS 三元组：补 config.guess 还不够，config.sub 要补两处（CI #53927 的根因）**
  - 失败原文（build #53927 / worker CI-031）：
    `checking host system type... Invalid configuration 'aarch64-unknown-linux-ohos':
    OS 'ohos' not recognized` ⇒ `configure: error: /bin/sh ./config.sub ... failed`。
  - config.sub 对同一输入有**两道**关口：先 `case $os in`（OS 类型列表，缺 `ohos*` 报
    `OS 'ohos' not recognized`），再 `case $kernel-$os in`（内核-OS 校验表，缺
    `linux-ohos*` 报 `Kernel 'linux' not known to work with OS 'ohos'`）。
    **只过第一道会在第二道再死一次**，两处必须同补。
  - 本 tarball 的 config.sub 里 `maybe_os` 分支已含 `linux-*`，故 4 段输入
    `aarch64-unknown-linux-ohos` 走 `basic_machine=$field1-$field2 / basic_os=$field3-$field4`
    直取路径 ⇒ `kernel=linux, os=ohos` ⇒ 正好撞上这两道校验。
  - **`scripts/patch-autotools-ohos.pl` 在这个 config.sub 上会静默漏掉内核-OS 那处**：
    它先插入 `basic_os=linux-ohos`（§2.1），紧接着 §2.3 的守卫却是**整文件**子串
    `unless ($sc =~ /linux-ohos/)` —— 自己刚写进去的字符串把守卫顶成真，于是 skip；
    而它的自检 `$sc =~ /linux-ohos/` 用同一个整文件匹配，于是照样打印 `Score: 4/5 ✅`。
    实测：脚本跑完 `sh config.sub aarch64-unknown-linux-ohos` 仍报
    `Kernel 'linux' not known to work with OS 'ohos'` —— **自证成功的假象**。
    ⇒ 判据只能是"把补丁后的 config.sub 真跑一遍"，不能看脚本自报的 ✅。
  - 本版 `patches/0002-config.sub-ohos.patch` = 该脚本的三处意图（`ohos-linux` 映射 +
    OS 列表 `ohos*` + 内核列表 `linux-ohos*`），把被漏掉的第三处补齐；两处修好后
    `aarch64-unknown-linux-ohos` 与 `aarch64-ohos-linux` 两种写法都放行。
- **★ 不再用 `--build/--host` 绕（P-AUTOTOOLS-001 / E007 铁律）**：旧配方传的是
  `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`，等于把 configure
  骗进"交叉编译"分支（build ≠ host）：`AC_RUN_IFELSE` 一类运行时探测被整体跳过、
  config.h 退回保守默认值；而且它并不能省掉补丁——config.sub 照样要认 `linux-ohos`。
  正解是补 config.guess / config.sub，让 configure 自己猜出 `aarch64-unknown-linux-ohos`
  （build == host，真·原生构建），配方里那对三元组整个删掉。
- **宿主侧离线复现（x86_64 / WSL 实测）**：把 `uname` 换成返回 `-s HarmonyOS / -m aarch64`
  的桩 ⇒ 补丁后的 config.guess 输出 `aarch64-unknown-linux-ohos`；再用**不带 --build/--host**
  的同一组参数跑真实 `configure` ⇒ `checking build system type... aarch64-unknown-linux-ohos`
  与 `checking host system type... aarch64-unknown-linux-ohos`（host == build 成立），
  libtool `LT_INIT` 一并通过并生成 config.status；随后 `make rc=0`、
  `make -C src check rc=0`（TOTAL:16 / PASS:16 / FAIL:0 / SKIP:0）。
  这条链路在 CI 之外已端到端跑通，CI 只需验 OHOS 侧。
- 依赖链关键: **gmp/6.3.0.1（CXX 构建，--enable-cxx）**——libmps 的 formal 模块
  （formal-monomial.cpp/formal-polynomial.cpp）无条件编译且使用 GMP C++ 绑定
  （mpq_class），基础版 gmp/6.3.0 不含 libgmpxx/gmpxx.h。check/0.15.2 经
  PKG_CHECK_MODULES([CHECK], [check >= 0.9.4]) 驱动上游 make check。
- 构建要点（E386/§12.49 + E114 家族，全部设备实证）:
  ① 全部 configure/make 经 `env -u CONFIG_SHELL SHELL=/bin/sh` 路由（hnp bash getcwd 缺陷）；
  ② 生成的 configure 中 `(umask 077 && mktemp -d "./confXXXXXX")` / `(umask 077 && mkdir "$tmp")`
     在 HMDFS 上造出连属主都不可写的临时目录（目录被强制 setgid ⇒ drwx--S---），
     build() 里改写生成物摘掉 umask 077（E114；3.2.1 走的是 sed 生成物 077→022，同源）；
  ③ GMP_CFLAGS/GMP_LIBS 内联注入（configure.ac 原生支持；GMP_LIBS 含 -lgmpxx）；
  ④ make -j1（E074：HMDFS jobserver fifo EPERM）；
  ⑤ make check 的 check 框架 IPC 临时文件按 TEMP→P_tmpdir(/tmp)→TMPDIR→"." 取路径，
     /tmp 只读 → TEMP 重定向到可写目录（picotcp 同款）；测试二进制运行时
     LD_LIBRARY_PATH 补 libgmpxx/libcheck 路径。
- **测试账本（四维）**:
  - 上游静态注册: 16 个 check(3) 测试程序（src/tests/Makefile.am 的 `check_PROGRAMS`
    = `TESTS`：check_convex / check_context / check_mpc / check_matrix / check_dpe /
    check_formal / check_multithread / check_cluster / check_chebyshev / check_parser /
    check_utils / check_monomial_poly / check_list / check_secsolve / check_unisolve /
    check_version）；用例级 START_TEST 声明 90 处（分布于其中 15 个程序，check_multithread.c 为 0），
    其中 88 处经 tcase_add_test 注册进 Suite。
  - 实际执行: `make -C src check` → automake 汇总 `# TOTAL: 16 / # PASS: 16 /
    # FAIL: 0 / # SKIP: 0 / # ERROR: 0 / # XPASS: 0`（宿主 x86_64 复跑实测，OHOS 侧同口径）。
  - 通过率口径: 程序级 16/16 = 100%；零 SKIP 已由配方硬校验钉死。
  - 消费者测试: test_package/smoke_mpsolve.sh —— CLI 视角 3 组断言（见 MANIFEST.yml）。
- 未执行子项: examples（--disable-examples，依赖额外语言绑定）、GTK/Qt UI 与
  graphical-debugger（--disable-*，OHOS 无桌面栈）——均为非测试入口的组件。
- result.json 由 ohc-run.py result 按最终 HEAD 生成。
---

**编译结束**: 2026-09-20
**最终状态**: built
