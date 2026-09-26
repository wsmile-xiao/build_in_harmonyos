# radvd 2.20 测试报告

- 平台：HarmonyOS PC（B 机，aarch64，profile `ohos-aarch64`，os=OHOS / os.version=6.0 / clang 15）
- 参考：`radvd/2.20`
- 构建主机执行时间：`conan-verify` 为 2026-09-25 01:16–01:19；**入库的 `reports/w3-local-ci.log` 是 01:38:41 那轮 finish 的产物**（轮次归属见 §1.3）
- 本报告所有数字均逐字取自下表列出的日志文件，可用给出的命令原样复核。
- §1.2 的行号锚点绑定**入库那份** `reports/w3-local-ci.log`：`sha256 = 72a55b39149d986ccdb985222ed87b8a38c165aa482504c955de0f6430ca2cc9`（25036 B，mtime 2026-09-25 01:38:41），与同版本目录 `.ci-result.json` 的 `log_sha256` 逐字节相同（`timestamp=2026-09-25T01:38:41.653321`、`exit_code=0`）。改锚点前先 `sed -n 'Np'` 回读该行。

## 1. 五维账本

| 维度 | 上游官方套件（`make check`） | 消费者测试（`test_package/test.sh`） |
|---|---|---|
| 静态注册总数 | **36** | **7** 组断言 |
| 可执行数 | **36** | 7 |
| 实测通过 | **36** | 7 |
| 跳过 | **0** | 0 |
| 失败 | **0** | 0 |

通过率：上游 36/36 = 100%，消费者 7/7 = 100%。

### 1.1 静态清点口径（R51 第 1 步）

上游 `Makefile.am` 末段为 `TESTS = check_all` + `check_PROGRAMS = check_all`，
即 **automake 层只有 1 个测试条目**，36 个 libcheck 用例由这一个可执行程序承载：

```
grep -c tcase_add_test test/util.c   -> 16
grep -c tcase_add_test test/send.c   -> 20      ⇒ 注册用例 36
grep -c tcase_create   test/util.c   -> 6
grep -c tcase_create   test/send.c   -> 2       ⇒ Suite 2 个 / TCase 8 个
```

所以 `test-suite.log` 的 `# TOTAL: 1 / # PASS: 1` 与 `check_all.log` 的
`Checks: 36, Failures: 0, Errors: 0` 是同一轮测试的两个层级，不矛盾、不重复计数。
前置条件：`configure --with-check`，否则上游 `Makefile.am` 的 `check:` 目标直接
`$(error libcheck not available)`。
`test/test_build.sh` **不是**测试用例（它是按发行版名 apt/apk/dnf 装构建依赖的引导脚本），
故未计入分母。

### 1.2 实测取数原文

`reports/check_all.log`（本目录，36 条 `: Passed` 逐条在列）：

```
Running suite(s): util
 send
100%: Checks: 36, Failures: 0, Errors: 0
...
PASS check_all (exit status: 0)
```

`grep -c ": Passed$" reports/check_all.log` → **36**

`reports/test-suite.log`：

```
# TOTAL: 1
# PASS:  1
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
```

`reports/w3-local-ci.log`（本地 CI 模拟全量日志）行号锚点：

| 行 | 内容 |
|---|---|
| 367–378 | 367 `radvd/2.20: RUN: make check -j1`；370–377 编译 `check_all` 的 8 个 .o；378 `CCLD     check_all` |
| 383 | `PASS: check_all` |
| 385–394 | 385 `Testsuite summary for radvd 2.20`；387–393 `# TOTAL/PASS/SKIP/XFAIL/FAIL/XPASS/ERROR`（`# TOTAL: 1` 在 387） |
| 459–467 | 消费者测试 7 条 `PASS:` 原文（依次为断言 1-7：459 可定位 / 460 `-v` 版本 / 461 `-h` usage / 462 合法配置 / 463 非法配置被拒 / 466 未知指令被拒 / 467 `radvdump` 拒未知选项）；夹在中间的 464–465 是负例断言的**预期输出** |
| 468 | `radvd 2.20 consumer test: all assertions passed` |
| 470 | `[ok] radvd/2.20 — conan create passed` |
| 472 / 473 / 474 | `L1a` test_package 被 conan create 执行 / `L1b` 有执行证据 / `L1c` 上游官方测试在构建期真跑 |
| 478 + 480 | `L1e` 破坏性反向验证两行：478 `[step] L1e: Destructive negative test (R34)...`、480 `[ok] L1e: Negative test confirmed — test genuinely depends on radvd` |
| 23 / 66 / 93 | `G0_RESULT=pass` / `KC_RESULT=pass` / `JC_RESULT=pass` |
| 485–489 | 五档门禁判决 `L0/L1/L2/L4/L5_RESULT` = 485/486/487/488/489（见 §4，**`L2` 为 `skip`** 不是 pass） |
| 497 | `Pass rate: 100.0% (1/1)` |

上述行号系对本份日志（sha256 见文首）逐条 `sed -n 'Np'` 回读所得，一条命令可复算：
`grep -n -E 'RUN: make check|PASS: check_all|Testsuite summary|all assertions passed|conan create passed|L1[abce]|_RESULT=|Pass rate' reports/w3-local-ci.log`。

## 1.3 证据出处与轮次（防伪凭证）

- `reports/w3-local-ci.log` = **2026-09-25 01:38:41** 那轮 `finish` Step 5/10 的本地 CI 模拟（真 W3，产出 `.ci-result.json`）。绑定关系可复核：本文件 `sha256` = `72a55b39149d986ccdb985222ed87b8a38c165aa482504c955de0f6430ca2cc9`（25036 B，mtime 01:38:41）与版本目录内 `.ci-result.json` 的 `log_sha256` **逐字节相同**，后者 `timestamp=2026-09-25T01:38:41.653321`、`exit_code=0`。其内嵌构建设为另一个包目录 `~/tmp/ch/home-z23-radvd/p/b/radvd383f5aac12dee/b/build-release/`（见本日志 369 / 379 / 381 行）。
  ⇒ **该份的上游测试证据只到 automake 层**：383 行 `PASS: check_all`、387 行 `# TOTAL: 1`；在本文件里 `grep -c ': Passed'` = **0**、`grep -c 'Checks:'` = **0**。因此**不要**拿这份去复核 36 条逐用例，逐用例的唯一载体是下一条的 `check_all.log`。
- `reports/check_all.log` / `reports/test-suite.log` = 本窗 2026-09-25 **01:17:38** 那轮 `conan-verify` 的 G2 干净构建设在 `~/tmp/ch/home-radvd/p/b/radvdd6ba8023b7c38/b/build-release/`（内嵌路径可核），01:24:23 原样拷进 `reports/` 固化。**逐用例 36 条只在 `check_all.log`**：`grep -c ": Passed$"` = **36**、第 3 行 `100%: Checks: 36, Failures: 0, Errors: 0`；`test-suite.log` 是同轮的 automake 层（`# TOTAL: 1 / # PASS: 1`），两者是同一轮测试的两个层级（见 §1.1）。
- **另有一轮 01:19 的 finish（本机留档 `~/tmp/uc2/z34-radvd/finish1.out`，未入库）不是上面这份入库日志**，且实测其中 `: Passed` 计数 = **0**、`Checks:` 计数 = **0** ⇒ 该轮**不得**作为「36 条逐用例通过」的凭据引用；本报告与 PR 正文均不引用它。
- 两份日志因内嵌绝对路径而 md5 不同属正常；**判真伪按本轮 mtime 晚于功能性提交 + 判决标记（`[step]` / `L*_RESULT=` / `Total:`）数量 > 0**，不比 md5。
- `reports/runtime-radvd-ra.out` / `runtime-radvdump.out` = 01:22 与 01:23 的运行时取证，用的是 01:17 那轮的包内二进制。

## 2. 未执行项（权限面；分母不缩）

| 运行时能力 | 状态 | 证据（本目录） |
|---|---|---|
| RA 报文实际发送（`AF_INET6/SOCK_RAW/IPPROTO_ICMPV6`） | **未执行 — EPERM（无 CAP_NET_RAW）** | `reports/runtime-radvd-ra.out` |
| `radvdump` 抓包 | **未执行 — 同一处 EPERM** | `reports/runtime-radvdump.out` |

```
$ radvd -n -C ra-test.conf -m stderr
[Sep 25 01:22:53] radvd (2858): version 2.20 started
[Sep 25 01:22:53] radvd (2858): can't create socket(AF_INET6): Permission denied
open_icmpv6_socket: Permission denied                              # RC=1
```

**分母口径声明**：上游 36 个用例**不含**实际发包（`send` 套件只测 RA 报文字段构造与
lifetime 递减，全部在用户态内存里完成），因此上述两项**不在 36 的分母内**——
分母保持 36，未执行项单列，既不缩分母也不虚增。
判定为**权限面**而非内核/配方缺陷的依据（同轮 `open()` 系探针实测）：
`AF_NETLINK/NETLINK_ROUTE` 可用、IPv6 地址存在、`IPV6_JOIN_GROUP` 可用，
只有 raw ICMPv6 被 EPERM 拒绝。

## 3. 配置校验实测（任务要求的 `-t`/`-c` 语义澄清）

`radvd -h` 真实 usage 原文（本机跑出的，非文档转述）：

```
  -C, --config=PATH       Set the config file.  Default is /etc/radvd.d.
  -c, --configtest        Parse the config file and exit.
  -t, --chrootdir=PATH    Chroot to the specified path.
```

⇒ **配置校验的正确开关是 `-c`（配 `-C` 指定文件）；`-t` 是 chroot，不是 configtest。**
`test_package/test.sh` 的写法与注释是对的。实测：

| 用例 | 命令 | 结果 |
|---|---|---|
| 合法配置 | `radvd -c -C good.conf -l good.log -m stderr` | **RC=0，通过** |
| 非法取值（`AdvSendAdvert maybe;`） | `radvd -c -C bad.conf ...` | **RC=1，被拒**，第一条错误 `bad.conf:3 error: syntax error` |
| 未知指令（`NotARealDirective on;`） | `radvd -c -C bad2.conf ...` | **RC=1，被拒** |

（后两条是**负例断言的预期输出**，不是构建错误——历史上曾被误读成编译失败，
`w3-local-ci.log:463–467` 上下文可证：463 与 466 是两条 `PASS:`，464–465 夹在其间的就是下面这两行错误输出。）

## 4. 门禁判决

| 门禁 | 判决 | 说明 |
|---|---|---|
| W3 本地 CI 模拟 | **通过** | `[ok] radvd/2.20 — conan create passed` |
| conan-verify G0/G1/G2/G3 | **PASS** | `reports/conan-verify-report.md`（G2=conan create 干净构建；G3=系统同名库隔离 R26） |
| L0（质量门禁） | `pass` | 含 L0i 依赖在制品仓（bison/flex）、L0j 版本未占用、L0k commands.json、L0m 目录结构 |
| L1（测试执行） | `pass` | L1a/L1b/L1c + L1e 破坏性反向验证 |
| L2（冒烟） | `skip` | **两点同时成立，均非缺陷**：①框架侧 L2 初值就是 `skip` 且全程 non-blocking，它只裸跑包内 `bin/*` 的 `--version/--help` 并丢弃输出、不加载 Conan 运行环境；②本包实测 radvd 2.20 打印完 version/help 后仍以 **RC=1** 退出（逐条无管道复测：`-v` RC=1 首行 `Version: 2.20`、`--version` RC=1 同、`-h` RC=1 首行 `usage: radvd`、`--help` RC=1 同、`radvdump -e` RC=1），L2 按退出码判定故落 skip ⇒ 属**上游 CLI 退出码约定**，不是适配缺陷也不是不可执行；可执行性由消费者测试断言 1-3/7（内容断言，`w3-local-ci.log:459-468`）与 L1e（478 + 480）破坏性反向验证正向证明 |
| L4（补丁静态扫描） | `pass` | patches clean |
| L5（产物基线） | `pass` | bin/ 有内容 |
| JC / KC（垃圾与知识库门禁） | `pass` / `pass` | `w3-local-ci.log:93 / :66` |

## 5. 与上游口径的差异（R51 第 2/3 步）

- **未删除、未跳过、未改写任何上游用例**：静态 36 = 实测 36。
- 唯一改动是**把测试数据 stage 进构建树**（`build()` 内 `files.copy("*.conf", ...)`），
  因为 Conan 走 VPATH 外树构建、automake 以构建树为 cwd，上游 `test/util.c`、`test/send.c`
  里的字面量 `test/test1.conf` 找不到文件，会使 libcheck 只跑到 17/36 并报 3 处 failure。
  补齐后 36/36。上游源码的路径写法未改。
- 补丁 0005 只把 `test/print_safe_buffer.{c,h}` 的 `#include "../config.h"` 对齐为
  `"config.h"`（同目录 `test/check.c` 本来就是该写法），不改测试逻辑。
- 消费者测试 7 条断言全部调用被测包自己的二进制（`radvd` / `radvdump`），
  并经 L1e 破坏性验证（把 `bin/` 移走后测试必须失败）。

## 6. 复核命令（任何人可在构建主机上一字不差重放）

```bash
export CONAN_HOME=$HOME/tmp/ch/home-radvd
export SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
export PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH
W=$HOME/qzy/主理-34-radvd-2.20
sh ~/tmp/uc2/gate.sh 3000
sh ~/tmp/uc2/build-slot.sh --kind short -- sh -c \
  "cd $W && python3 scripts/ohc-run.py conan-verify radvd 2.20"
python3 $W/scripts/ohc-run.py finish radvd 2.20 built
python3 $W/scripts/ohc-run.py graph validate
```

（`finish`/`conan-verify` 会临时把 conandata 的 url 改写成镜像列表再"还原"，
还原后仍带 `gh-proxy.com` ⇒ 复核完必须 `git show HEAD:archives/r/radvd/2.20/conandata.yml >` 回去，
详见 `../notes.md` 的「本地 W3 的 conandata 污染」。）
