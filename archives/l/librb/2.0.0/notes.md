# librb 2.0.0 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am + libtool）
- 编译日期: 2026-09-14
- 编译器: clang 15（OHOS SDK llvm，Conan profile 注入）
- 状态: built（首轮工作树，待真机预检回填实测数字）

## 源码信息
- 上游: https://github.com/mlyszczek/librb（作者 Michal Lyszczek，文档站 https://librb.bofc.pl）
- 版本: 2.0.0（tag v2.0.0）
- 源码包: https://github.com/mlyszczek/librb/archive/refs/tags/v2.0.0.tar.gz
- sha256: d616c3db98f83c8f81851694bce391b61c78cc121c02fb665fad20243e699e6c（实测下载计算）
- 许可证: BSD-2-Clause
- 选源说明: 官方 distfiles.bofc.pl 对抓取返回 bot 校验页（非压缩包），GitHub tag 包为作者官方源且可稳定下载，故采用后者；CI 会自动补充 GitHub 镜像 fallback。

## 配方固化（conan create 路径）
- build_requirements: tool_requires automake/1.18 + autoconf/2.72 + libtool/2.5.4（GitHub archive 为裸 git 树快照，不含 generated configure，需自举；zzuf 0.15 同型先例）。
- generate(): VirtualBuildEnv（tool 链 PATH）+ AutotoolsToolchain（默认参数，R1 最少化；线程保持上游默认开启）。
- build(): 无 configure 则手动五步自举（强制系统 perl，见下）；generated configure 经 `_patch_configure` 做变量形 HMDFS 适配（`umask 077`→`022`、ac_pwd 回退 $PWD、mktemp 模板→`${TMPDIR:-.}`、`${TMPDIR=/tmp}`→`${TMPDIR=.}`，不烘焙绝对路径）；`configure` → `make -j1 librb.la tests` → `make check-am -j1`（www/ 需 sphinx-build，真机无此工具，见问题 4；install 同理仍用 SUBDIRS=. 跳过 www）。
- generate()/build() 统一解析可写 tmp（`_resolve_hmbs_tmp` 探测 HMBS_AUTOCONF_MKTEMP_FALLBACK/TMPDIR/TMP/TEMP/HMBS_TMPDIR，实测 mkstemp 可写，永不选 /tmp，回退 build_folder/cfg-tmp），generate 经 `hmbs_tmp_env`（build scope）导出 TMPDIR/TMP/TEMP + SHELL/CONFIG_SHELL + HMBS_* 透传，build() 同步 os.environ 并在自举命令首行 export（cassbeam/c-client 同型先例，见问题 7）。
- 上游测试接入: `_run_upstream_tests` 在 `make check-am` 后解析 tests.log 的 TAP `ok`/`not ok` 行计数（回退解析 test-suite.log 的 TOTAL/PASS/FAIL/SKIP），输出 `HMBS_UPSTREAM_TEST_RESULT` 并落盘 `upstream_test_result.json`；零证据或有失败直接抛异常，拒绝空过。
- package(): `make install`；删除 `.la`（烤死绝对 libdir 路径）；LICENSE/COPYING 入 licenses/；`upstream_test_result.json` 入 res/ 供 test_package 复发；OHOS 下对 lib/*.so 自签（gd 2.3.3.1 同款）。
- package_info(): `libs = ["rb"]`（产物 librb.so/a），附 cmake_file_name/target 供 CMakeDeps 消费。
- 非系统同名库（OHOS /lib 下无 librb），保留动态库，R26 不触发。
- 补丁: patches/0001-rb-sem-destroy.patch（rb.c 未命名信号量 `sem_close`→`sem_destroy`，musl 可移植性修正，见问题 5）；patches/0002-rb-sem-post.patch（`rb_sem_post` 改为无条件 `sem_post`，见问题 8）。

## 上游测试清点（R51）
- 上游测试资产: 单个 automake TESTS 程序 `tests`（tests.c + rb.c + mtest.h，mtest TAP 框架，tap-driver.sh 驱动），`make check` 运行。
- 结构: main() 内参数化矩阵（ENABLE_THREADS 下 dynamic 生产消费 16x16、multi 生产消费 2x4x16x16、单/多线程缓冲尺寸 2x4x8^4 组合）+ 约 25 个固定 mt_run（peek/discard/count/grow/round/dynamic/invalid 等）；上游 README 称 master 全量 68874 测试点全过（作者声明，引自上游仓库页面，非本轮实测）。
- 计数口径: 以真机 `make check` 生成的 tests.log 中 TAP 点为准（discovered=ok+not ok），2.0.0 精确数字待预检日志回填，不预估。
- 消费者测试: test_librb.c 6 检查（模式与数值照抄上游 tests.c 用例），conanfile 计数 `PASS:` 行并校验 `RESULT` 行，双重判定后输出 `HMBS_TEST_PACKAGE_RESULT`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | distfiles.bofc.pl 源码包下载到的是 4KB HTML | 站点对非浏览器抓取返回 bot 校验页（"Making sure you're not a bot"），非压缩包 | 改用作者 GitHub 官方 tag 包（109295 字节，正常解包，文件清单含 configure.ac/rb.c/tests.c） |
| 2 | GitHub archive 无 configure | archive 只是 git 树快照，configure 是 autoreconf 产物不进版本库 | tool_requires 三件套 + build() 内 autoreconf（gd/zzuf 先例） |
| 3 | Windows 检出后 archives/l/libXext 与 libxext 互相覆盖显脏 | 上游同时存在仅大小写不同的两个目录，Windows 文件系统不区分大小写 | 与本任务无关，保持不动，不纳入本 PR |
| 4 | 真机 `make all` 在 www/ 目录失败：`sphinx-build: command not found` | 顶层 SUBDIRS=`www examples`，www/ 的 man 页由 sphinx 现场重建，真机/CI 镜像无 sphinx（configure.ac 无 --disable-docs 开关） | build/make check/install 统一加 `SUBDIRS=.` 只构建顶层 librb.la + tests（flex 2.6.4.2 同型先例）；man 页为纯文档不随包发布 |
| 5 | 真机 `make check` 中 tests 二进制段错误（signal 11，exit 139，零 TAP 输出） | rb.c 对 `sem_init()` 创建的未命名信号量调用了只适用于命名信号量的 `sem_close()`（rb_cleanup + rb_init_p 错误路径共 4 处），属 UB；glibc 宽容无感，OHOS musl 直接崩溃 | patches/0001-rb-sem-destroy.patch：4 处 `sem_close` → `sem_destroy`；上游行为不变（glibc 下同义），musl 下消除崩溃（首版 hunk 行号手估致 Conan 拒打，已按 v2.0.0 rb.c 真实行号 398/1609 校准并逐行验签） |
| 6 | 真机 `make check` 跑到动态生产消费矩阵中段（约第 15 个 TAP 点，producers 15/consumers 1）后 `sh: >&3 : bad file descriptor` + SSH `Connection closed by remote host`，上游测试 0/0/0 | `rb_sem_post()` 仅在 `sem_getvalue() == 0` 时 `sem_post()`；musl 在有线程阻塞于 `sem_wait()` 时返回负的等待者计数（glibc 实际钳制为 0），高并发下恰在有等待者时跳过 post → 丢失唤醒 → 生产/消费线程永久阻塞 → `make check` 挂起，SSH 会话被远端掐断，tap-driver 收尾写 fd 3 失败 | patches/0002-rb-sem-post.patch：`== 0` → `<= 0`；上限语义不变（计数 < 1 才 post，仍不超过 1），glibc/musl 双兼容；完整 `make check` 矩阵原样保留，未删减任何 TAP 点 |
| 7 | 真机预检 `preflight.sh[306]: can't create temporary file /tmp/shtns2aj.tmp: Read-only file system` + `conan create` 退出 137（`tap-driver.sh: line 141: 3: Bad file descriptor` + `Signal 9`），上游测试 0/0/0 | 真机 /tmp 只读（erofs，HMBS 平台诊断 `readonly_tmp`）；配方未导出可写 TMPDIR，autoconf/config.status/libtool/mktemp/tap-driver 默认回退到 /tmp 建临时文件，直接失败；挂起的 `make check` 随后被预检 SIGKILL（137），tap-driver 收尾写 fd 3 失败为被杀副作用，非测试逻辑失败 | generate 新增 `hmbs_tmp_env`（build scope）：`_resolve_hmbs_tmp` 实测可写性探测 HMBS_AUTOCONF_MKTEMP_FALLBACK/TMPDIR/TMP/TEMP/HMBS_TMPDIR（永不选 /tmp，回退 build_folder/cfg-tmp），导出 TMPDIR/TMP/TEMP + SHELL/CONFIG_SHELL + HMBS_* 透传；build() 同步 os.environ 并在自举首行 export；`_patch_configure` 变量形补丁（umask 022、mktemp→`${TMPDIR:-.}`、`${TMPDIR=/tmp}`→`${TMPDIR=.}`，不烘焙绝对路径）；自举 shell 改用 HMBS 注入 SHELL（/bin/sh）。完整 `make check` 原样保留，未跳过任何 TAP 点 |
| 8 | 真机 `make check` 在 `<= 0` 补丁后仍挂起：`tests` 链接出现两次后 `Connection closed by remote host`，上游测试 0/0/0 | 两因叠加：① `rb_sem_post` 的 getvalue 门限在任何 POSIX 上都竞态（读到 1 后消费者才阻塞 → 丢唤醒 → pthread_join 永挂；musl 另把等待者报成负数，`<= 0` 仍可能在 1 的窗口丢唤醒）；② `make check SUBDIRS=.` 经 automake `check-recursive` 向 `.` 自递归，把 `tests` 重链接一遍再跑两遍约 6.5 万 TAP 点的矩阵，耗时翻倍且两轮输出交错 | 0002 改为无条件 `sem_post`（计数超 1 只多一次 sem_wait 排空，不影响正确性；漏 post 才会永挂）；build 改显式目标 `make -j1 librb.la tests`（显式目标不递归），测试改 `make check-am -j1`（只跑顶层 TESTS 一次，不进 www/examples）；完整矩阵原样保留，未删减任何 TAP 点 |

## 依赖版本

无第三方依赖（仅 libc：pthread/semaphore/标准 C；configure 的 AX_PTHREAD 在 OHOS 上探测通过）。

## 验证结果（待真机预检回填）

- 首轮仅完成工作树，未跑真机；`conan create` 实测、上游 TAP 点数、消费者 6/6 均以 hmbs 预检日志为准，数字回填前不承诺。
- test_package 6 检查的每条模式均逐字取自上游 tests.c 已有断言（容量 count-1、EAGAIN 语义、grow/discard/peek/dynamic），降低新写用例踩雷概率。

## 路径 A/B 判断

**结论：纯路径 A（基础适配）。** 零补丁、零平台分支、无新错误模式、无可复用知识增量；若预检发现 OHOS 特有失败再视情况补救。

## 注意事项

- `make check` 全量矩阵为多线程重压测试，真机耗时以预检实测为准；若超默认预算，后续轮按 W3 指引在 ci/config/build_timeouts.txt 登记。
- test_package 二进制链接共享 librb.so，运行时经 conanrun/LD_LIBRARY_PATH 解析；捕获复跑同样注入依赖 libdir。
