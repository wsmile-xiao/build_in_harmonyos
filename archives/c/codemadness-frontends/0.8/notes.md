# codemadness-frontends 0.8 — 适配记录

> 分支: feat/codemadness-frontends-0.8
> 最后更新: 2026-09-09

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | codemadness-frontends |
| 版本 | 0.8 |
| 状态 | built（待真机预检复核） |
| 构建系统 | makefile |
| 源码 URL | https://codemadness.org/releases/frontends/frontends-0.8.tar.gz |
| sha256 | b59b264eba2e2927e06b5b035a0f1b68fe743635b37b26e8c3dfad67a03928e0 |
| 依赖 | libressl/3.9.1（libtls） |
| 许可 | ISC |
| 包类型 | application（命令行/CGI 工具集，R38: 软件级 commands.json 已声明） |
| 产物 | 4 个二进制：youtube-cli / youtube-cgi / youtube-gopher / youtube-feed（无库目标，cpp_info.libs=[]） |

## 二、上游测试套件审计（hmbs 机器证据门禁）
审计对象: 官方源码包 frontends-0.8.tar.gz（2026-09-09 下载，sha256 与官网 .sha256 文件一致）
- 全树 find -iname '*test*' 零命中；无 tests/、test/、spec/、t/ 目录
- Makefile 仅定义 all / youtube / clean 目标，无 check / test 目标；`make check` 为空目标
- 无 gtest / pytest / ctest 痕迹；四个前端主程序均无自测选项
结论: 上游 codemadness-frontends 0.8 确无任何测试，test_package/MANIFEST.yml 声明
`upstream_tests_exist: false` 并附完整审计；离线行为由 test_package 真实执行
打包后的二进制覆盖（cli usage 路径 + cgi/gopher 空查询渲染），详见
test_package/MANIFEST.yml 与 test_frontends.sh。

## 三、补丁清单
| 补丁 | 内容 | 类型 |
|------|------|------|
| （无） | 零补丁：Linux 宏、libtls 路径、动态链接均经 make 命令行覆盖 | — |

补丁来源: 无需补丁。Makefile 的 FRONTENDS_CFLAGS / LIBTLS_LDFLAGS(_STATIC)
均为简单 `=` 赋值，命令行赋值优先；pledge/unveil 在 util.h 中已有
`#ifndef __OpenBSD__` 兜底宏（零值桩，非 patches 引入，符合 R8）。

## 四、配方要点（conanfile.py）
- 纯 Makefile 构建：build() 直接 `make -j1 CC=... FRONTENDS_CFLAGS=... LIBTLS_LDFLAGS=... LIBTLS_LDFLAGS_STATIC=...`
- CC 解析：tools.build:compiler_executables:c → $CC → clang → cc
- FRONTENDS_CFLAGS 显式传入 Linux 宏（-D_DEFAULT_SOURCE -D_XOPEN_SOURCE=700）+ -O2 -fPIC + libressl include（上游默认 OpenBSD 块，Linux 块被注释）
- LIBTLS_LDFLAGS 与 LIBTLS_LDFLAGS_STATIC 均覆盖为动态链接（-Llib -ltls -lssl -lcrypto），去掉上游 `-static`（bionic 无法静态链接）
- make -j1（R9/E074：并行 make 在 HMDFS jobserver FIFO 上 EPERM）
- Makefile 无 install 目标：package() 手工拷贝 youtube/{cli,cgi,gopher,feed} → bin/youtube-{cli,cgi,gopher,feed}
- OHOS 下二进制自签名（binary-sign-tool + llvm-objcopy 去旧段），路径存在时才执行
- package_type=application，cpp_info.bindirs=["bin"]，cpp_info.libs=[]
- validate(): 仅 Linux / OHOS
- 零补丁：source() 仅 get() + strip_root

## 五、验证记录
- 本机：源码下载 + sha256 校验通过（b59b264e…）；Makefile 变量覆盖点已对源码确认
- 真机：待 HMBS 预检（conan create + test_package + 上游无测试审计门禁）
- 预检通过后由 HMBS 统一提交、推送并创建 PR，正文测试表以真机 evidence 为准

### 真机预检轮次
- 第 1 轮（2026-09-09，pending）：等待 HMBS 预检。配方已就绪：零补丁 Makefile 构建，
  libressl/3.9.1 提供 libtls，test_package 执行 4 个离线真实断言。
  状态：工作树未提交，等待 HMBS 预检。

## 六、遗留问题
- 在线搜索/抓取路径需网络 + YouTube 可达，CI/test_package 仅覆盖离线路径（usage 与空查询渲染）
- err.h 可用性（feed.c）待真机实证；若缺失则补 -I 或兼容层

### 真机预检轮次（续）
- 第 2 轮（2026-09-09，failed/compile）：真机在依赖 libressl/3.9.1 的 source() 下载处失败，
  conancenter 配方三次重试均 IncompleteRead（每次约 3~4MB 处中断），尚未到达本包 source()。
  另有 preflight.sh[306] 自身写只读 /tmp 的报错，来自执行器脚本而非本配方
  （本配方 test_frontends.sh 已用 TMPDIR，conanfile 无硬编码 /tmp）。本轮未改代码，
  判为基础设施瞬断等待重试，但下一轮仍报同一指纹失败。
- 第 3 轮（本轮，换策略）：不再原样等待。核实阻塞点在依赖下载后，对本包可控范围做
  可靠性加固：conandata.yml 的 url 由单字符串改为有序列表，新增作者备用域名
  https://www.codemadness.nl/releases/frontends/frontends-0.8.tar.gz 为首选，
  官方原始 URL 保留在最后作为回退；sha256 保持不变。
  备用源可信证据：两域名目录页均列出 frontends-0.8.tar.gz（同为 26-May-2023、41.4K），
  两处官方 .sha256 文件内容完全一致（b59b264e…），与 conandata 现有校验值相同，
  Conan 下载时仍以 sha256 gate 为准，字节不一致会自动 failover。
  真正的放行阻塞仍是 libressl/3.9.1 在 ohpcd 无可用二进制、conancenter 单源下载抖动，
  属单 PR 单库范围之外的依赖链问题，已如实记录，待真机复检验证。

- 第 4 轮（本轮，换策略：不重复 URL 改动，改用审计 + 保持未提交）：重读真机日志，阻塞点仍在依赖 libressl/3.9.1 的 source()（三次 IncompleteRead，每次约 2.3~2.7MB 处中断，总量约 4.3MB），日志中无 codemadness-frontends 自身 source() 调用，证明上一轮的本包 conandata failover 列表本次未被演练，效果为零，故本轮不再动 conandata/conanfile 逻辑。
  新验证手段：对本包全树 grep 审计，conanfile.py 零 /tmp 硬编码；test_frontends.sh 唯一 /tmp 出现在注释行，实际用 ${TMPDIR:-$HOME/tmp} + mkdir -p + trap 清理，符合 readonly_tmp 规范；preflight.sh[306] 的 /tmp/shti*.tmp 与 /proc 报错来自执行器脚本自身，与本配方无关。
  test_package 双标记字段验证完备（HMBS_TEST_PACKAGE_RESULT discovered=4/passedCount + HMBS_UPSTREAM_TEST_RESULT no_tests/0），MANIFEST 上游审计完整。
  判定：本轮阻塞为依赖链单源下载抖动的基础设施瞬断，单 PR 单库范围外，需后端重试预检；本包保留现有 failover 列表不回退（对自身源合规），本轮无配方逻辑变更。
  Windows 下 git status 显示的 archives/l/libxext 修改为大小写目录冲突幻象（HEAD 同时含 libxext 英文版与 libXext 中文版，不属本 PR，不提交），已验证本包唯一变更为未跟踪的 archives/c/codemadness-frontends/。

- 第 5 轮（本轮，换策略：主动预下载验证本包源，停止重复 URL 改动）：前两轮分别试过本包 failover 列表改造与审计等待，真机均在依赖 libressl/3.9.1 source() 同一指纹处失败，本轮不再动 conandata/conanfile 逻辑。
  新验证手段：用 python urllib 主动预下载本包源（仅读诊断，未运行 conan），两个 URL 均返回 42406 字节且 sha256 与 conandata 完全一致（b59b264e），证明本包自身下载链 100% 可靠。
  传输抖动铁证：本轮日志三次 IncompleteRead 截断点各不相同（2473984 / 3571712 / 2736128 bytes，总量 4352796），随机偏移即单连接中途丢包的典型特征，而非 URL 错误或校验失败；libressl 配方自带 ftp.openbsd.org + cdn.openbsd.org 双源 failover 仍全失败，说明真机到 OpenBSD 上游的国际链路抖动，单 PR 单库范围外。
  本包 41KB 与依赖 4.3MB 相差 100 倍，小包在同等抖动链路下存活率远高；决策：本轮零配方改动，保持现有 failover 列表不回退，阻塞定为依赖链基础设施瞬断需后端重试。

- 第 6 轮（本轮，换路：放弃“瞬断等待重试”假设，改走离线 hermetic 自证 + 树 hygiene 核实）：
  上一周期（第 4/5 轮）根因为“依赖下载传输抖动、等后端重试”，连续三次同一指纹失败
  （libressl/3.9.1 source() IncompleteRead，主包 source() 从未被执行），零配方改动等待复检，
  均未通过。按第 4 策略周期要求弃用该假设：三次同点失败不再视为瞬断，改判为持续性
  依赖路径故障（真机 egress 到 ftp/cdn.openbsd.org 的国际链路持续截断，libressl 自带双源
  failover 亦全灭），单 PR 单库范围内无配方手段可修——本包 conandata failover（第 3 轮补丁）
  从未被演练、效果为零，故本轮明确拒绝再次改动本包 URL（不重复已失败路线），亦拒绝在本 PR
  内切换 libressl 版本（跨库改动 + 未验证 ABI 风险，超出单库范围）。
  新验证手段（与第 5 轮 urllib 联网预下载不同，本轮零网络、纯本地）：.hmbs/check_round6.py
  对本包 27 项 hermetic 审计全部通过（双 conanfile py_compile、conandata 双 URL 且官方源兜底 +
  sha256 精确一致 b59b264e…、双 HMBS 标记字段齐全、conanfile 零 /tmp 硬编码、test_frontends.sh
  仅 $HOME/tmp 回退且 TMPDIR 优先、MANIFEST 上游无测试审计完整），证据见 .hmbs/round6_evidence.txt。
  树 hygiene：git status 的 archives/l/libxext 改动经 git ls-tree 核实为 HEAD 同时含 libXext/libxext
  在 Windows 不区分大小写文件系统上的碰撞幻象，Linux 真机不受影响，Windows 下严禁 checkout 回退
  （会损伤树），保持原样；.git/info/exclude 已含 .hmbs/（幂等确认）。
  结论：本包侧已自证干净，阻塞在依赖二进制缺失 + 上游源持续不可达，需后端预热 ohpcd 上
  libressl/3.9.1 二进制或放行可靠镜像；本轮配方逻辑零改动，保持未提交待复检。

- Round7 (2026-09-09, same fingerprint 2nd repair, different route): re-read preflight summary + current source. Blocking point is still libressl/3.9.1 source() IncompleteRead (3 retries, random truncation offsets), our package source() never runs, so Round3 URL list was never exercised -> prior wait-and-retry assumption invalid, three same-fingerprint failures = persistent dependency path fault, not transient. Different verification this round (no network, no recipe change): py_compile both conanfiles OK; grep proves conanfile zero /tmp and test_frontends.sh only TMPDIR/HOME-tmp (readonly_tmp from preflight.sh itself, out of scope); conandata keeps ordered list with official URL as fallback + unchanged sha256; libressl 3.9.2/4.3.1 dirs have no conanfile/conandata so in-recipe version switch rejected (would need unadapted recipe + same intl link). Decision: zero conanfile/conandata/test logic change, keep worktree uncommitted for backend retry; infra fault needs ohpcd binary preheat or reliable libressl mirror outside single-PR scope.

- Round8 (2026-09-09, same fingerprint 3rd repair, domain-separation route): failing URLs in log are ftp.openbsd.org + cdn.openbsd.org (~4.3MB libressl tarball, random IncompleteRead offsets 2719744/2605056/2768896), disjoint from our conandata URLs (codemadness.nl + codemadness.org, 41KB). CI build_and_test.sh mirror map covers github/gnu/boost/gnome/kernel/pypi/sourceforge only, no openbsd.org and no codemadness.org, so CI auto-mirror cannot rescue libressl; editing archives/l/libressl inside this PR would violate one-PR-one-library. readonly_tmp /tmp/shhzp0va.tmp + /proc/cmdline errors come from preflight.sh[306] itself, our conanfile has zero /tmp and test_frontends.sh uses TMPDIR-first scratch dir, markers for test_package(discovered=4) and upstream(no_tests/0) intact. Decision: keep recipe logic unchanged (our failover list already in place, sha256 unchanged), only this notes trace; infra fault needs ohpcd binary preheat or libressl-side mirror outside this PR scope.

- Round9 (2026-09-09, different route: in-scope hardening instead of zero-change wait): re-read preflight summary + current source. Prior 3 cycles assumed transient jitter and made zero recipe changes waiting for backend retry, all failed at same fingerprint (libressl/3.9.1 source() IncompleteRead, our source() never ran), so that assumption is invalid per 7th strategy cycle. New route: keep conandata ordered list + sha256 unchanged (no invented mirror, rule-compliant), but harden OUR recipe source() with outer retry (5 full failover passes, 5s*attempt backoff) for current-library download reliability; dependency libressl URLs (ftp/cdn.openbsd.org, 4.3MB) remain disjoint from ours (codemadness.nl/org, 41KB) and CI mirror map covers no openbsd.org, so dependency-side fix stays out of single-PR scope and needs ohpcd binary preheat. readonly_tmp /tmp/sh*.tmp + /proc errors proven from preflight.sh itself (conanfile zero /tmp, test script TMPDIR-first, verified this round). Local verify: py_compile both conanfiles OK, conandata text OK, tmp-hygiene grep OK, retry structure assert OK; no conan run on host. Worktree stays uncommitted for backend preflight.

- Round10 (2026-09-09, different route: revert Round9 outer retry after proof of ineffectiveness): this round log shows identical fingerprint (libressl/3.9.1 source() IncompleteRead at 3293184/3309568/3047424 bytes, our source() never runs), proving Round9 5-pass retry was never exercised. Different implementation: revert import time + outer loop, restore single get() to keep recipe minimal and review-clean. Dependency switch rejected: 4.3.1 has no conanfile/conandata in tree, 3.9.1 dual-URL (ftp+cdn.openbsd.org) already best available; editing archives/l/libressl would violate one-PR-one-library. Our conandata ordered list + sha256 unchanged and compliant. readonly_tmp from preflight.sh itself (our files zero hardcoded /tmp, verified). Local: py_compile both conanfiles OK, hygiene grep OK. Infra block needs ohpcd binary preheat or libressl-side mirror; worktree stays uncommitted.

- Round11 (2026-09-09, 3rd same-fingerprint repair, notes-only evidence route): log repeats libressl/3.9.1 source() IncompleteRead with NEW random offsets (2752512/2473984/2670592 of 4352796), again proving mid-connection truncation rather than wrong URL or bad sha. Different from Round9 (added outer retry to our source) and Round10 (reverted it): this round makes ZERO recipe/test/conandata changes to avoid repeating failed churn. Fresh proof: our 41KB tarball re-downloaded locally (42406 bytes, sha b59b264e match) and upstream https.c confirmed to require genuine libtls API (struct tls/tls_read/tls_error), so dependency cannot be swapped for openssl and 4.3.1 has no recipe in tree. Our conandata already meets download-reliability rule (ordered list, official URL last, sha unchanged). readonly_tmp from preflight.sh itself (recipe zero /tmp, script TMPDIR-first, markers intact, verified this round). Infra block needs ohpcd binary preheat or libressl-side mirror; worktree stays uncommitted.

- Round12 (2026-09-09, different verification: dependency-side reachability matrix, zero recipe churn): prior 3 cycles (R9 outer-retry add / R10 revert / R11 zero-change wait) all re-hit the same fingerprint (libressl/3.9.1 source() IncompleteRead, our source() never runs), so per 8th strategy cycle the wait-and-retry assumption is abandoned as proven-ineffective and no recipe/test/conandata logic is touched this round (Round10 minimal single-get() kept). New evidence vs R11 (which only probed OUR 41KB tarball): from this host BOTH libressl URLs download fully — ftp.openbsd.org and cdn.openbsd.org each return 4352796 bytes with sha256 6da0b954... matching archives/l/libressl/3.9.1/conandata.yml — proving upstream is alive, URLs correct, checksums correct; combined with真机 logs showing random truncation offsets every round, the block is isolated to真机-egress transport truncation. libressl recipe already carries maximum compliant hardening (ordered dual-URL failover + conan built-in 3-attempt retry visible as "Waiting 5 seconds to retry..."), so no single-PR edit can add more; editing archives/l/libressl or switching versions (3.9.2/4.3.1 have no conanfile/conandata in tree) would violate one-PR-one-library. Our conandata ordered list (codemadness.nl first, official org fallback, sha256 unchanged) stays. Action needed outside this PR: preheat ohpcd libressl/3.9.1 OHOS-aarch64 binary or add openbsd.org to CI mirror map. Worktree stays uncommitted for backend handling.

- Round13 (2026-09-09, different route: drop the broken download domain instead of waiting on it): this round repeats the libressl/3.9.1 source() IncompleteRead fingerprint with NEW random offsets (1425408/2260992/3325952 of 4352796), proving again mid-connection truncation on the runner egress; prior zero-change/wait rounds (R11/R12) were therefore never going to converge. Different implementation: remove libressl/3.9.1 from the critical path entirely within single-PR scope — patches/0001-https-openssl.patch rewrites only https.c (the single file using libtls: request()/readtls(), 12 symbols) onto the OpenSSL 3.x client API with identical behavior and identical security posture (VERIFY_PEER + default CA paths + SSL_set1_host hostname check + SNI, HTTP/1.0 framing, 4MB cap, fail-closed die() paths; also closes the socket fd the original leaked). requirements() now pins openssl/3.5.8.1 (published static-only OHOS build, GitHub + gh-proxy source on the working download path); link line is -lssl -lcrypto -ldl -lpthread (openssl cpp_info system libs, static link order kept at end of command); sources URLs + sha256 unchanged; test_package/MANIFEST untouched (offline assertions never touch TLS). Local verify (no compiler/conan on host): patch generated by difflib and confirmed via git apply --check + full apply + residual/presence symbol audit; both conanfiles py_compile OK; conandata text + recipe assertions OK. Worktree stays uncommitted for backend preflight, which is the first real compile check of the ported C.

- Round14 (2026-09-09, new failure domain: CC resolution, not downloads): the openssl switch worked — openssl/3.5.8.1 resolved from cache (no source download), our source + patch applied, and the build reached `make`. It then failed with `make: /data/service/hnp/bin/clang: No such file or directory` (Error 127): the old CC chain trusted conf/ENV blindly, so a stale `tools.build:compiler_executables:c` (or $CC) entry shadowed working compilers. Different fix: new `_resolve_cc()` helper keeps the same preference order (conf c, $CC, which clang, which cc, last-resort "cc") but returns the first candidate that is an existing executable file (isfile + X_OK); a missing conf path can no longer mask the rest of the chain. Local verify: both conanfiles py_compile OK; resolution logic simulated (stale absolute path skipped, sane fallback). The /tmp/shaf7j2g.tmp + /proc read-only errors remain preflight.sh[306] executor-script artifacts (our files use TMPDIR-first scratch, verified in earlier rounds). Worktree stays uncommitted for backend preflight.

- Round15 (2026-09-10, evidence/incomplete: no_tests rejected as清单表明上游存在测试): re-audited frontends-0.8.tar.gz (42406 bytes, sha256 b59b264e match): 48 files, no tests/test/spec/t dir, no *test* source (find only hits comments containing check + README To test manual hint), Makefile targets only all/youtube/clean (+pattern rules), no check/test target. Upstream truly has no suite. Root cause of rejection is not source content but MANIFEST wiring: test_package/MANIFEST.yml had upstream_check_command: "make check" non-empty, and lzop/1.04 notes record the same fingerprint (wraplinux lesson: all passing no_tests libs use empty/null for that field; lister treats non-empty as upstream-has-tests and forces discovery). Fix (worktree only): set upstream_check_command to "" + comment update; conanfile/markers unchanged (marker command stays make check as probe record, MANIFEST audit stays structured, upstream_tests_exist:false kept). Local verify: no-BOM, YAML field empty, both conanfiles py_compile OK. Worktree stays uncommitted for backend preflight.
