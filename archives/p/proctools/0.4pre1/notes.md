# proctools 0.4pre1 适配笔记

## 编译环境
- 构建系统: makefile（原 BSD make/bsd.prog.mk 重写为 GNU make）
- 编译日期: 2026-09-04
- 编译器: clang 15（/data/service/hnp/bin/clang，musl libc，aarch64-linux-ohos）
- 状态: published

## 软件背景
- 上游：https://downloads.sourceforge.net/project/proctools/proctools/0.4pre1/proctools-0.4pre1.tar.gz
- sha256: 4553b9c6eda959b12913bc39b6e048a8a66dad18f888f983697fece155ec5538
- 许可：BSD-3-Clause + BSD-4-Clause-UC（tarball 内 LICENSE）
- OpenBSD 原生 + Darwin 移植版（2003-12-07 最后版本），pgrep/pkill/pfind 三工具 + libproctools
- 纯 C、零第三方依赖（W0 天然满足，conan 无 requires）

## 编译步骤
1. 解压 tarball，工作副本 $HOME/tmp/builds/proctools-0.4pre1.work
2. 平台移植（见"源码修改"）
3. `make CC=/data/service/hnp/bin/clang`（GNU make，根 Makefile 编排 lib+3 工具）
4. `make install DESTDIR=... PREFIX=...`（bin/man1/doc）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | regexec 第 5 参 eflags 传 NULL 编译报错（-Wint-conversion） | BSD 时代 NULL==0 的遗留写法，musl/clang15 视为硬错误 | 7 处 `regexec(..., NULL, NULL)` 改为 `(..., NULL, 0)`（proctools.c×4、pfind.c×3） |
| 2 | REG_NOSPEC 未定义 | OpenBSD regex 扩展（字面量编译模式），musl 无 | pfind.c 增加 regcomp_escape() 转义 ERE 元字符等价模拟（xflag 字面量子串匹配语义不变），BSD 路径原样保留 |
| 3 | 启动即段错误 | musl 的 constructor 不传参数（glibc 才传 argc/argv/envp），bsd_compat.c 里读 argv[0] 解引用寄存器垃圾值 | 去掉 constructor，改为三个前端 main() 首行 `__progname = cmdpart(argv[0])` |
| 4 | pgrep 枚举结果为空 | procfs_read_stat 从 state token（字母）开始 strtoll 解析失败，所有进程被跳过 | 跳过 state（strcspn 到空格），从 token 2 (ppid) 起数值解析 |
| 5 | pfind -f 回读 dump 报 "could not read entire dumpfile" | 上游 DUMPOUT/UNDUMP 宏对 32 位 int 移位最多 56 位（UB），-O2 下 clang 任意发挥产生垃圾值（-O0 碰巧正确） | 宏内改用 `(u_int64_t)` 显式 64 位转换后再移位，dump 文件格式（8 字节大端字段）不变，与旧 dump 兼容 |
| 6 | pfind -result/-wait 报 "could not attach: Permission denied" | 本沙箱环境限制 ptrace attach（gdb 同样被拒），非代码问题 | 属环境限制，工具如实报错；ptrace 代码路径本身无需修改（PT_ATTACH/PT_CONTINUE/PT_DETACH musl 原生可用） |
| 7 | 本机 grep 无 -P、cat 无 -A | OHOS 工具链精简 | 用 python3 脚本做控制字符扫描；用 `sed -n 'l'` 查看转义字符 |

## 源码修改（实质性平台适配，非 stub）

### 后端替换：/proc 替代 kvm/sysctl（R40）
上游用 `<kvm.h>` kvm_openfiles/kvm_getprocs/kvm_getargv + sysctl(KERN_PROCARGS2/KERN_MAXPROC/KERN_ARGMAX/KERN_PROC) + struct kinfo_proc，Linux/musl 上全部不存在。保持 proctools.h 对外 API 面（struct baton/getProcList/getProcArgs/printProcInfo 等）与 pgrep/pkill 前端不变：

1. **proctools.h**：`__linux__` 时自动定义 USE_PROCFS（第三后端，与 USE_KVM/USE_SYSCTL 并列）；提供 OpenBSD 形状的 kinfo_proc shim（kp_proc.p_pid/p_comm[64]/p_wmesg/p_starttime；kp_eproc.e_ppid/e_pgid/e_tdev/e_ucred.cr_gid/e_pcred.p_ruid/p_svuid）；`#define p_starttime p_starttime`（对象宏自引用）使 getProcList 的 `#elif defined(p_starttime)` 分支在 Linux 生效（-n lastonly 可用）；声明 sys_signame/__progname/cmdpart
2. **proctools/procfs.c**（新文件，~300 行）：
   - procfs_read_stat()：解析 /proc/\<pid\>/stat，strrchr(buf,')') 定位 comm（正确处理含空格/括号 comm），token 2/3/5/20 → e_ppid/e_pgid/e_tdev(starttime)，starttime 时钟滴答按 _SC_CLK_TCK 换算 timeval
   - procfs_read_status_ids()：解析 /proc/\<pid\>/status 的 Uid:/Gid: 行（real/effective/saved/fs 四列），p_ruid←real、p_svuid←saved（与上游 -u 匹配 p_svuid 语义一致）、cr_gid←effective（与 OpenBSD e_ucred 语义一致）
   - procfs_get_all_procs()：readdir /proc 枚举数字目录，动态数组倍增，进程中途消失静默跳过（等价 kvm_getprocs 竞态语义）
   - procfs_read_cmdline()：读 /proc/\<pid\>/cmdline，NUL 分隔符转空格 join（与 kvmArgs 语义逐字节一致），内核线程/不可读返回 NULL 回退 p_comm
3. **proctools/bsd_compat.c**（新文件，~200 行）：
   - strvis()：忠实实现 vis(3)（VIS_OCTAL/VIS_CSTYLE/VIS_SP/VIS_TAB/VIS_NL，isgraph 透传、\\n\\r\\b\\a\\v\\f\\t C 风格转义、其余 \\xxx 八进制）
   - sys_signame[NSIG=65]：1-31 标准名、32-34 空（musl 保留）、35-64=RTMIN/RTMIN+n/RTMAX（实测本机 musl SIGRTMIN=35 SIGRTMAX=64）
   - __progname 定义（由前端 main() 赋值）
4. **proctools.c**：getProcList 采集段三分支（kvm/sysctl/procfs）——procfs 分支：argmax=max(sysconf(_SC_ARG_MAX),256KB)、kp=procfs_get_all_procs()、-M corefile 诚实报 EX_UNAVAILABLE（kernel core 是 kvm 特性）；**匹配主循环零改动**（兼容 shim 使 kpi.kp_eproc.* 原样工作）；procArgs/getProcArgs/printProcInfoNative 增加 USE_PROCFS 分支；DUMPOUT/UNDUMP 移位 UB 修复
5. **fmt.c**：fmt_argv 在 USE_PROCFS 下改为 (baton, proctoolslist) 签名，自行读 cmdline 逐参数 fmt_puts+空格（语义同 kvm_getargv 路径），argv[0] basename≠comm 时补 "(comm)"
6. **pfind.c**：仅 sys/sysctl.h、sys/user.h include 守卫 + REG_NOSPEC 模拟 + __progname 初始化；ptrace/表达式树逻辑零改动
7. **构建系统**：根 Makefile 重写为 GNU make（libproctools.a + 3 工具 + install/DESTDIR，CC/CFLAGS 可覆盖）；Makefile.inc 改为 GNU 语法变量（PREFIX/BINDIR/MANDIR=share/man/DOCDIR）；4 个子目录 Makefile 改为委托根 Makefile 的 thin wrapper（保持 `cd pgrep && make` 可用）；man 页 raw 装 man1/ + .so 伴生页装 MANDIR/proctools/（不依赖 soelim，CI 确定性）

## 依赖版本
- 无第三方依赖（W0）
- 工具链：clang 15 + ld.lld + musl（OHOS SDK 26.0.0.18 sysroot）
- 构建工具：GNU make

## 验证结果

本地功能测试（13/13 通过）：
- pgrep：-x 精确匹配、-l 显示名、-f 全命令行匹配、-n 最新进程（starttime 时间戳比较）、-d 分隔符、-P 父进程过滤
- pkill：默认 TERM、-9、-s TERM 信号名解析
- pfind：裸模式、-name/-args/-any、-uid/-ppid/-pgrp 组合、-x/-i、-d 分隔符、-dump/-f 往返、-kill TERM、-id/-details
- 环境限制：pfind -result/-wait 需 ptrace attach，本沙箱禁止（gdb 同样被拒），工具如实报错；test_package 不含此类断言

```bash
$ pgrep -l -x sleep
35326 sleep
$ pgrep -lf sleep          # 完整 argv（fmt_argv→cmdline）
35811 sleep 994
$ pkill -x sleep && ...    # 进程被杀
$ pfind -x -name sleep -kill TERM; kill -0 $S1 || echo OK
OK
$ pfind -x -name sleep -dump d.txt; pfind -f d.txt -name sleep
38537
```

## 交付物
- archives/p/proctools/0.4pre1/conanfile.py、conandata.yml、patches/、test_package/、manifest.yaml、notes.md、reports/test-report.md
- archives/p/proctools/commands.json、README.md、manifest.yaml（软件级 R38）

## 注意事项
- man 页 .so 伴生文件安装于 MANDIR/proctools/（groff 相对路径解析），勿删否则 man 页缺节
- pfind 选项（-d/-f/-i/-x 等）必须在表达式之前（上游设计）
- pgrep -v 语义为上游原样（仅反转 uid/gid 列表匹配，不反转 pattern 匹配）
- 上游 pgrep 按设计不匹配自身进程（getProcList 显式跳过 getpid()）

## 2026-09-07 AI Review 第二轮修复（PR #8276，13:55 结论）
第二轮 `/ai review`（P0=0 P1=0 P2=0，P3×3 + 1 条 Medium 意见）已全部处理：
1. **E545 → E547 重命名**（Medium 意见）：E545 已被 fossa 草稿 E545-draft-5CC4.kv 占用（review 建议 E546 也已被 E546-draft-A58D 占用，实测取 E547）。knowledge/drafts/E545-draft-AA22.{kv,md} → E547-draft-AA22.{kv,md}，内部 id/doc_file 同步。
2. **P3 声明后语句**（0004/0008）：`__progname` 赋值移到 main() 声明区全部结束之后，与 0006（pgrep）写法一致；严格 C89（-std=c89 -pedantic-errors 或 -Werror=declaration-after-statement）不再报错。
3. **P3 test.sh 预清理误杀**：预清理改只杀孤儿 sleep（/proc/<pid>/stat 第 4 字段 ppid==1）；断言 15 后的收尾清理改为按本 shell 子进程域杀（`kill $(pgrep -P $$ -x sleep)`）；pkill 断言本身全局是测试语义（已在注释说明）。
4. **P3 shebang**：`#!/data/service/hnp/bin/bash` → `#!/usr/bin/env bash`（conanfile.py 以 `bash test.sh` 显式调用，shebang 运行时不依赖）。
5. **P3 uid/gid 覆盖**：新增断言 17（`pfind -x -gid <self-gid> -name sleep`，覆盖 procfs status Gid: 解析路径）；断言总数 19。
- 上轮 P2/P3 修复经本轮 review 确认（"均已在当前 diff 中确认修复"）。
- 本地复验：build_and_test.sh L0/L1/L2/L4/L5 全 pass，19/19 断言。

## 2026-09-07 AI Review 第一轮修复（PR #8276，10:49 结论）
PR #8276 `/ai review` 出 2 条意见（P2×1、P3×1），均已修复并本地复验：
1. **P2 — regcomp_escape 转义集缺 `{`/`}`**（0004 补丁）：`-x` 字面量模式含花括号时（如 `a{2}`），生成的 ERE 把 `a{2}` 当区间量词（匹配 "aa"），孤立 `{` 还可能触发 REG_EBRACE。修复：strchr 元字符集补 `"{}"`，转义后正则不含任何 ERE 元字符，与 REG_NOSPEC 语义等价。pgrep/pkill 不受影响（上游 proctools.c:862 对 pgrep 模式本就用纯 REG_EXTENDED，`-x` 语义由 getProcList 全名匹配实现，非 REG_NOSPEC 路径）。
2. **P3 — 子目录 wrapper 默认目标回归**（0003/0005/0007 补丁）：wrapper 以程序名为首目标，裸 `make` 在子目录会转发到顶层不存在的同名目标（新检出报错、已构建后静默不重编）。修复：`all install clean` 置首使 `all` 成为默认目标；程序名目标单独显式映射到顶层真实文件目标（`pfind/pfind` 等），`make pfind` 依旧带依赖增量构建。
3. **审查附带项澄清**：审查表称 0012-0014 补丁"不在本 diff 内"——实为误报（分文件表仅列 12 个文件），PR 实际含全部 26 文件，0012/0013/0014 均在 diff 内，conan create 应用顺序无缺失风险。
- 测试：test.sh 新增断言 16（spawn 名为 `a{2}` 与 `aa` 的进程，`pfind -x 'a{2}'` 必须命中前者且不命中后者，双向判别转义修复）；MANIFEST assertion_count 17→18。

## 框架 bug 记录（skill 脚本只读，未改动）
1. **patch --dry-run 污染 orig 目录**（已提知识草稿 E547-draft-AA22，原误记为 E429）：本机 `patch --dry-run` 对 `--- /dev/null` 新文件补丁会在 orig 目录创建 0 字节文件；后续 refresh-patch 收集阶段 `orig_file.exists()` 为真，生成 `--- a/<path>` 头导致 conan create 报 source/target file does not exist。解决：每次 refresh-patch 前清理 orig 污染（baseline 哈希校验）。
2. **finish Step 8 gen_summary 崩溃**：`'str' object has no attribute 'append'`，SUMMARY.md 未生成（非阻塞，状态仍 published）。
3. **refresh-patch 尾部 `import yaml` 依赖 PYTHONPATH**：设 `PYTHONPATH=ohos-pysubsys-fix` 会覆盖默认 pip-global（PyYAML 所在），需合并 `pip-global:ohos-pysubsys-fix` 冒号分隔。
4. **track-edit scan 不识别新增文件**：新源文件必须显式 `track-edit add` 登记否则 refresh-patch --auto 漏生成新文件补丁（设计如此但易踩坑）。

---

**编译结束**: 2026-09-04 19:20
**最终状态**: published
